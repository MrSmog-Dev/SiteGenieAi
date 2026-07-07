import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger
from database import db
from services.agents import (AGENT_MAP, BASE_CONTEXT, business_snapshot,
                             post_agent_message, run_forge_build, team_memory_context)
from services.llm import _call_llm


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json(raw) -> dict:
    return json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))


# ---------------- Shared team memory (memos) ----------------

async def create_memo(owner_id: str, from_agent: str, to_agents: list, kind: str,
                      content: str, source: str = "chat"):
    to_agents = [t for t in to_agents if t in AGENT_MAP and t != from_agent]
    content = (content or "").strip()
    if not to_agents or not content:
        return
    await db.team_memos.insert_one({
        "memo_id": f"memo_{uuid.uuid4().hex[:10]}", "user_id": owner_id,
        "from_agent": from_agent, "to_agents": to_agents, "kind": kind,
        "content": content[:1800], "source": source, "created_at": _now()})
    frm = AGENT_MAP.get(from_agent, {}).get("name", "Team")
    for t in to_agents:
        await post_agent_message(owner_id, t, f"📨 Memo from {frm} ({kind}): {content[:1800]}")
    try:
        from services.activity import log_activity
        to_names = ", ".join(AGENT_MAP.get(t, {}).get("name", t) for t in to_agents)
        await log_activity(owner_id, from_agent, "memo",
                           f"Sent a {kind} memo to {to_names}.", detail=content[:400],
                           link=f"/team?agent={to_agents[0]}")
    except Exception:
        pass


MEMO_DETECT_SYSTEM = (
    "You are SiteGenie's internal message router. You read an AI teammate's reply to the business Owner "
    "and detect REAL commitments to deliver something to other teammates, or finalized decisions the whole "
    "team must know. Teammate ids: titan, nova, atlas, ledger, quill, ivy, blaze, mara, rex, halo, forge, zephyr.\n"
    "Reply with ONLY a JSON object, no markdown fences:\n"
    '{"memos": [{"to": ["<teammate id>"], "kind": "handoff" or "decision", '
    '"content": "<self-contained message containing the ACTUAL substance being handed off (the full draft, '
    'plan or key points — not just a mention of it), max 1800 chars>"}]}\n'
    "Create a memo ONLY when the reply clearly commits to sending/sharing/handing something to a NAMED "
    "teammate (e.g. 'I'll send this to Quill'), or announces a finalized team decision. Vague suggestions "
    'like "you could ask Quill" are NOT memos. Most replies contain none: then reply {"memos": []}.'
)


async def detect_and_route_memos(owner_id: str, agent_id: str, owner_msg: str, reply: str):
    try:
        raw = await _call_llm(
            f"AGENT: {agent_id}\nOWNER SAID: {owner_msg[:800]}\nAGENT'S REPLY:\n{reply[:6000]}",
            MEMO_DETECT_SYSTEM, STRATEGY_MODEL)
        for m in (_parse_json(raw).get("memos") or [])[:3]:
            await create_memo(owner_id, agent_id, m.get("to") or [],
                              m.get("kind", "handoff"), str(m.get("content", "")))
    except Exception:
        logger.exception("memo detection failed")


# ---------------- War Room (team group chat) ----------------

async def post_war_room(owner_id: str, agent_id, content: str, role: str = "agent"):
    await db.war_room.update_one(
        {"user_id": owner_id},
        {"$push": {"messages": {"$each": [{"role": role, "agent_id": agent_id, "content": content, "ts": _now()}],
                                "$slice": -300}},
         "$set": {"updated_at": _now()}}, upsert=True)


PICK_SYSTEM = (
    "You pick which of SiteGenie's AI team should attend a War Room meeting. Titan (COO) always chairs and "
    "is already included. Agents: nova (Business Strategist), atlas (Data Analyst), ledger (Finance), "
    "quill (Copywriter), ivy (SEO), blaze (Social Media), mara (Email), rex (Sales & Leads), halo (Support), "
    "forge (Template Builder), zephyr (Growth). Given the topic, pick the 2-4 most relevant. "
    'Reply ONLY JSON: {"participants": ["id", ...]}'
)

