"""Team Pulse — makes the AI Team feel alive.

Two responsibilities:
1. ACTIVITY LOG — a single append-only feed (`agent_activity`) that every autonomous
   agent action writes to, plus a rolling per-agent status board (`agent_status`).
   The Team Pulse tab and the Dashboard widget read from these.
2. PROACTIVE PULSE — a throttled loop where idle agents drop short, data-grounded
   observations on their own so the team is visibly working even when no one is
   talking to them.
"""
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger
from database import db

# How often the pulse loop wakes up, and how often a single agent may proactively post.
PULSE_TICK_SECONDS = 180           # loop cadence
PULSE_MIN_GAP_MINUTES = 20         # min gap between two proactive posts (any agent) — "subtle"
AGENT_PROACTIVE_COOLDOWN_HOURS = 4 # an individual agent won't self-post more often than this
ACTIVITY_CAP = 400                 # keep the feed bounded


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def log_activity(user_id: str, agent_id: str, kind: str, summary: str,
                       detail: str = "", link: str = "", status: str = "idle"):
    """Record one autonomous action into the shared feed and refresh the agent's status."""
    try:
        act = {
            "activity_id": f"act_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "agent_id": agent_id,
            "kind": kind,                    # e.g. briefing, article, build, hunt, demo, memo, meeting, task, pulse
            "summary": (summary or "").strip()[:280],
            "detail": (detail or "").strip()[:600],
            "link": link or "",
            "created_at": _now(),
        }
        await db.agent_activity.insert_one(dict(act))
        await set_agent_status(user_id, agent_id, status, last_action=act["summary"])
        # bound the feed
        count = await db.agent_activity.count_documents({"user_id": user_id})
        if count > ACTIVITY_CAP:
            old = await db.agent_activity.find(
                {"user_id": user_id}, {"_id": 1}).sort("created_at", 1).to_list(count - ACTIVITY_CAP)
            if old:
                await db.agent_activity.delete_many({"_id": {"$in": [o["_id"] for o in old]}})
    except Exception:
        logger.exception("log_activity failed")


async def set_agent_status(user_id: str, agent_id: str, status: str, current_task: str = None,
                           last_action: str = None):
    """status: idle | working. current_task describes what they're doing right now."""
    upd = {"status": status, "updated_at": _now()}
    if status == "working" and current_task is not None:
        upd["current_task"] = current_task
    if status != "working":
        upd["current_task"] = None
    if last_action is not None:
        upd["last_action"] = last_action
        upd["last_active"] = _now()
    await db.agent_status.update_one(
        {"user_id": user_id, "agent_id": agent_id}, {"$set": upd}, upsert=True)


async def start_working(user_id: str, agent_id: str, current_task: str):
    await set_agent_status(user_id, agent_id, "working", current_task=current_task)


async def stop_working(user_id: str, agent_id: str, last_action: str = None):
    await set_agent_status(user_id, agent_id, "idle", last_action=last_action)


# ---------------- Proactive pulse ----------------

PULSE_SYSTEM = (
    "You are {name} — {role} on SiteGenie's autonomous AI executive team. You are between tasks and "
    "proactively checking in with the business Owner WITHOUT being asked — showing initiative like a "
    "real team member who never stops working.\n"
    "PERSONALITY: {personality}\n\n"
    "Write ONE short, punchy proactive update in your own voice: an observation, a small win, a heads-up, "
    "or a concrete next step you're taking — grounded in the live numbers below. Max 45 words. "
    "No greeting, no sign-off, no markdown. Sound genuinely on-duty and specific to your specialty.\n\n"
    "LIVE BUSINESS DATA:\n{snapshot}"
)

# Kept small & specific so pulses feel like real work-in-progress, not chatter.
PULSE_KINDS = {
    "titan": "scanning the ops dashboard",
    "nova": "reviewing strategy angles",
    "atlas": "crunching the latest numbers",
    "ledger": "checking unit economics",
    "quill": "polishing conversion copy",
    "ivy": "tracking keyword opportunities",
    "blaze": "spotting content trends",
    "mara": "reviewing the lifecycle funnel",
    "rex": "eyeing the lead pipeline",
    "halo": "watching the support queue",
    "forge": "auditing the Market lineup",
    "zephyr": "designing a growth experiment",
}


