import asyncio
import ipaddress
import json
import os
import re
import socket
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, GOOGLE_PLACES_API_KEY, logger
from database import db

LEAD_STATUSES = ("new", "contacted", "won", "lost")

PUBLIC_BASE = next((o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()), "")


def _tier(score: int) -> str | None:
    if score <= 40:
        return "hot"
    if score <= 65:
        return "warm"
    return None


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = f"https://{url}"
    return url


def _blocked_host(host: str) -> bool:
    """True if the host is private/internal — checked by NAME and by every resolved IP."""
    host = (host or "").lower().strip(".")
    if not host or host == "localhost" or host.endswith((".local", ".internal")):
        return True
    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None)]
        except (socket.gaierror, ValueError):
            return True
    return any(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
               or ip.is_multicast or ip.is_unspecified for ip in ips)


async def _fetch(url: str) -> dict:
    start = time.monotonic()
    async with httpx.AsyncClient(follow_redirects=False, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"}) as client:
        r = None
        for _ in range(4):
            if await asyncio.to_thread(_blocked_host, httpx.URL(url).host):
                raise RuntimeError("Blocked host")
            r = await client.get(url)
            loc = r.headers.get("location")
            if r.status_code in (301, 302, 303, 307, 308) and loc:
                url = str(httpx.URL(url).join(loc))
                continue
            break
    return {"html": r.text[:800_000], "final_url": str(r.url), "status": r.status_code,
            "https": str(r.url).startswith("https://"), "elapsed": round(time.monotonic() - start, 2),
            "size_kb": round(len(r.content) / 1024, 1)}


def _deterministic_checks(html: str, meta: dict) -> list:
    low = html.lower()
    checks = []

    def add(name, ok, pts, note=""):
        checks.append({"check": name, "points": pts if ok else 0, "max": pts, "note": note})

    add("Secure HTTPS", meta["https"], 8)
    add("Mobile-ready viewport", "viewport" in low and "<meta" in low, 10)
    add("Responsive design signals",
        "@media" in low or any(f in low for f in ("tailwind", "bootstrap", "display:flex", "display: flex", "grid-template")), 8)
    title = re.search(r"<title[^>]*>([^<]{1,300})</title>", html, re.I)
    add("Descriptive page title", bool(title and 5 <= len(title.group(1).strip()) <= 80), 6)
    add("SEO meta description", 'name="description"' in low or "name='description'" in low, 6)
    add("Social share (OG) tags", 'property="og:' in low or "property='og:" in low, 4)
    add("Favicon", 'rel="icon"' in low or 'rel="shortcut icon"' in low or 'rel="apple-touch-icon"' in low, 2)
    contact = "tel:" in low or "mailto:" in low or re.search(r"\(\d{3}\)\s?\d{3}[-.\s]?\d{4}", html)
    add("Contact info visible", bool(contact), 8)
    year_now = datetime.now(timezone.utc).year
    years = [int(y) for pair in re.findall(r"(?:©|&copy;)\s*(20\d{2})|(20\d{2})\s*(?:©|&copy;)", html) for y in pair if y]
    add("Fresh copyright year", bool(years) and max(years) >= year_now - 1, 4)
    add("Fast load (under 4s)", meta["elapsed"] < 4, 6, f"{meta['elapsed']}s")
    legacy = any(t in low for t in ("<frameset", "<font ", "<marquee", "<blink"))
    add("Modern markup", (not legacy) and "<!doctype html" in low[:300], 8)
    return checks


REX_SCAN_SYSTEM = (
    "You are Rex, SiteGenie's sales lead scanner. You are given raw HTML from a small-business website. "
    "Judge its design and sales quality harshly but fairly, like a modern web designer. Respond with ONLY "
    "a JSON object, no markdown fences:\n"
    '{"design_score": <integer 0-30, 30 = stunning modern high-converting site, 15 = dated but usable, '
    '0 = ancient or broken>, "business_name": "<best guess>", "category": "<business type guess>", '
    '"top_issues": ["<up to 4 concrete, specific issues a buyer would notice>"], '
    '"pitch": "<1-2 sentence sales angle for selling them a brand-new SiteGenie website, referencing their '
    'specific weaknesses>"}'
)


async def _llm_review(html: str, url: str) -> dict:
    trimmed = re.sub(r"<script[\s\S]*?</script>", "", html)[:15000]
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"rexscan_{uuid.uuid4().hex[:8]}",
                       system_message=REX_SCAN_SYSTEM).with_model("anthropic", STRATEGY_MODEL)
        raw = str(await asyncio.wait_for(
            chat.send_message(UserMessage(text=f"Website: {url}\n\nHTML:\n{trimmed}")), timeout=90))
        data = json.loads(re.search(r"\{[\s\S]*\}", raw).group(0))
        return {"design_score": max(0, min(30, int(data.get("design_score", 15)))),
                "business_name": str(data.get("business_name") or "")[:80],
                "category": str(data.get("category") or "")[:60],
                "issues": [str(i)[:140] for i in (data.get("top_issues") or [])][:4],
                "pitch": str(data.get("pitch") or "")[:400]}
    except Exception:
        logger.exception("rex scan llm review failed; using neutral design score")
        return {"design_score": 15, "business_name": "", "category": "", "issues": [], "pitch": ""}


