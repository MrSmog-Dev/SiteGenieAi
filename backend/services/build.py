"""Conversational Build Canvas — fluid, chat-driven website building.

A build SESSION holds a chat thread + the current template. The first message spins up a full
site (design-intelligence injected); subsequent messages are natural-language refinements applied
live to the same template. Small tweaks are billed at a discount.
"""
import json
import re
import uuid
from datetime import datetime, timezone

from config import STRATEGY_MODEL, logger
from database import db
from services.llm import _call_llm, _start_job

INTENT_SYSTEM = (
    "You turn a small-business owner's first message into a website build brief. Infer sensible details "
    "from the message; invent tasteful specifics where unstated. Reply ONLY JSON, no markdown:\n"
    '{"business_name": "<name or a fitting invented one>", "industry": "<niche>", '
    '"description": "<1-2 sentence description>", "style": "<one of: modern, minimal, bold, elegant, '
    'playful, corporate>", "primary_color": "<hex that fits the brand>", '
    '"brand_keywords": "<3-5 comma-separated vibe words>", "target_audience": "<who>", '
    '"key_services": "<3-5 comma-separated>", "reply": "<one friendly sentence to the owner confirming '
    "what you're building>\"}"
)

REFINE_CLASSIFY_SYSTEM = (
    "You are the build assistant on SiteGenie's live website canvas. The owner sent a message about the "
    "site currently on screen. Classify it and craft a friendly one-line reply.\n"
    "Reply ONLY JSON: {\"kind\": \"tweak\"|\"major\"|\"chat\", \"reply\": \"<one friendly sentence>\", "
    "\"instructions\": \"<clear design/edit instructions for the builder, or empty if kind=chat>\"}\n"
    "kind=tweak: a small change (color, text, spacing, swap a word, tweak a button). "
    "kind=major: a substantial change (add/remove a whole section, restructure, restyle the whole site). "
    "kind=chat: a question or comment needing no site change."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(user_id: str) -> dict:
    sid = f"bld_{uuid.uuid4().hex[:12]}"
    doc = {"session_id": sid, "user_id": user_id, "template_id": None,
           "messages": [], "created_at": _now(), "updated_at": _now()}
    await db.build_sessions.insert_one(dict(doc))
    return {"session_id": sid, "messages": [], "template_id": None}


async def get_session(user_id: str, sid: str) -> dict | None:
    return await db.build_sessions.find_one(
        {"session_id": sid, "user_id": user_id}, {"_id": 0})


async def _push(sid: str, role: str, content: str, **extra):
    msg = {"role": role, "content": content, "ts": _now(), **extra}
    await db.build_sessions.update_one(
        {"session_id": sid},
        {"$push": {"messages": {"$each": [msg], "$slice": -80}}, "$set": {"updated_at": _now()}})
    return msg


async def handle_message(user: dict, session: dict, text: str, model: str = None, quality: str = None) -> dict:
    """Returns {reply, job_id?, kind}. The frontend polls the job for the live site update."""
    uid = user["user_id"]
    sid = session["session_id"]
    await _push(sid, "user", text)

    if not session.get("template_id"):
        # First message → full build.
        try:
            raw = await _call_llm(f"Owner's request: {text}", INTENT_SYSTEM, STRATEGY_MODEL)
            spec = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        except Exception:
            logger.exception("build intent parse failed")
            spec = {"business_name": "", "industry": "", "description": text[:300], "style": "modern",
                    "primary_color": "#0055FF", "reply": "On it — building your site now."}
        fields = {
            "business_name": spec.get("business_name") or "New Business",
            "industry": spec.get("industry", ""), "description": spec.get("description", text[:300]),
            "style": spec.get("style", "modern"), "primary_color": spec.get("primary_color", "#0055FF"),
            "brand_keywords": spec.get("brand_keywords", ""), "target_audience": spec.get("target_audience", ""),
            "key_services": spec.get("key_services", ""),
            "quality": (quality or "quality"), "model": model,
        }
        job = await _start_job(user, fields, mode="new")
        reply = spec.get("reply") or f"Building your {fields['industry'] or 'business'} site now — one moment."
        await _push(sid, "assistant", reply, job_id=job["job_id"])
        return {"reply": reply, "job_id": job["job_id"], "kind": "build"}

    # Refinement on the existing site.
    try:
        raw = await _call_llm(f"Owner said: {text}", REFINE_CLASSIFY_SYSTEM, STRATEGY_MODEL)
        cls = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
    except Exception:
        cls = {"kind": "major", "reply": "Applying that now.", "instructions": text}
    kind = cls.get("kind", "major")
    reply = cls.get("reply") or "On it."

    if kind == "chat":
        await _push(sid, "assistant", reply)
        return {"reply": reply, "kind": "chat"}

    instructions = cls.get("instructions") or text
    # Small tweaks are billed at a discount via the 'tweak' mode floor.
    edit_mode = "edit"
    fields = {"instructions": instructions, "model": model, "tweak": kind == "tweak"}
    tpl = await db.templates.find_one({"template_id": session["template_id"]}, {"_id": 0, "purchased": 1})
    free = bool(tpl and tpl.get("purchased"))
    job = await _start_job(user, fields, mode=edit_mode, template_id=session["template_id"], free=free)
    await _push(sid, "assistant", reply, job_id=job["job_id"])
    return {"reply": reply, "job_id": job["job_id"], "kind": kind}


async def attach_template(sid: str, template_id: str):
    await db.build_sessions.update_one({"session_id": sid}, {"$set": {"template_id": template_id, "updated_at": _now()}})