async def _eligible_pulse_agent(user_id: str, agent_ids: list) -> str:
    """Pick an agent that is idle and hasn't self-posted recently (rotates naturally)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=AGENT_PROACTIVE_COOLDOWN_HOURS)).isoformat()
    # recently pulsed agents
    recent = {a["agent_id"] async for a in db.agent_activity.find(
        {"user_id": user_id, "kind": "pulse", "created_at": {"$gte": cutoff}},
        {"_id": 0, "agent_id": 1})}
    # never let a currently-working agent pulse
    working = {s["agent_id"] async for s in db.agent_status.find(
        {"user_id": user_id, "status": "working"}, {"_id": 0, "agent_id": 1})}
    pool = [a for a in agent_ids if a not in recent and a not in working]
    if not pool:
        return None
    # prefer the agent idle the longest (or never active)
    statuses = {s["agent_id"]: s async for s in db.agent_status.find(
        {"user_id": user_id, "agent_id": {"$in": pool}}, {"_id": 0})}
    pool.sort(key=lambda a: statuses.get(a, {}).get("last_active") or "")
    # a little randomness among the stalest few so it doesn't feel robotic
    return random.choice(pool[:4])


async def maybe_proactive_pulse(user_id: str):
    """Called by the automation tick. At most one subtle proactive post per PULSE_MIN_GAP_MINUTES."""
    from services.agents import AGENTS, AGENT_MAP, post_agent_message, business_snapshot
    from services.llm import _call_llm

    gap_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=PULSE_MIN_GAP_MINUTES)).isoformat()
    last = await db.agent_activity.find_one(
        {"user_id": user_id, "kind": "pulse"}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
    if last and str(last.get("created_at", "")) >= gap_cutoff:
        return  # too soon — keep it subtle

    agent_id = await _eligible_pulse_agent(user_id, [a["id"] for a in AGENTS])
    if not agent_id:
        return
    agent = AGENT_MAP[agent_id]
    try:
        await start_working(user_id, agent_id, PULSE_KINDS.get(agent_id, "on the job"))
        snapshot = await business_snapshot()
        import json
        system = PULSE_SYSTEM.format(name=agent["name"], role=agent["role"],
                                     personality=agent["personality"],
                                     snapshot=json.dumps(snapshot, default=str)[:6000])
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"pulse_{agent_id}_{uuid.uuid4().hex[:8]}",
                       system_message=system).with_model("anthropic", STRATEGY_MODEL)
        msg = str(await asyncio.wait_for(
            chat.send_message(UserMessage(text="Post your proactive update now.")), timeout=60)).strip()
        if not msg:
            await stop_working(user_id, agent_id)
            return
        await post_agent_message(user_id, agent_id, f"💡 {msg}")
        await log_activity(user_id, agent_id, "pulse", msg,
                           detail="Proactive check-in — no prompt needed.",
                           link=f"/team?agent={agent_id}", status="idle")
        logger.info("pulse: %s posted a proactive update", agent_id)
    except Exception:
        logger.exception("proactive pulse failed for %s", agent_id)
        await stop_working(user_id, agent_id)


# ---------------- Read models for the API ----------------

async def get_activity_feed(user_id: str, limit: int = 40, before: str = None,
                            agent_id: str = None) -> list:
    q = {"user_id": user_id}
    if agent_id:
        q["agent_id"] = agent_id
    if before:
        q["created_at"] = {"$lt": before}
    return await db.agent_activity.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def get_status_board(user_id: str) -> dict:
    board = {s["agent_id"]: s async for s in db.agent_status.find(
        {"user_id": user_id}, {"_id": 0})}
    working = sum(1 for s in board.values() if s.get("status") == "working")
    latest = await db.agent_activity.find_one(
        {"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)])
    total = await db.agent_activity.count_documents({"user_id": user_id})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = await db.agent_activity.count_documents(
        {"user_id": user_id, "created_at": {"$gte": today}})
    return {"statuses": board, "working_now": working, "latest": latest,
            "total_activities": total, "today_count": today_count}