async def scan_website(url: str) -> dict:
    url = _normalize_url(url)
    host = urlparse(url).hostname
    if await asyncio.to_thread(_blocked_host, host):
        raise ValueError("That URL can't be scanned.")
    domain = re.sub(r"^www\.", "", (host or "").lower())
    try:
        meta = await _fetch(url)
    except Exception:
        return {"url": url, "final_url": url, "domain": domain, "score": 5, "tier": "hot",
                "breakdown": [{"check": "Site reachable", "points": 0, "max": 100, "note": "unreachable"}],
                "issues": ["Website is unreachable or broken"], "business_name": domain, "category": "",
                "pitch": f"Their website at {domain} doesn't even load — easiest pitch in the world: SiteGenie can have a new site live this week.",
                "fetched": False}
    checks = _deterministic_checks(meta["html"], meta)
    review = await _llm_review(meta["html"], meta["final_url"])
    checks.append({"check": "Design & sales quality (AI review)",
                   "points": review["design_score"], "max": 30, "note": ""})
    score = max(0, min(100, sum(c["points"] for c in checks)))
    return {"url": url, "final_url": meta["final_url"], "domain": domain, "score": score,
            "tier": _tier(score), "breakdown": checks, "issues": review["issues"],
            "business_name": review["business_name"] or domain, "category": review["category"],
            "pitch": review["pitch"], "fetched": True}


async def upsert_weak_site_lead(scan: dict, extra: dict | None = None) -> dict:
    dedupe_key = f"site:{scan['domain']}"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "source": "weak_website", "business_name": scan["business_name"], "category": scan["category"],
        "website": scan["final_url"], "score": scan["score"], "tier": scan["tier"],
        "breakdown": scan["breakdown"], "issues": scan["issues"], "rex_pitch": scan["pitch"],
        "updated_at": now, **(extra or {}),
    }
    existing = await db.leads.find_one({"dedupe_key": dedupe_key}, {"_id": 0, "lead_id": 1})
    if existing:
        await db.leads.update_one({"dedupe_key": dedupe_key}, {"$set": doc})
        lead_id, created = existing["lead_id"], False
    else:
        lead_id, created = f"lead_{uuid.uuid4().hex[:12]}", True
        await db.leads.insert_one({**doc, "lead_id": lead_id, "dedupe_key": dedupe_key,
                                   "status": "new", "created_at": now})
    return {"lead_id": lead_id, "created": created}


PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_FIELDS = ("places.id,places.displayName,places.rating,places.userRatingCount,"
                 "places.websiteUri,places.nationalPhoneNumber,places.formattedAddress")


