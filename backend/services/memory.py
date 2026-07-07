"""Persistent agent brain — survives the 'Reset business data' tool.

Each of the 12 agents keeps a durable memory per owner in `agent_memory`:
- facts        : durable facts, preferences, goals, context (auto-extracted + manual)
- open_threads : work-in-progress the agent can pick back up
- rolling_summary : a short running summary of recent conversation
This is injected into every agent reply so agents "remember and continue" even after
`agent_chats` (visible history) is wiped by a reset. The reset tool never touches this store.
"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger
from database import db

FACTS_CAP = 40
THREADS_CAP = 15
SUMMARY_MAX = 900


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())[:200]


async def get_memory(user_id: str, agent_id: str) -> dict:
    mem = await db.agent_memory.find_one(
        {"user_id": user_id, "agent_id": agent_id}, {"_id": 0})
    if not mem:
        return {"agent_id": agent_id, "facts": [], "open_threads": [], "rolling_summary": ""}
    mem.setdefault("facts", [])
    mem.setdefault("open_threads", [])
    mem.setdefault("rolling_summary", "")
    return mem


async def agent_memory_context(user_id: str, agent_id: str) -> str:
    mem = await get_memory(user_id, agent_id)
    facts = mem.get("facts") or []
    threads = [t for t in (mem.get("open_threads") or []) if t.get("status") != "done"]
    summary = mem.get("rolling_summary") or ""
    if not (facts or threads or summary):
        return ("YOUR PERSISTENT MEMORY: empty so far — you'll build durable memory of the owner's "
                "preferences, decisions and open work as you go (it survives data resets).")
    lines = ["YOUR PERSISTENT MEMORY (durable — survives data resets; treat as true and continue from it):"]
    if summary:
        lines.append(f"Where we left off: {summary}")
    if facts:
        lines.append("What you remember about the owner & business:")
        lines += [f"  • {f['text']}" for f in facts[-FACTS_CAP:]]
    if threads:
        lines.append("Open threads you were working on (pick these back up):")
        lines += [f"  • {t['text']}" for t in threads[-THREADS_CAP:]]
    return "\n".join(lines)


EXTRACT_SYSTEM = (
    "You maintain the long-term MEMORY of a single AI teammate on SiteGenie's executive team. You read the "
    "latest exchange between the business OWNER and this teammate and extract only what is worth remembering "
    "long-term. Be selective — skip small talk.\n"
    "Reply with ONLY a JSON object, no markdown:\n"
    "{\n"
    '  "facts": [{"text": "<durable fact/preference/goal/context, one sentence>", '
    '"kind": "fact"|"preference"|"goal"|"context"}],\n'
    '  "open_threads": [{"text": "<a task/thread now in progress this teammate should continue>"}],\n'
    '  "done_threads": ["<text of a previously-open thread that is now finished/resolved>"],\n'
    '  "summary": "<=60 words: where this conversation currently stands, so it can resume seamlessly>"\n'
    "}\n"
    "Rules: facts must be genuinely durable (preferences, decisions, goals, stable context) — NOT one-off "
    "questions. If the owner says 'remember…/note that…/keep in mind…', ALWAYS capture it as a fact. "
    'If nothing is worth storing, use empty arrays and keep summary short. Never invent.'
)


async def extract_and_store_memory(user_id: str, agent_id: str, owner_msg: str, reply: str):
    """Background: distill the exchange into durable memory for this agent."""
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"mem_{agent_id}_{uuid.uuid4().hex[:8]}",
                       system_message=EXTRACT_SYSTEM).with_model("anthropic", STRATEGY_MODEL)
        raw = await asyncio.wait_for(chat.send_message(UserMessage(
            text=f"OWNER SAID:\n{owner_msg[:1500]}\n\nTEAMMATE REPLIED:\n{reply[:4000]}")), timeout=45)
        data = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        await _merge_memory(user_id, agent_id, data, source="auto")
    except Exception:
        logger.exception("memory extraction failed for %s", agent_id)


async def _merge_memory(user_id: str, agent_id: str, data: dict, source: str):
    mem = await get_memory(user_id, agent_id)
    facts = mem.get("facts") or []
    threads = mem.get("open_threads") or []
    existing_fact_norms = {_norm(f["text"]) for f in facts}
    for f in (data.get("facts") or [])[:8]:
        text = str(f.get("text", "")).strip()
        if text and _norm(text) not in existing_fact_norms:
            facts.append({"mem_id": f"m_{uuid.uuid4().hex[:8]}", "text": text[:280],
                          "kind": f.get("kind", "fact"), "source": source, "created_at": _now()})
            existing_fact_norms.add(_norm(text))

    done_norms = {_norm(t) for t in (data.get("done_threads") or [])}
    for t in threads:
        if _norm(t.get("text", "")) in done_norms:
            t["status"] = "done"
            t["updated_at"] = _now()
    open_norms = {_norm(t["text"]) for t in threads if t.get("status") != "done"}
    for t in (data.get("open_threads") or [])[:5]:
        text = str(t.get("text", "")).strip()
        if text and _norm(text) not in open_norms:
            threads.append({"mem_id": f"m_{uuid.uuid4().hex[:8]}", "text": text[:280],
                            "status": "open", "created_at": _now(), "updated_at": _now()})
            open_norms.add(_norm(text))

    summary = str(data.get("summary", "")).strip()[:SUMMARY_MAX] or mem.get("rolling_summary", "")
    update = {
        "facts": facts[-FACTS_CAP:],
        "open_threads": threads[-THREADS_CAP:],
        "rolling_summary": summary,
        "summary_updated_at": _now(), "updated_at": _now(),
    }
    await db.agent_memory.update_one(
        {"user_id": user_id, "agent_id": agent_id},
        {"$set": update, "$setOnInsert": {"user_id": user_id, "agent_id": agent_id}}, upsert=True)


async def add_fact(user_id: str, agent_id: str, text: str, kind: str = "fact") -> dict:
    text = (text or "").strip()
    if not text:
        return {"added": False}
    await _merge_memory(user_id, agent_id, {"facts": [{"text": text, "kind": kind}]}, source="manual")
    return {"added": True}


async def delete_memory_item(user_id: str, agent_id: str, mem_id: str) -> bool:
    res = await db.agent_memory.update_one(
        {"user_id": user_id, "agent_id": agent_id},
        {"$pull": {"facts": {"mem_id": mem_id}, "open_threads": {"mem_id": mem_id}},
         "$set": {"updated_at": _now()}})
    return res.modified_count > 0