EXTRACT_SYSTEM = (
    "Extract the final decision and action items from a SiteGenie War Room meeting transcript. "
    "Agent ids: titan, nova, atlas, ledger, quill, ivy, blaze, mara, rex, halo, forge, zephyr.\n"
    "Reply ONLY JSON:\n"
    '{"decision": "<one-line final decision>", "action_items": [{"owner": "<agent id>", '
    '"task": "<what to do>", "executable": "forge_build" | "ivy_blog" | "rex_hunt" | null, '
    '"brief": "<forge_build: the niche/theme to build; ivy_blog: article topic; '
    'rex_hunt: \'<City, ST> | <business category>\'; else null>", '
    '"count": <int, how many templates to build, default 1, max 5>}]}\n'
    '"executable" rules: use "forge_build" ONLY when the item is to actually build website template(s) for '
    'the Template Market. Use "ivy_blog" ONLY when the item is to write and publish a blog article. '
    'Use "rex_hunt" ONLY when the item is to actually hunt/scrape for local business leads in a real '
    "location. Everything else (copy, strategy, analysis, emails, pitches) is null — advisory assignments."
)

REX_PARSE_SYSTEM = (
    "Extract a location and business category from the task text. "
    'Reply ONLY JSON: {"location": "<City, ST>", "category": "<business category>"}'
)

NICHE_EXPAND_SYSTEM = (
    "You are Forge. Expand a build theme into N distinct, specific business niches for premium website "
    'templates. Reply ONLY JSON: {"niches": ["<2-6 word niche>", ...]} with exactly the requested count, '
    "no duplicates."
)


def _war_system(agent: dict, snapshot_json: str, team_ctx: str, memory_ctx: str = "") -> str:
    return (
        f"You are {agent['name']} — {agent['role']} — speaking in SiteGenie's WAR ROOM, a live team meeting "
        "attended by the business Owner and fellow AI teammates.\n"
        f"PERSONALITY: {agent['personality']}\n\n{BASE_CONTEXT}\n\n"
        f"{memory_ctx}\n\n"
        f"LIVE BUSINESS DATA:\n{snapshot_json}\n\n{team_ctx}\n\n"
        f"Rules: speak ONLY as {agent['name']} — never write other people's lines. React to what teammates "
        "already said, bring your specialty's angle, cite live numbers, disagree when warranted. Short and "
        "punchy — this is a meeting, not an essay. No markdown tables. Do NOT prefix your message with your "
        "name or any speaker label — the interface already shows who is talking."
    )


async def _agent_mem(owner_id: str, agent_id: str) -> str:
    try:
        from services.memory import agent_memory_context
        return await agent_memory_context(owner_id, agent_id)
    except Exception:
        return ""


async def _war_turn(agent: dict, system: str, transcript: str, instruction: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"war_{agent['id']}_{uuid.uuid4().hex[:8]}",
                   system_message=system).with_model("anthropic", STRATEGY_MODEL)
    prompt = f"MEETING TRANSCRIPT SO FAR:\n{transcript[-9000:]}\n\n{instruction}"
    return str(await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=90)).strip()


async def _set_meeting(meeting_id: str, **kw):
    await db.war_room_meetings.update_one(
        {"meeting_id": meeting_id}, {"$set": {**kw, "updated_at": _now()}})


async def run_war_room_meeting(meeting_id: str, owner_id: str, topic: str):
    try:
        await _set_meeting(meeting_id, status="running")
        snapshot_json = json.dumps(await business_snapshot(), default=str)
        team_ctx = await team_memory_context()
        raw = await _call_llm(f"Meeting topic: {topic}", PICK_SYSTEM, STRATEGY_MODEL)
        ids = [i for i in _parse_json(raw).get("participants", [])
               if i in AGENT_MAP and i != "titan"][:4] or ["nova", "atlas"]
        await _set_meeting(meeting_id, participants=["titan"] + ids)

        titan = AGENT_MAP["titan"]
        names = ", ".join(AGENT_MAP[i]["name"] for i in ids)
        transcript = f"Owner: {topic}"
        msg = await _war_turn(titan, _war_system(titan, snapshot_json, team_ctx, await _agent_mem(owner_id, "titan")), transcript,
                              f"Open the meeting: restate the objective in 1-2 lines and call on {names} "
                              "for input. Max 60 words.")
        transcript += f"\nTitan: {msg}"
        await post_war_room(owner_id, "titan", msg)

        for aid in ids:
            a = AGENT_MAP[aid]
            await _set_meeting(meeting_id, status="running")
            msg = await _war_turn(a, _war_system(a, snapshot_json, team_ctx, await _agent_mem(owner_id, aid)), transcript,
                                  f"It's your turn, {a['name']}. Give your specialty's take on the topic, "
                                  "reacting to what teammates said. Max 110 words.")
            transcript += f"\n{a['name']}: {msg}"
            await post_war_room(owner_id, aid, msg)

        closing = await _war_turn(titan, _war_system(titan, snapshot_json, team_ctx), transcript,
                                  "Close the meeting: state the final DECISION in one line, then numbered "
                                  "action items, each owned by a named teammate. Be decisive. Max 130 words.")
        transcript += f"\nTitan: {closing}"
        await post_war_room(owner_id, "titan", closing)

        data = _parse_json(await _call_llm(f"TRANSCRIPT:\n{transcript[-9000:]}", EXTRACT_SYSTEM, STRATEGY_MODEL))
        decision = str(data.get("decision", ""))[:400]
        items = (data.get("action_items") or [])[:8]
        created = await _create_tasks(owner_id, meeting_id, items)
        await create_memo(owner_id, "titan", ids, "decision",
                          f"War Room decision on '{topic}': {decision}. Action items: " +
                          "; ".join(f"{AGENT_MAP.get(i.get('owner'), {}).get('name', i.get('owner'))}: "
                                    f"{i.get('task')}" for i in items), source="war_room")
        await _set_meeting(meeting_id, status="done", decision=decision)
        from services.activity import log_activity
        await log_activity(owner_id, "titan", "meeting",
                           f"Chaired a War Room on '{topic[:60]}'.",
                           detail=f"Decision: {decision}", link="/team")
        # Auto-capture the outcome into persistent memory (shared brain + owners' open threads).
        try:
            from services.memory import record_war_room_decision
            await record_war_room_decision(owner_id, topic, decision, items)
        except Exception:
            logger.exception("war room decision memory capture failed")
        exec_n = sum(1 for t in created if t.get("executable"))
        if exec_n:
            await post_war_room(owner_id, "titan",
                                f"⚙️ {exec_n} executable task(s) queued — the team is on it. Watch the task board.")
            asyncio.create_task(process_team_tasks(owner_id))
    except Exception as e:
        logger.exception("war room meeting failed")
        await _set_meeting(meeting_id, status="error", error=str(e)[:300])
        await post_war_room(owner_id, "titan",
                            "The meeting hit a technical snag. Drop the topic again and we'll re-run it.")


