import asyncio
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

from config import OWNER_EMAIL, STRATEGY_MODEL, logger
from database import db
from services.agents import (AGENT_MAP, agent_reply, post_agent_message, run_forge_build)
from services.llm import (_build_brief_prompt, _build_site_prompt, _call_llm, _call_build_llm,
                          clean_html, GEN_STRATEGY_SYSTEM)
from services.blog import run_ivy_blog

BRIEFING_UTC_HOUR = 11
BLOG_UTC_HOUR = 9
DIGEST_UTC_HOUR = 12
TICK_SECONDS = 900


async def ensure_automation_state():
    for job in ("titan_briefing", "forge_weekly", "ivy_daily_blog", "rex_weekly_hunt", "mara_digest"):
        await db.automation_state.update_one({"job": job}, {"$setOnInsert": {"job": job}}, upsert=True)


async def automation_loop():
    await asyncio.sleep(20)
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("automation tick failed")
        await asyncio.sleep(TICK_SECONDS)


async def _tick():
    owner = await db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "user_id": 1})
    if not owner:
        return
    now = datetime.now(timezone.utc)
    stale = (now - timedelta(minutes=20)).isoformat()
    await db.agent_jobs.update_many(
        {"status": {"$in": ["queued", "designing", "building", "pricing"]},
         "$or": [{"updated_at": {"$lt": stale}},
                 {"updated_at": {"$exists": False}, "created_at": {"$lt": stale}}]},
        {"$set": {"status": "error", "error": "Interrupted by a server restart."}})
    await db.leads.update_many(
        {"demo_status": {"$in": ["queued", "building"]}, "updated_at": {"$lt": stale}},
        {"$set": {"demo_status": "error"}})
    await db.team_tasks.update_many(
        {"status": "running", "updated_at": {"$lt": stale}},
        {"$set": {"status": "error", "error": "Interrupted by a server restart."}})
    await db.war_room_meetings.update_many(
        {"status": {"$in": ["starting", "running"]}, "updated_at": {"$lt": stale}},
        {"$set": {"status": "error", "error": "Interrupted by a server restart."}})
    queued_task = await db.team_tasks.find_one(
        {"status": "queued", "executable": {"$ne": None}}, {"_id": 1})
    running_task = await db.team_tasks.find_one({"status": "running"}, {"_id": 1})
    if queued_task and not running_task:
        from services.team import process_team_tasks
        asyncio.create_task(process_team_tasks(owner["user_id"]))
    today = now.strftime("%Y-%m-%d")
    if now.hour >= BRIEFING_UTC_HOUR:
        claimed = await db.automation_state.find_one_and_update(
            {"job": "titan_briefing", "last_run_date": {"$ne": today}},
            {"$set": {"last_run_date": today}})
        if claimed:
            await run_titan_briefing(owner["user_id"])
    if now.hour >= BLOG_UTC_HOUR:
        claimed = await db.automation_state.find_one_and_update(
            {"job": "ivy_daily_blog", "last_run_date": {"$ne": today}},
            {"$set": {"last_run_date": today}})
        if claimed:
            await run_ivy_blog(owner["user_id"])
    if now.weekday() == 0 and now.hour >= DIGEST_UTC_HOUR:
        claimed = await db.automation_state.find_one_and_update(
            {"job": "mara_digest", "last_run_date": {"$ne": today}},
            {"$set": {"last_run_date": today}})
        if claimed:
            await run_mara_digest(owner["user_id"])
    cutoff = (now - timedelta(days=7)).isoformat()
    claimed = await db.automation_state.find_one_and_update(
        {"job": "rex_weekly_hunt", "$or": [{"last_run": {"$exists": False}}, {"last_run": {"$lt": cutoff}}]},
        {"$set": {"last_run": now.isoformat()}})
    if claimed:
        await run_rex_weekly_hunt(owner["user_id"])
    claimed = await db.automation_state.find_one_and_update(
        {"job": "forge_weekly", "$or": [{"last_run": {"$exists": False}}, {"last_run": {"$lt": cutoff}}]},
        {"$set": {"last_run": now.isoformat()}})
    if claimed:
        await run_forge_weekly(owner["user_id"])


