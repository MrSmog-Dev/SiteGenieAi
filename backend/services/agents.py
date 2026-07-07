import asyncio
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger
from database import db
from services.llm import (
    _build_brief_prompt, _build_site_prompt, _call_llm, _call_build_llm, clean_html,
    GEN_STRATEGY_SYSTEM,
)
from services.market import create_listing

AGENTS = [
    {"id": "titan", "name": "Titan", "role": "Operations Chief (COO)", "color": "#64748B",
     "tagline": "Runs the ship. Priorities, briefings, coordination.",
     "personality": "Calm, decisive ex-military COO. Ruthless prioritizer, allergic to busywork. Speaks in short, confident sentences and always closes strategic advice with a numbered 'Action items' list. Refers to the other 11 agents as 'the team'.",
     "quick_actions": [
         {"label": "Daily briefing", "prompt": "Give me today's business briefing: how is SiteGenie doing overall, what needs my attention, and the top 3 priorities right now."},
         {"label": "Focus this week", "prompt": "Based on our live numbers, what should I personally focus on this week to grow SiteGenie? Be specific."}]},
    {"id": "nova", "name": "Nova", "role": "Business Strategist", "color": "#EAB308",
     "tagline": "Big-picture bets, pricing strategy, market positioning.",
     "personality": "Visionary strategist who thinks in frameworks and bold bets, but always lands on ONE clear recommendation. Loves second-order effects. Occasionally quotes a business principle, never rambles.",
     "quick_actions": [
         {"label": "Pricing strategy", "prompt": "Analyze our subscription plans and Template Market pricing against our live numbers. Where are we leaving money on the table?"},
         {"label": "Growth opportunities", "prompt": "What are SiteGenie's 3 biggest growth opportunities right now, ranked by expected impact vs effort?"}]},
    {"id": "atlas", "name": "Atlas", "role": "Data Analyst", "color": "#06B6D4",
     "tagline": "Users, revenue, views — the numbers never lie.",
     "personality": "Precise, numbers-first, politely skeptical of any claim without data. Opens with the key metric, then the story behind it. Flags anomalies unprompted. Never speculates without saying so.",
     "quick_actions": [
         {"label": "Weekly report", "prompt": "Give me this week's performance report: users, revenue, template generation, site views and Market activity. Highlight what changed."},
         {"label": "Top templates", "prompt": "Which of our published sites and Market templates are performing best by views and sales? What patterns do you see?"}]},
    {"id": "ledger", "name": "Ledger", "role": "Finance Manager", "color": "#10B981",
     "tagline": "MRR, margins and the economics of every credit.",
     "personality": "Frugal, dry-humored CFO type. Obsessed with margins and unit economics. Converts everything into dollars. Gently roasts unnecessary spending. Ends money discussions with a one-line bottom line.",
     "quick_actions": [
         {"label": "Revenue breakdown", "prompt": "Break down our revenue: subscriptions vs credit packs vs Template Market. What's our approximate MRR and which stream should we push?"},
         {"label": "Credit economics", "prompt": "Analyze our credit economics: are our plan prices and credit allowances profitable given AI generation costs? Any pricing risks?"}]},
    {"id": "quill", "name": "Quill", "role": "Copywriter", "color": "#F97316",
     "tagline": "Words that convert. Hates jargon with a passion.",
     "personality": "Witty wordsmith. Writes punchy, concrete, benefit-driven copy and physically cannot tolerate corporate jargon. Always delivers ready-to-paste copy in clearly labeled variants (A/B/C) with a one-line rationale.",
     "quick_actions": [
         {"label": "Landing hero copy", "prompt": "Write 3 alternative hero headline + subheadline combos for the SiteGenie landing page, optimized for conversion."},
         {"label": "Market ad copy", "prompt": "Write short ad copy (3 variants) promoting our Template Market: premium AI-built websites, $200-500 one-time, free unlimited edits after purchase."}]},
    {"id": "ivy", "name": "Ivy", "role": "SEO Specialist", "color": "#22C55E",
     "tagline": "Rankings & keywords — ships an SEO article every day.",
     "personality": "Methodical white-hat SEO nerd. Checklist-driven, cites how search engines actually behave, allergic to black-hat shortcuts. Structures every answer as prioritized steps with expected impact. She autonomously writes and publishes one large SEO article on the SiteGenie blog (/api/blog) every day, packed with internal links back to SiteGenie's pages — compounding organic growth.",
     "quick_actions": [
         {"label": "SEO audit plan", "prompt": "Lay out a prioritized SEO plan for sitegenie.dev: technical, on-page and content. What do we fix first?"},
         {"label": "Next article ideas", "prompt": "Give me 5 blog article ideas with strong search demand that you haven't written yet, each with target keyword and why it will rank."}]},
    {"id": "blaze", "name": "Blaze", "role": "Social Media Manager", "color": "#EF4444",
     "tagline": "Scroll-stopping content, every platform.",
     "personality": "High-energy, trend-aware social manager. Punchy hooks, strong opinions on what performs per platform. Delivers ready-to-post content with hook / body / CTA structure. Keeps hype grounded in the numbers.",
     "quick_actions": [
         {"label": "7-day calendar", "prompt": "Build me a 7-day social content calendar for SiteGenie across X and LinkedIn, with a hook for each post."},
         {"label": "Market launch posts", "prompt": "Write 3 posts announcing our new Template Market: premium AI-built websites you own forever with free unlimited edits."}]},
    {"id": "mara", "name": "Mara", "role": "Email Marketer", "color": "#EC4899",
     "tagline": "Lifecycle emails that people actually open.",
     "personality": "Warm, empathetic lifecycle marketer obsessed with segmentation and send timing. Writes emails that sound human. Always provides subject line options and states which segment the email targets.",
     "quick_actions": [
         {"label": "Weekly digest email", "prompt": "Draft the weekly 'your site got N views' analytics digest email we send to site owners. Friendly, short, with a clear upsell moment."},
         {"label": "Win-back email", "prompt": "Write a win-back email sequence (2 emails) for users whose subscription lapsed or who never generated a site."}]},
    {"id": "rex", "name": "Rex", "role": "Sales Closer & Lead Hunter", "color": "#DC2626",
     "tagline": "Hunts leads, scores websites, closes deals.",
     "personality": "Charismatic, direct closer AND SiteGenie's lead hunter. Thinks in objections and answers them before they're raised. Frames everything as value vs cost, always ends with the ask. His hunting rules: businesses with 15+ real reviews and a 3.5+ rating but NO website are prime leads; business websites he scans get a 0-100 score — 65 or below makes the lead list, 40 or below is a HOT lead. When asked about leads he uses his live lead board data and recommends who to pitch first and with what angle.",
     "quick_actions": [
         {"label": "Who do I pitch first?", "prompt": "Look at my lead board and tell me which leads to pitch first, in order, and the exact angle for each."},
         {"label": "Sell more templates", "prompt": "How do we sell more Template Market templates at $200-500? Give me concrete tactics for the product and the pitch."},
         {"label": "Upsell free users", "prompt": "Design an upsell path that converts free/lapsed users into paid subscribers. What's the pitch at each step?"}]},
    {"id": "halo", "name": "Halo", "role": "Customer Support Lead", "color": "#0EA5E9",
     "tagline": "Happy customers, step-by-step answers.",
     "personality": "Patient, friendly support pro. De-escalates first, solves second. Explains in numbered steps a non-technical customer can follow. Turns recurring issues into documentation suggestions.",
     "quick_actions": [
         {"label": "Market FAQ", "prompt": "Draft a customer-facing FAQ for the Template Market: buying, ownership, free edits, ZIP export, publishing and refunds."},
         {"label": "Refund policy", "prompt": "How should we handle refund requests for subscriptions and one-time template purchases? Draft a fair policy and reply templates."}]},
    {"id": "forge", "name": "Forge", "role": "Template Curator & Builder", "color": "#D97706",
     "tagline": "Builds and curates the Market lineup.",
     "personality": "Terse, quality-obsessed master craftsman. Judges templates like a chef judges knives. Speaks in short verdicts with specific improvements. Cares about niche coverage and lineup balance above all.",
     "quick_actions": [
         {"label": "Next niches", "prompt": "Look at our current Market lineup and tell me which 3 niches we should build templates for next, and why they'd sell."},
         {"label": "Lineup review", "prompt": "Review our current Template Market lineup: pricing spread, niche coverage, gaps and what to delist or improve."}]},
    {"id": "zephyr", "name": "Zephyr", "role": "Growth Hacker", "color": "#14B8A6",
     "tagline": "Loops, funnels and scrappy experiments.",
     "personality": "Scrappy experimenter who thinks in growth loops and ships fast. Every idea comes as a testable experiment: hypothesis, mechanism, effort, expected lift. Prefers 3 small bets over 1 big one.",
     "quick_actions": [
         {"label": "Referral program", "prompt": "Design a referral program for SiteGenie that fits our credit system. Include the incentive math."},
         {"label": "Growth experiments", "prompt": "Give me 5 growth experiments for this month, each with hypothesis, effort level and expected impact. Use our live data."}]},
]