async def _create_tasks(owner_id: str, meeting_id: str, items: list) -> list:
    docs = []
    for it in items:
        owner_agent = it.get("owner") if it.get("owner") in AGENT_MAP else "titan"
        ex = it.get("executable")
        if ex not in ("forge_build", "ivy_blog", "rex_hunt"):
            ex = None
        if ex == "forge_build":
            owner_agent = "forge"
        if ex == "ivy_blog":
            owner_agent = "ivy"
        if ex == "rex_hunt":
            owner_agent = "rex"
        try:
            count = min(max(int(it.get("count") or 1), 1), 5) if ex == "forge_build" else 1
        except (TypeError, ValueError):
            count = 1
        briefs = [str(it.get("brief") or it.get("task") or "")[:300]]
        if count > 1:
            try:
                raw = await _call_llm(f"Theme: {briefs[0]}. Give exactly {count} distinct niches.",
                                      NICHE_EXPAND_SYSTEM, STRATEGY_MODEL)
                got = _parse_json(raw).get("niches") or []
                briefs = [str(n)[:100] for n in got[:count]] if len(got) >= count else briefs * count
            except Exception:
                briefs = briefs * count
        for b in briefs:
            docs.append({"task_id": f"task_{uuid.uuid4().hex[:10]}", "user_id": owner_id,
                         "meeting_id": meeting_id, "owner_agent": owner_agent,
                         "task": str(it.get("task", ""))[:300], "executable": ex, "brief": b,
                         "status": "queued" if ex else "assigned",
                         "created_at": _now(), "updated_at": _now()})
        if not ex:
            await create_memo(owner_id, "titan", [owner_agent], "handoff",
                              f"War Room action item assigned to you: {it.get('task')}", source="war_room")
    if docs:
        await db.team_tasks.insert_many([dict(d) for d in docs])
    return docs


# ---------------- Task execution ----------------

async def process_team_tasks(owner_id: str):
    while True:
        task = await db.team_tasks.find_one_and_update(
            {"user_id": owner_id, "status": "queued",
             "executable": {"$in": ["forge_build", "ivy_blog", "rex_hunt"]}},
            {"$set": {"status": "running", "updated_at": _now()}},
            sort=[("created_at", 1)])
        if not task:
            return
        try:
            if task["executable"] == "forge_build":
                await _exec_forge(owner_id, task)
            elif task["executable"] == "rex_hunt":
                await _exec_rex(owner_id, task)
            else:
                await _exec_ivy(owner_id, task)
        except Exception as e:
            logger.exception("team task failed")
            await db.team_tasks.update_one(
                {"task_id": task["task_id"]},
                {"$set": {"status": "error", "error": str(e)[:200], "updated_at": _now()}})