async def run_titan_briefing(owner_id: str):
    date_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    prompt = (f"AUTOMATED MORNING BRIEFING for {date_str}. Compile the owner's daily briefing now: "
              "1) a one-line business health verdict, 2) the key numbers, 3) anything that needs the "
              "owner's attention, 4) top 3 priorities today with which teammate should own each. "
              f"Open with 'Morning Briefing — {date_str}'.")
    reply = await agent_reply(AGENT_MAP["titan"], [], prompt)
    await post_agent_message(owner_id, "titan", reply)
    logger.info("automation: titan morning briefing posted")


NICHE_SYSTEM = ("You are Forge, SiteGenie's template curator. Given the current Template Market lineup, "
                "suggest ONE specific new business niche not yet covered that would sell well as a premium "
                "$200-500 website template. Reply with ONLY the niche phrase (2-6 words), nothing else.")


HUNT_PICK_SYSTEM = (
    "You are Rex, SiteGenie's lead hunter, picking this week's hunting ground. Choose ONE US city or town "
    "(mid-size or small — less saturated) and ONE local business category likely to have established "
    "businesses WITHOUT websites (e.g. barbershops, food trucks, auto repair, landscaping, taquerias, "
    "nail salons, plumbers, towing). Avoid the recently hunted combos provided. "
    'Reply ONLY JSON: {"location": "<City, ST>", "category": "<category>"}'
)


async def run_rex_weekly_hunt(owner_id: str):
    from config import GOOGLE_PLACES_API_KEY
    if not GOOGLE_PLACES_API_KEY:
        logger.info("automation: rex weekly hunt skipped — no Google Places key")
        return
    recent = await db.leads.find({"location": {"$exists": True, "$ne": None}},
                                 {"_id": 0, "location": 1, "category": 1}
                                 ).sort("created_at", -1).to_list(30)
    combos = sorted({f"{l.get('category')} in {l.get('location')}" for l in recent if l.get("location")})
    try:
        raw = await _call_llm("Recently hunted: " + ("; ".join(combos) or "none yet"),
                              HUNT_PICK_SYSTEM, STRATEGY_MODEL)
        pick = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        from services.team import rex_hunt_and_report
        await rex_hunt_and_report(owner_id, pick["location"], pick["category"], intro="Weekly auto-hunt")
        logger.info("automation: rex weekly hunt done (%s / %s)", pick["location"], pick["category"])
    except Exception as e:
        logger.exception("rex weekly hunt failed")
        await post_agent_message(owner_id, "rex",
                                 f"My weekly auto-hunt hit a snag ({type(e).__name__}). I'll try again next week.")


async def run_mara_digest(owner_id: str):
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    prompt = (f"AUTOMATED WEEKLY ANALYTICS DIGEST for the week ending {date_str}. Write the owner's weekly "
              "digest now, in your voice, as a ready-to-send email: a subject line, then a short skimmable "
              "body covering 1) users (total + new this week), 2) revenue by stream, 3) site views + top "
              "published sites, 4) Template Market activity, 5) lead-board movement, and 6) ONE clear "
              f"recommendation for next week. Open with 'Weekly Digest — {date_str}'.")
    reply = await agent_reply(AGENT_MAP["mara"], [], prompt)
    await post_agent_message(owner_id, "mara", reply)
    logger.info("automation: mara weekly digest posted")