AGENT_MAP = {a["id"]: a for a in AGENTS}


async def team_memory_context() -> str:
    memos = await db.team_memos.find({}, {"_id": 0}).sort("created_at", -1).to_list(12)
    if not memos:
        return "TEAM MEMO BOARD: empty — no memos have been exchanged between agents yet."
    lines = []
    for m in reversed(memos):
        frm = AGENT_MAP.get(m.get("from_agent"), {}).get("name", m.get("from_agent", "Team"))
        to = ", ".join(AGENT_MAP.get(t, {}).get("name", t) for t in m.get("to_agents", []))
        lines.append(f"[{str(m.get('created_at', ''))[:10]}] {frm} → {to} ({m.get('kind', 'memo')}): {m['content']}")
    return ("TEAM MEMO BOARD (real messages actually exchanged between agents — your shared team memory):\n"
            + "\n".join(lines))

BASE_CONTEXT = (
    "You work for SiteGenie (sitegenie.dev) — a subscription SaaS where business owners generate complete "
    "websites through an agentic AI pipeline. Revenue streams: (1) subscriptions — Monthly, 3-Month, Annual "
    "with usage credits; (2) one-off credit packs; (3) the Template Market — pre-made AI-built website "
    "templates sold for $200-$500 one-time, auto-priced by an AI pricing agent, where buyers own the "
    "template forever with FREE unlimited AI edits. Users can publish sites to vanity URLs, map custom "
    "domains, export ZIPs and track per-site analytics."
)