async def _exec_forge(owner_id: str, task: dict):
    for _ in range(20):
        active = await db.agent_jobs.find_one(
            {"status": {"$in": ["queued", "designing", "building", "pricing"]}}, {"_id": 1})
        if not active:
            break
        await db.team_tasks.update_one({"task_id": task["task_id"]}, {"$set": {"updated_at": _now()}})
        await asyncio.sleep(30)
    job_id = f"forge_{uuid.uuid4().hex[:10]}"
    await db.agent_jobs.insert_one({"job_id": job_id, "user_id": owner_id, "agent_id": "forge",
                                    "brief": task["brief"], "status": "queued", "auto": True,
                                    "created_at": _now()})
    await run_forge_build(job_id, owner_id, task["brief"])
    job = await db.agent_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if job and job.get("status") == "done":
        r = job["result"]
        await db.team_tasks.update_one(
            {"task_id": task["task_id"]},
            {"$set": {"status": "done", "result": r, "updated_at": _now()}})
        await post_war_room(owner_id, "forge",
                            f'✅ Task done — built "{r["title"]}" for niche "{task["brief"]}" and listed it '
                            f'on the Market at ${r["price_usd"]} ({r["tier"]}).')
        await create_memo(owner_id, "forge", ["titan"], "update",
                          f'Completed War Room task: built and listed "{r["title"]}" at ${r["price_usd"]} '
                          f'({r["tier"]}) on the Template Market.', source="task")
    else:
        err = (job or {}).get("error", "unknown error")
        await db.team_tasks.update_one(
            {"task_id": task["task_id"]},
            {"$set": {"status": "error", "error": err, "updated_at": _now()}})
        await post_war_room(owner_id, "forge", f'❌ Build for "{task["brief"]}" failed: {err}')


async def _exec_ivy(owner_id: str, task: dict):
    from services.blog import run_ivy_blog
    await run_ivy_blog(owner_id)
    await db.team_tasks.update_one(
        {"task_id": task["task_id"]}, {"$set": {"status": "done", "updated_at": _now()}})
    await post_war_room(owner_id, "ivy",
                        f"✅ Task done — article written and published on the blog. (Task: {task['task']})")


async def rex_hunt_and_report(owner_id: str, location: str, category: str,
                              intro: str = "Hunt report") -> dict:
    from services.leads import hunt_places
    res = await hunt_places(location, category)
    new_leads = []
    if res["new_leads"]:
        new_leads = await db.leads.find(
            {"location": location, "category": category},
            {"_id": 0, "business_name": 1, "reviews_count": 1, "rating": 1, "tier": 1}
        ).sort("created_at", -1).to_list(res["new_leads"])
    if new_leads:
        lines = "\n".join(f"• {l['business_name']} — {l['reviews_count']} reviews, {l['rating']}★ "
                          f"({(l.get('tier') or 'warm').upper()})" for l in new_leads)
        msg = (f"🎯 {intro} — {category} in {location}: scanned {res['found']} businesses, bagged "
               f"{res['new_leads']} new no-website lead(s):\n{lines}\n"
               "They're on the Lead Board. Mark one Contacted and Forge auto-builds their demo site — "
               "nothing closes like a finished product.")
    else:
        msg = (f"🎯 {intro} — {category} in {location}: scanned {res['found']} businesses, no new qualified "
               f"no-website leads this time ({res['skipped_existing']} already on the board). "
               "I'll pick a fresh spot next hunt.")
    await post_agent_message(owner_id, "rex", msg)
    from services.activity import log_activity
    await log_activity(owner_id, "rex", "hunt",
                       f"Hunted {category} in {location} — {res['new_leads']} new lead(s) from "
                       f"{res['found']} scanned.", detail=msg[:600], link="/team?agent=rex")
    return res


async def _exec_rex(owner_id: str, task: dict):
    from config import GOOGLE_PLACES_API_KEY
    if not GOOGLE_PLACES_API_KEY:
        raise RuntimeError("Google Places API key not configured")
    brief = task.get("brief") or task.get("task") or ""
    if "|" in brief:
        location, category = [s.strip() for s in brief.split("|", 1)]
    else:
        parsed = _parse_json(await _call_llm(f"Task text: {brief}", REX_PARSE_SYSTEM, STRATEGY_MODEL))
        location, category = parsed["location"], parsed["category"]
    res = await rex_hunt_and_report(owner_id, location, category, intro="War Room hunt")
    await db.team_tasks.update_one(
        {"task_id": task["task_id"]},
        {"$set": {"status": "done", "updated_at": _now(),
                  "result": {"found": res["found"], "new_leads": res["new_leads"]}}})
    await post_war_room(owner_id, "rex",
                        f"✅ Task done — hunted {category} in {location}: {res['new_leads']} new lead(s) on "
                        f"the board from {res['found']} businesses scanned. Full report in my chat.")
    from services.automation import rex_autopilot
    await rex_autopilot(owner_id)