async def hunt_places(location: str, category: str) -> dict:
    """Rex's hunt: real businesses via Google Places. Criteria: >=15 reviews, rating >=3.5, no website."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(PLACES_URL, json={"textQuery": f"{category} in {location}", "pageSize": 20},
                              headers={"X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
                                       "X-Goog-FieldMask": PLACES_FIELDS})
    if r.status_code != 200:
        logger.error("places api error %s: %s", r.status_code, r.text[:300])
        # Bubble up the specific Google reason (IP restriction, API disabled, etc.)
        try:
            msg = r.json().get("error", {}).get("message", "").strip()
        except Exception:
            msg = ""
        if r.status_code == 403 and "IP address restriction" in msg:
            raise RuntimeError(
                "Google Places rejected the key: it has an IP restriction that blocks our server. "
                "Remove the IP restriction (or switch to an HTTP-referrer / no-restriction key) in Google Cloud Console → Credentials.")
        if r.status_code == 403:
            raise RuntimeError(
                f"Google Places denied the request (403). {msg or 'Confirm the key is unrestricted and Places API (New) is enabled.'}")
        raise RuntimeError(
            f"Google Places rejected the request ({r.status_code}). {msg or 'Check the API key and that Places API (New) is enabled.'}")
    places = r.json().get("places", [])
    now = datetime.now(timezone.utc).isoformat()
    added, skipped, candidates = 0, 0, []
    for p in places:
        reviews = int(p.get("userRatingCount") or 0)
        rating = float(p.get("rating") or 0)
        if reviews < 15 or rating < 3.5:
            continue
        name = (p.get("displayName") or {}).get("text", "Unknown")
        if p.get("websiteUri"):
            candidates.append({"business_name": name, "website": p["websiteUri"], "reviews_count": reviews,
                               "rating": rating, "phone": p.get("nationalPhoneNumber"),
                               "address": p.get("formattedAddress")})
            continue
        dedupe_key = f"place:{p['id']}"
        if await db.leads.find_one({"dedupe_key": dedupe_key}, {"_id": 1}):
            skipped += 1
            continue
        await db.leads.insert_one({
            "lead_id": f"lead_{uuid.uuid4().hex[:12]}", "dedupe_key": dedupe_key, "source": "no_website",
            "business_name": name, "category": category, "location": location,
            "phone": p.get("nationalPhoneNumber"), "address": p.get("formattedAddress"),
            "rating": rating, "reviews_count": reviews, "website": None, "score": None,
            "tier": "hot" if reviews >= 50 else "warm",
            "rex_pitch": f"{name} has {reviews} reviews ({rating}★) and NO website — customers are searching and finding nothing. SiteGenie can launch their site this week.",
            "status": "new", "created_at": now, "updated_at": now})
        added += 1
    return {"found": len(places), "new_leads": added, "skipped_existing": skipped,
            "website_candidates": candidates}


OUTREACH_SYSTEM = (
    "You are Rex, SiteGenie's top sales hunter, drafting first-touch outreach for a small local business "
    "that needs a website. The Owner will send it MANUALLY (never auto-blasted). Tone: friendly, local, "
    "specific, zero corporate speak — lead with value, reference something real about their business. "
    "The SMS is sent TO the business owner — never include their own phone number in it; end with a "
    "question CTA instead. "
    "Reply ONLY JSON, no markdown fences:\n"
    '{"sms": "<first-touch SMS, max 280 chars, mention a specific detail (reviews, rating, missing/weak '
    "website), one clear CTA; if a live demo link is provided, make it the hook>\", "
    '"call_script": "<a 2-3 sentence call opener, then the single best line to handle: '
    "'we don't need a website'>\"}"
)


async def set_lead_outreach(lead: dict) -> dict:
    from services.llm import _call_llm
    demo_url = f"{PUBLIC_BASE}/api/p/{lead['demo_slug']}" if lead.get("demo_slug") else None
    info = {k: lead.get(k) for k in ("business_name", "category", "location", "phone", "rating",
                                     "reviews_count", "issues", "rex_pitch", "website")}
    prompt = f"Business info: {json.dumps(info, default=str)}"
    if demo_url:
        prompt += f"\nTheir brand-new demo website is ALREADY LIVE at {demo_url} — strongest possible hook."
    raw = await _call_llm(prompt, OUTREACH_SYSTEM, STRATEGY_MODEL)
    data = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
    outreach = {"sms": str(data.get("sms", ""))[:400],
                "call_script": str(data.get("call_script", ""))[:900],
                "demo_url": demo_url,
                "generated_at": datetime.now(timezone.utc).isoformat()}
    await db.leads.update_one({"lead_id": lead["lead_id"]}, {"$set": {"outreach": outreach}})
    return outreach


async def leads_summary() -> dict:
    total = await db.leads.count_documents({})
    by_status = {str(s["_id"]): s["n"] async for s in
                 db.leads.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    by_tier = {str(s["_id"]): s["n"] async for s in
               db.leads.aggregate([{"$group": {"_id": "$tier", "n": {"$sum": 1}}}])}
    recent = await db.leads.find({}, {"_id": 0, "business_name": 1, "source": 1, "score": 1, "tier": 1,
                                      "reviews_count": 1, "rating": 1, "status": 1, "category": 1}
                                 ).sort("created_at", -1).to_list(10)
    return {"total": total, "by_status": by_status, "by_tier": by_tier, "recent_leads": recent}
