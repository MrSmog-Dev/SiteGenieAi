"""Ivy SEO Autopilot — keyword engine, content calendar, article scoring, GEO/technical audits,
internal-link/pillar map, and community (Reddit) opportunity finder.

All LLM-driven (Haiku) + our own stack — no paid SEO APIs. Owner-scoped. Every action logs to Team Pulse.
"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone, timedelta

from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger
from database import db
from services.llm import _call_llm
from services.activity import log_activity


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json(raw) -> dict:
    m = re.search(r"\{[\s\S]*\}", str(raw))
    return json.loads(m.group(0)) if m else {}


SITE_CONTEXT = (
    "SiteGenie (sitegenie-ai.com) is an AI website builder for small-business owners: describe your "
    "business and it generates a complete, premium, high-converting website in minutes. Revenue: "
    "subscriptions (usage credits), a Template Market of premium one-of-one websites ($200-500, owned "
    "forever with free AI edits), publishing to vanity URLs + custom domains, ZIP export, analytics. "
    "Target audience: small-business owners, founders, freelancers, agencies searching Google/AI for help "
    "with websites, online presence, local marketing and SEO."
)


# ---------------- 1. Keyword engine + 30-day content calendar ----------------

KEYWORD_SYSTEM = (
    "You are Ivy, SiteGenie's SEO strategist. Build a keyword-driven content plan that wins visibility on "
    "BOTH Google and AI search (ChatGPT/Perplexity/Gemini).\n"
    f"{SITE_CONTEXT}\n"
    "Produce a plan of high-intent topics a small-business owner would search, mixing informational, "
    "commercial and comparison intent, plus 'prompts people ask AI assistants'. Avoid topics already "
    "covered (provided). Reply with ONLY JSON, no markdown:\n"
    '{"plan": [{"day": <1..N>, "title": "<compelling SEO headline, <=60 chars>", '
    '"target_keyword": "<primary keyword>", "secondary_keywords": ["<kw>", "<kw>"], '
    '"intent": "informational"|"commercial"|"comparison"|"transactional", '
    '"format": "how-to"|"listicle"|"guide"|"comparison"|"faq", '
    '"ai_prompt": "<a natural question someone would ask ChatGPT that this should rank for>", '
    '"pillar": "<one of: AI website building, Templates & design, Local/SEO growth, Getting customers>"}]}'
)


async def build_content_calendar(owner_id: str, days: int = 30) -> dict:
    existing = await db.blog_posts.find({}, {"_id": 0, "title": 1}).sort("created_at", -1).to_list(60)
    planned = await db.seo_calendar.find(
        {"user_id": owner_id, "status": {"$in": ["planned", "published"]}},
        {"_id": 0, "title": 1}).to_list(120)
    avoid = [p["title"] for p in existing] + [p["title"] for p in planned]
    raw = await _call_llm(
        f"Plan {days} days of content. Avoid these existing/planned titles: {avoid}. "
        f"Return exactly {days} plan items numbered day 1..{days}.",
        KEYWORD_SYSTEM, STRATEGY_MODEL)
    plan = _parse_json(raw).get("plan", [])[:days]
    start = datetime.now(timezone.utc)
    docs = []
    for i, item in enumerate(plan):
        docs.append({
            "cal_id": f"cal_{uuid.uuid4().hex[:10]}", "user_id": owner_id,
            "title": str(item.get("title", ""))[:90],
            "target_keyword": str(item.get("target_keyword", ""))[:80],
            "secondary_keywords": [str(k)[:60] for k in (item.get("secondary_keywords") or [])][:4],
            "intent": item.get("intent", "informational"),
            "format": item.get("format", "guide"),
            "ai_prompt": str(item.get("ai_prompt", ""))[:200],
            "pillar": str(item.get("pillar", ""))[:60],
            "scheduled_for": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
            "status": "planned", "created_at": _now(),
        })
    if docs:
        await db.seo_calendar.insert_many([dict(d) for d in docs])
    await log_activity(owner_id, "ivy", "seo",
                       f"Built a {len(docs)}-topic content calendar from keyword research.",
                       detail="Topics prioritized by search + AI-visibility intent.",
                       link="/team?agent=ivy&seo=1")
    return {"created": len(docs)}


async def get_calendar(owner_id: str) -> list:
    return await db.seo_calendar.find(
        {"user_id": owner_id}, {"_id": 0}).sort("scheduled_for", 1).to_list(120)


async def next_planned_topic(owner_id: str) -> dict | None:
    return await db.seo_calendar.find_one_and_update(
        {"user_id": owner_id, "status": "planned"},
        {"$set": {"status": "writing", "started_at": _now()}},
        sort=[("scheduled_for", 1)])


async def mark_topic_published(owner_id: str, cal_id: str, slug: str, score: int):
    await db.seo_calendar.update_one(
        {"cal_id": cal_id, "user_id": owner_id},
        {"$set": {"status": "published", "slug": slug, "score": score, "published_at": _now()}})


# ---------------- 2. Article quality score (BLG-style checklist) ----------------

def score_article(post: dict) -> dict:
    """Deterministic /100 SEO quality score on the babylovegrowth-style checklist."""
    body = post.get("body", "") or ""
    low = body.lower()
    kws = [k.lower() for k in (post.get("keywords") or [])]
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", body)))
    checks = []

    def add(name, ok, pts):
        checks.append({"check": name, "points": pts if ok else 0, "max": pts})

    add("Strong word count (1200+)", words >= 1200, 12)
    add("Clear heading structure (h2/h3)", low.count("<h2") >= 3, 10)
    add("Table of contents", "table of contents" in low or 'id="toc"' in low or "#key-takeaways" in low, 8)
    add("TL;DR / key takeaways", "tl;dr" in low or "key takeaway" in low or "<table" in low, 8)
    add("Comparison or data table", "<table" in low, 6)
    add("FAQ section", "faq" in low or "frequently asked" in low, 8)
    add("Internal links (3+)", len(re.findall(r'href="/(?!/)', body)) + low.count('href="/api/blog/') >= 3, 12)
    add("External citations (1+)", bool(re.search(r'href="https?://', body)), 8)
    add("Statistics / data points", bool(re.search(r"\d{1,3}%|\b\d{2,}\b", body)), 8)
    add("Image alt texts", body.count("alt=") >= 1 or body.count("<figure") >= 1, 6)
    add("Meta description set", bool(post.get("meta_description")), 6)
    add("Semantic keyword coverage", sum(1 for k in kws if k and k in low) >= max(2, len(kws) // 2), 8)
    score = sum(c["points"] for c in checks)
    return {"score": score, "max": 100, "checks": checks, "word_count": words}


ARTICLE_IMPROVE_SYSTEM = (
    "You are Ivy, SiteGenie's SEO editor. You are given an article body (HTML) and a list of SEO gaps to "
    "fix. Return the FULL improved article body HTML only (no commentary, no code fences), keeping all "
    "good existing content and ADDING what's missing. Allowed tags: h2,h3,p,ul,ol,li,a,strong,em,table,"
    "thead,tbody,tr,th,td,blockquote,figure,figcaption. Keep internal links to /, /market, /pricing and "
    "any existing /api/blog/ links. Add a short 'Key takeaways' table near the top and an FAQ with 3-4 "
    "Q&As at the end if missing. Keep it genuinely useful and specific — no fluff."
)


async def improve_article(post: dict, gaps: list) -> str:
    prompt = (f"SEO GAPS TO FIX: {', '.join(gaps)}\n\nTITLE: {post.get('title')}\n"
              f"TARGET KEYWORDS: {', '.join(post.get('keywords', []))}\n\nARTICLE BODY:\n{post.get('body','')}")
    raw = await _call_llm(prompt, ARTICLE_IMPROVE_SYSTEM, STRATEGY_MODEL)
    out = re.sub(r"^```(?:html)?|```$", "", str(raw).strip(), flags=re.M).strip()
    out = re.sub(r"<script[\s\S]*?</script>", "", out, flags=re.I)
    return out if len(out) > 400 else post.get("body", "")


# ---------------- 3. GEO / AI-visibility audit + technical SEO audit ----------------

GEO_SYSTEM = (
    "You simulate how a modern AI assistant (ChatGPT/Perplexity/Gemini) would answer a buyer's question, "
    "then judge whether SiteGenie (an AI website builder at sitegenie-ai.com) would plausibly be "
    "recommended/cited given its public footprint. Be honest and critical, not promotional.\n"
    "Reply ONLY JSON: {\"answer\": \"<how an AI would answer in 2-3 sentences, naming the kinds of tools "
    "it would cite>\", \"sitegenie_cited\": true|false, \"visibility\": <0-100 estimate of SiteGenie's "
    "current AI-search visibility for this query>, \"why\": \"<1 sentence>\", "
    "\"content_gap\": \"<a specific article/topic SiteGenie should publish to earn this citation>\"}"
)


async def geo_audit(owner_id: str, query: str) -> dict:
    raw = await _call_llm(f"Buyer question: {query}", GEO_SYSTEM, STRATEGY_MODEL)
    data = _parse_json(raw)
    result = {
        "query": query,
        "answer": str(data.get("answer", ""))[:600],
        "sitegenie_cited": bool(data.get("sitegenie_cited")),
        "visibility": int(data.get("visibility") or 0),
        "why": str(data.get("why", ""))[:300],
        "content_gap": str(data.get("content_gap", ""))[:200],
        "created_at": _now(),
    }
    await db.seo_audits.insert_one({"audit_id": f"geo_{uuid.uuid4().hex[:10]}",
                                    "user_id": owner_id, "kind": "geo", **result})
    await log_activity(owner_id, "ivy", "seo",
                       f"GEO audit: '{query[:50]}' — AI visibility {result['visibility']}/100"
                       + (" (cited ✓)" if result["sitegenie_cited"] else " (not cited)"),
                       detail=result["why"], link="/team?agent=ivy&seo=1")
    return result


TECH_AUDIT_SYSTEM = (
    "You are Ivy, an SEO/GEO technical auditor. Given a page's extracted signals, give a prioritized, "
    "specific fix list a non-expert can action. Reply ONLY JSON: {\"summary\": \"<1-2 sentences>\", "
    "\"fixes\": [{\"issue\": \"<what>\", \"why\": \"<impact on Google/AI ranking>\", "
    "\"priority\": \"high\"|\"medium\"|\"low\"}]}"
)


def _tech_signals(html: str, meta: dict) -> dict:
    low = html.lower()
    title = re.search(r"<title[^>]*>([^<]{0,300})</title>", html, re.I)
    h1 = re.findall(r"<h1", low)
    imgs = re.findall(r"<img\b[^>]*>", low)
    imgs_no_alt = [i for i in imgs if "alt=" not in i]
    return {
        "https": meta.get("https"),
        "title": title.group(1).strip() if title else "",
        "has_meta_description": 'name="description"' in low or "name='description'" in low,
        "has_canonical": 'rel="canonical"' in low,
        "has_og": 'property="og:' in low,
        "has_viewport": "viewport" in low,
        "has_json_ld": "application/ld+json" in low,
        "h1_count": len(h1),
        "h2_count": low.count("<h2"),
        "img_count": len(imgs),
        "img_missing_alt": len(imgs_no_alt),
        "word_count": len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", html))),
        "load_kb": meta.get("size_kb"),
    }


async def technical_audit(owner_id: str, url: str) -> dict:
    from services.leads import _fetch, _blocked_host
    if await asyncio.to_thread(_blocked_host, __import__("httpx").URL(
            url if "://" in url else "https://" + url).host):
        raise ValueError("That host can't be scanned.")
    fetched = await _fetch(url if "://" in url else "https://" + url)
    signals = _tech_signals(fetched["html"], fetched)
    raw = await _call_llm(f"Page signals: {json.dumps(signals)}", TECH_AUDIT_SYSTEM, STRATEGY_MODEL)
    data = _parse_json(raw)
    result = {"url": fetched["final_url"], "signals": signals,
              "summary": str(data.get("summary", ""))[:400],
              "fixes": (data.get("fixes") or [])[:12], "created_at": _now()}
    await db.seo_audits.insert_one({"audit_id": f"tech_{uuid.uuid4().hex[:10]}",
                                    "user_id": owner_id, "kind": "technical", **result})
    high = sum(1 for f in result["fixes"] if f.get("priority") == "high")
    await log_activity(owner_id, "ivy", "seo",
                       f"Technical SEO audit of {signals['title'][:40] or url} — {high} high-priority fix(es).",
                       detail=result["summary"], link="/team?agent=ivy&seo=1")
    return result


async def recent_audits(owner_id: str, limit: int = 20) -> list:
    return await db.seo_audits.find({"user_id": owner_id}, {"_id": 0, "signals": 0}).sort(
        "created_at", -1).to_list(limit)


# ---------------- 4. Internal link / pillar map ----------------

async def internal_link_map(owner_id: str) -> dict:
    posts = await db.blog_posts.find({}, {"_id": 0, "title": 1, "slug": 1, "keywords": 1, "body": 1}).sort(
        "created_at", -1).to_list(80)
    if not posts:
        return {"pillars": [], "total_posts": 0, "suggestions": []}
    lite = [{"title": p["title"], "slug": p["slug"], "keywords": p.get("keywords", [])} for p in posts]
    raw = await _call_llm(
        "Group these SiteGenie blog posts into 3-5 topical PILLARS and, for each post, suggest 2-3 other "
        "posts it should internally link to (by slug) to build topical authority (pillar/cluster model). "
        f"Posts: {json.dumps(lite)[:6000]}\n"
        'Reply ONLY JSON: {"pillars": [{"name": "<pillar>", "slugs": ["<slug>"]}], '
        '"suggestions": [{"from": "<slug>", "link_to": ["<slug>"]}]}',
        "You are Ivy, an internal-linking strategist. Be concrete.", STRATEGY_MODEL)
    data = _parse_json(raw)
    # count existing internal links per post for a quick health signal
    for p in posts:
        p["_links"] = p.get("body", "").count('href="/api/blog/')
    linked = sum(1 for p in posts if p["_links"] > 0)
    return {"pillars": (data.get("pillars") or [])[:6], "total_posts": len(posts),
            "posts_with_links": linked, "suggestions": (data.get("suggestions") or [])[:40]}


# ---------------- 5. Reddit / community opportunity finder ----------------

REDDIT_SYSTEM = (
    "You are Ivy, SiteGenie's community-SEO strategist. Suggest high-intent Reddit/forum discussion angles "
    "where SiteGenie could be genuinely helpful (AI assistants increasingly cite Reddit). For each, give a "
    "likely subreddit, the kind of question being asked, and a GENUINELY HELPFUL, non-spammy reply draft "
    "that leads with real value and mentions SiteGenie only if truly relevant.\n"
    f"{SITE_CONTEXT}\n"
    'Reply ONLY JSON: {"opportunities": [{"subreddit": "r/<name>", "angle": "<the question/thread type>", '
    '"why": "<why high-intent>", "reply_draft": "<2-4 sentence helpful reply>"}]}'
)


async def reddit_opportunities(owner_id: str, count: int = 5) -> dict:
    raw = await _call_llm(f"Give {count} community opportunities.", REDDIT_SYSTEM, STRATEGY_MODEL)
    opps = (_parse_json(raw).get("opportunities") or [])[:count]
    await log_activity(owner_id, "ivy", "seo",
                       f"Found {len(opps)} community (Reddit) visibility opportunities.",
                       detail="High-intent threads + ready-to-post helpful replies.",
                       link="/team?agent=ivy&seo=1")
    return {"opportunities": opps}


# ---------------- Dashboard aggregate ----------------

async def seo_overview(owner_id: str) -> dict:
    cal = await db.seo_calendar.count_documents({"user_id": owner_id})
    planned = await db.seo_calendar.count_documents({"user_id": owner_id, "status": "planned"})
    published = await db.blog_posts.count_documents({})
    scored = await db.blog_posts.find({"seo_score": {"$exists": True}},
                                      {"_id": 0, "seo_score": 1}).to_list(200)
    avg = round(sum(p["seo_score"] for p in scored) / len(scored)) if scored else None
    last_geo = await db.seo_audits.find_one({"user_id": owner_id, "kind": "geo"},
                                            {"_id": 0}, sort=[("created_at", -1)])
    return {"calendar_total": cal, "calendar_planned": planned, "articles_published": published,
            "avg_article_score": avg, "scored_count": len(scored),
            "last_geo_visibility": (last_geo or {}).get("visibility")}