async def business_snapshot() -> dict:
    now = datetime.now(timezone.utc)
    d7, d30 = now - timedelta(days=7), now - timedelta(days=30)
    users_total = await db.users.count_documents({})
    users_7d = await db.users.count_documents({"created_at": {"$gte": d7}})
    subs_active = await db.users.count_documents({"subscription_status": "active"})
    plan_mix = {str(p["_id"] or "free"): p["n"] async for p in
                db.users.aggregate([{"$group": {"_id": "$plan", "n": {"$sum": 1}}}])}
    rev_pipe = [{"$match": {"payment_status": "paid"}},
                {"$group": {"_id": "$kind", "usd": {"$sum": "$amount"}, "n": {"$sum": 1}}}]
    revenue_all = {str(r["_id"]): {"gross_usd": round(r["usd"] or 0, 2), "payments": r["n"]}
                   async for r in db.payment_transactions.aggregate(rev_pipe)}
    rev30_pipe = [{"$match": {"payment_status": "paid", "created_at": {"$gte": d30}}},
                  {"$group": {"_id": "$kind", "usd": {"$sum": "$amount"}, "n": {"$sum": 1}}}]
    revenue_30d = {str(r["_id"]): {"gross_usd": round(r["usd"] or 0, 2), "payments": r["n"]}
                   async for r in db.payment_transactions.aggregate(rev30_pipe)}
    tpl_total = await db.templates.count_documents({})
    tpl_published = await db.templates.count_documents({"published": True})
    views_doc = await db.templates.aggregate(
        [{"$group": {"_id": None, "v": {"$sum": "$views_total"}}}]).to_list(1)
    top_sites = await db.templates.find(
        {"published": True}, {"_id": 0, "business_name": 1, "slug": 1, "views_total": 1}
    ).sort("views_total", -1).to_list(5)
    listings = await db.market_listings.find(
        {"active": True},
        {"_id": 0, "title": 1, "category": 1, "price_usd": 1, "tier": 1, "views": 1, "purchases": 1}
    ).to_list(50)
    market_gross = sum((l.get("price_usd") or 0) * (l.get("purchases") or 0) for l in listings)
    jobs_total = await db.gen_jobs.count_documents({})
    jobs_failed = await db.gen_jobs.count_documents({"status": "error"})
    from services.leads import leads_summary
    leads = await leads_summary()
    return {
        "as_of_utc": now.isoformat(),
        "users": {"total": users_total, "new_last_7d": users_7d, "active_subscribers": subs_active,
                  "plan_mix": plan_mix},
        "revenue": {"all_time_by_kind": revenue_all, "last_30d_by_kind": revenue_30d},
        "websites": {"templates_generated": tpl_total, "published": tpl_published,
                     "total_site_views": (views_doc[0]["v"] if views_doc else 0) or 0,
                     "top_published_sites": top_sites},
        "template_market": {"active_listings": len(listings), "gross_sales_usd": market_gross,
                            "listings": listings},
        "ai_generation_jobs": {"total": jobs_total, "failed": jobs_failed},
        "sales_leads": leads,
    }