async def run_forge_weekly(owner_id: str):
    active = await db.agent_jobs.find_one(
        {"user_id": owner_id, "status": {"$in": ["queued", "designing", "building", "pricing"]}}, {"_id": 1})
    if active:
        logger.info("automation: forge busy, skipping weekly build")
        return
    cats = [l.get("category") or l.get("title") async for l in
            db.market_listings.find({"active": True}, {"_id": 0, "category": 1, "title": 1})]
    raw = await _call_llm("Current lineup: " + "; ".join(str(c) for c in cats if c), NICHE_SYSTEM, STRATEGY_MODEL)
    niche = str(raw).strip().strip('."\'')[:80]
    job_id = f"forge_{uuid.uuid4().hex[:10]}"
    await db.agent_jobs.insert_one({"job_id": job_id, "user_id": owner_id, "agent_id": "forge",
                                    "brief": niche, "status": "queued", "auto": True,
                                    "created_at": datetime.now(timezone.utc).isoformat()})
    logger.info("automation: forge weekly build starting for niche '%s'", niche)
    await run_forge_build(job_id, owner_id, niche)
    job = await db.agent_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if job and job.get("status") == "done":
        r = job["result"]
        await post_agent_message(owner_id, "forge",
            f'Weekly drop, done while you were away: I picked the niche "{niche}", built "{r["title"]}" '
            f'and listed it on the Market at ${r["price_usd"]} ({r["tier"]}). Lineup stays fresh.')
    else:
        await post_agent_message(owner_id, "forge",
            f'My automated weekly build for "{niche}" failed: {(job or {}).get("error", "unknown error")}. '
            "I'll try again next week.")


DEMO_SPEC_SYSTEM = (
    "You prepare a website spec for a REAL business that SiteGenie wants to win as a client by building "
    "them a demo site. Keep the given business name EXACTLY. Invent plausible details where unknown. "
    "Respond with ONLY a JSON object, no markdown fences:\n"
    '{"business_name": "<exactly as given>", "industry": "<niche>", "description": "<2 rich sentences>", '
    '"style": "<one word>", "primary_color": "<hex>", "target_audience": "<who>", '
    '"key_services": "<4 comma-separated services>", "brand_keywords": "<4 comma-separated adjectives>", '
    '"contact_email": "<plausible email for the business>", "phone": "<the given phone if provided>"}'
)


async def run_lead_demo(lead_id: str):
    """Rex -> Forge handoff: auto-build and publish a pitch demo site for a contacted lead."""
    lead = await db.leads.find_one({"lead_id": lead_id}, {"_id": 0})
    if not lead or lead.get("demo_status") in ("building", "ready"):
        return
    owner = await db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "user_id": 1})
    if not owner:
        return
    await db.leads.update_one({"lead_id": lead_id},
                              {"$set": {"demo_status": "building",
                                        "updated_at": datetime.now(timezone.utc).isoformat()}})
    try:
        info = {k: lead.get(k) for k in ("business_name", "category", "phone", "address",
                                         "rating", "reviews_count", "issues")}
        raw = await _call_llm(f"Business info: {json.dumps(info, default=str)}", DEMO_SPEC_SYSTEM, STRATEGY_MODEL)
        spec = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        spec["business_name"] = lead["business_name"]
        if lead.get("phone"):
            spec["phone"] = lead["phone"]
        brief = await _call_llm(_build_brief_prompt(spec), GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
        html = clean_html(await _call_build_llm(_build_site_prompt(spec, brief)))
        from routes.templates import unique_slug
        slug = await unique_slug(f"demo {lead['business_name']}")
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        await db.templates.insert_one({**spec, "quality": "quality", "template_id": template_id,
                                       "user_id": owner["user_id"], "html": html,
                                       "demo_for_lead": lead_id, "published": True, "slug": slug,
                                       "published_at": now, "created_at": now})
        await db.leads.update_one({"lead_id": lead_id},
                                  {"$set": {"demo_status": "ready", "demo_template_id": template_id,
                                            "demo_slug": slug, "updated_at": now.isoformat()}})
        await post_agent_message(owner["user_id"], "rex",
            f"Handoff complete — Forge just finished the demo site for {lead['business_name']} and it's "
            f"live (hit 'Demo' on the Lead Board, path /api/p/{slug}). My opener: \"We already built your "
            "new website — want to see it?\" Nothing closes like a finished product.")
    except Exception as e:
        logger.exception("lead demo build failed")
        await db.leads.update_one({"lead_id": lead_id}, {"$set": {"demo_status": "error"}})
        await post_agent_message(owner["user_id"], "rex",
            f"Forge hit a snag building the demo for {lead['business_name']} ({type(e).__name__}). "
            "Flip the lead back to New and mark it Contacted again to retry.")