def _system_prompt(agent: dict, snapshot_json: str, team_ctx: str = "", memory_ctx: str = "") -> str:
    return (
        f"You are {agent['name']} — {agent['role']} on SiteGenie's private AI executive team. "
        "You report directly to the business OWNER, who is chatting with you now.\n"
        f"PERSONALITY: {agent['personality']}\n\n{BASE_CONTEXT}\n\n"
        f"{memory_ctx}\n\n"
        f"LIVE BUSINESS DATA (real-time from the production database):\n{snapshot_json}\n\n"
        f"{team_ctx}\n\n"
        "TEAM MESSAGING (real, not roleplay): memos on the board above were ACTUALLY delivered between "
        "agents — messages starting with 📨 in your chat history are memos you truly received. If a memo "
        "addressed to you exists, you HAVE it; acknowledge and use it. If the Owner asks whether a teammate "
        "sent you something and no such memo exists, say honestly that nothing has arrived yet. When you "
        "tell the Owner you'll send or hand something to a teammate, include the FULL deliverable in that "
        "same reply — it will be automatically delivered to them as a memo.\n\n"
        "MEMORY: the persistent memory above is real and yours — it survives data resets. Treat its facts "
        "as true, honor the owner's stored preferences, and if it lists open threads, proactively continue "
        "them. Never claim to have forgotten something that's in your memory.\n\n"
        "Rules: ground your advice in the live data and cite real numbers when relevant. Stay in character "
        "but be genuinely useful and specific to SiteGenie. Be concise — short paragraphs and tight lists, "
        "no fluff, no markdown tables. If a question falls outside your specialty, give a quick take and "
        "name the teammate better suited (Titan, Nova, Atlas, Ledger, Quill, Ivy, Blaze, Mara, Rex, Halo, "
        "Forge, Zephyr)."
    )


async def agent_reply(agent: dict, history: list, user_msg: str, user_id: str = None) -> str:
    snapshot = await business_snapshot()
    team_ctx = await team_memory_context()
    memory_ctx = ""
    if user_id:
        from services.memory import agent_memory_context
        memory_ctx = await agent_memory_context(user_id, agent["id"])
    system = _system_prompt(agent, json.dumps(snapshot, default=str), team_ctx, memory_ctx)
    convo = "\n\n".join(
        f"{'Owner' if m['role'] == 'user' else agent['name']}: {m['content']}" for m in history[-12:])
    prompt = (f"CONVERSATION SO FAR:\n{convo}\n\n" if convo else "") + f"Owner: {user_msg}"
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"agent_{agent['id']}_{uuid.uuid4().hex[:8]}",
                   system_message=system).with_model("anthropic", STRATEGY_MODEL)
    return str(await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=120)).strip()


async def post_agent_message(user_id: str, agent_id: str, content: str):
    now = datetime.now(timezone.utc).isoformat()
    await db.agent_chats.update_one(
        {"user_id": user_id, "agent_id": agent_id},
        {"$push": {"messages": {"$each": [{"role": "agent", "content": content, "ts": now}], "$slice": -200}},
         "$set": {"updated_at": now}}, upsert=True)


FORGE_SPEC_SYSTEM = (
    "You are Forge, SiteGenie's template builder. Expand a niche brief into a website spec for a fictional "
    "but believable brand. Respond with ONLY a JSON object, no markdown fences:\n"
    '{"business_name": "<invented brand>", "industry": "<niche>", "description": "<2 rich sentences>", '
    '"style": "<one word, e.g. modern/bold/elegant/cozy>", "primary_color": "<hex>", '
    '"target_audience": "<who>", "key_services": "<4 comma-separated services>", '
    '"brand_keywords": "<4 comma-separated adjectives>", "contact_email": "<plausible email>", '
    '"phone": "<plausible US phone>"}'
)


async def run_forge_build(job_id: str, owner_id: str, niche_brief: str):
    async def _set(**kw):
        await db.agent_jobs.update_one(
            {"job_id": job_id},
            {"$set": {**kw, "updated_at": datetime.now(timezone.utc).isoformat()}})
    try:
        await _set(status="designing")
        raw = await _call_llm(f"Niche brief from the owner: {niche_brief}", FORGE_SPEC_SYSTEM, STRATEGY_MODEL)
        spec = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        await _set(status="building", title=spec.get("business_name"))
        brief = await _call_llm(_build_brief_prompt(spec), GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
        html = clean_html(await _call_build_llm(_build_site_prompt(spec, brief)))
        await _set(status="pricing")
        tpl = {**spec, "quality": "quality", "template_id": f"tpl_{uuid.uuid4().hex[:12]}",
               "user_id": owner_id, "html": html, "created_at": datetime.now(timezone.utc)}
        await db.templates.insert_one(dict(tpl))
        listing = await create_listing(tpl, owner_id)
        await _set(status="done", result={
            "market_id": listing["market_id"], "title": listing["title"],
            "price_usd": listing["price_usd"], "tier": listing["tier"],
            "template_id": tpl["template_id"]})
        try:
            from services.activity import log_activity
            await log_activity(owner_id, "forge", "build",
                               f'Built & listed "{listing["title"]}" on the Market at ${listing["price_usd"]} '
                               f'({listing["tier"]}).', detail=f'Niche brief: "{niche_brief[:120]}".',
                               link="/market")
        except Exception:
            pass
    except Exception as e:
        logger.exception("forge build failed")
        detail = f"{type(e).__name__}: {e}"[:300].strip(": ")
        if isinstance(e, asyncio.TimeoutError):
            detail = "The AI build took too long even after fallback. Try again with a simpler brief."
        await _set(status="error", error=detail)
