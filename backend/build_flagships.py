"""Builds SiteGenie's 3 flagship Market templates targeting the $500 Premium grade.
Run once: python build_flagships.py"""
import asyncio
import re
import uuid
from datetime import datetime, timezone

from database import db, client
from config import OWNER_EMAIL, STRATEGY_MODEL, BUILD_MODEL
from services.llm import (_build_brief_prompt, _build_site_prompt, _call_llm, clean_html,
                          GEN_STRATEGY_SYSTEM, GEN_BUILD_SYSTEM)
from services.market import create_listing
from services.pricing_agent import price_template

FLAGSHIPS = [
    {"business_name": "Sterling & Vale", "industry": "Luxury Real Estate Brokerage",
     "description": "An elite real-estate brokerage representing architectural estates and waterfront properties for high-net-worth clients, with white-glove concierge service from first tour to closing.",
     "style": "luxurious", "primary_color": "#0F4C5C",
     "target_audience": "High-net-worth buyers and sellers of $2M+ properties",
     "key_services": "Estate sales, Private off-market listings, Buyer representation, Relocation concierge",
     "brand_keywords": "prestigious, discreet, polished, exclusive",
     "contact_email": "clients@sterlingvale.com", "phone": "(310) 555-0190",
     "pages": "hero, featured listings gallery, sold portfolio with stats, agent team, buying process timeline, testimonials, market insights, neighborhoods, private consultation booking, FAQ, contact"},
    {"business_name": "Auréa Med Spa", "industry": "High-End Med Spa & Aesthetics Clinic",
     "description": "A physician-led aesthetics clinic offering advanced injectables, laser treatments and medical-grade skincare in a serene, five-star spa environment.",
     "style": "elegant", "primary_color": "#9A6A4F",
     "target_audience": "Affluent clients 30-60 seeking premium non-surgical aesthetics",
     "key_services": "Injectables & fillers, Laser skin resurfacing, Medical-grade facials, Membership programs",
     "brand_keywords": "serene, clinical, indulgent, transformative",
     "contact_email": "bookings@aureamedspa.com", "phone": "(212) 555-0164",
     "pages": "hero, signature treatments with pricing tiers, before-after gallery, medical team credentials, membership packages, treatment process steps, testimonials slider, safety standards, booking form, FAQ, contact"},
    {"business_name": "Hartwell & Cross LLP", "industry": "Premium Corporate Law Firm",
     "description": "A powerhouse corporate law firm advising founders, funds and Fortune-500 boards on M&A, litigation and complex commercial strategy across three offices.",
     "style": "professional", "primary_color": "#1E293B",
     "target_audience": "Founders, general counsels and investment funds",
     "key_services": "Mergers & acquisitions, Commercial litigation, Venture & funds, Corporate governance",
     "brand_keywords": "authoritative, precise, established, formidable",
     "contact_email": "inquiries@hartwellcross.com", "phone": "(646) 555-0141",
     "pages": "hero, practice areas grid, case results with animated stats, partner profiles, industries served, client testimonials, insights preview, awards bar, consultation request form, FAQ, offices/contact"},
]

ENHANCE_SYSTEM = (
    "You are a principal front-end engineer adding flagship-grade upgrades to an existing single-file "
    "website. You receive its complete HTML. You respond with ONLY three blocks in this EXACT format and "
    "nothing else:\n"
    "===STYLE===\n<style>/* all new CSS, matching the site's existing design tokens */</style>\n"
    "===SECTIONS===\n<!-- all NEW full <section> elements, matching the site's class conventions -->\n"
    "===SCRIPT===\n<script>/* all vanilla JS, defensive with null checks so it never throws */</script>"
)

ENHANCE_PROMPT = (
    "You are upgrading an existing premium single-file website toward flagship $500 quality. Below is "
    "its design context (palette, fonts, class conventions, existing sections). Everything you produce "
    "must match that design system exactly and be self-contained (no external assets). JS must be "
    "defensive (null checks, no errors if an element is missing)."
)


async def _sonnet(prompt: str, system: str, timeout: int = 420) -> str:
    try:
        return await _call_llm(prompt, system, BUILD_MODEL, timeout=timeout)
    except Exception as e:
        print(f"  (sonnet error: {type(e).__name__}, retrying once...)")
        await asyncio.sleep(5)
        return await _call_llm(prompt, system, BUILD_MODEL, timeout=timeout)


def _extract(block: str, raw: str, next_marker: str = None) -> str:
    if f"==={block}===" not in raw:
        return ""
    part = raw.split(f"==={block}===", 1)[1]
    if next_marker and f"==={next_marker}===" in part:
        part = part.split(f"==={next_marker}===", 1)[0]
    return part.strip()


def _inject(html: str, raw: str) -> str:
    style = _extract("STYLE", raw, "SECTIONS")
    sections = _extract("SECTIONS", raw, "SCRIPT")
    script = _extract("SCRIPT", raw)
    if not (style or sections or script):
        return html
    if style and "</head>" in html:
        html = html.replace("</head>", f"\n{style}\n</head>", 1)
    if sections:
        anchor = "<footer" if "<footer" in html else "</body>"
        html = html.replace(anchor, f"\n{sections}\n{anchor}", 1)
    if script and "</body>" in html:
        html = html.replace("</body>", f"\n{script}\n</body>", 1)
    return html


UPGRADE_TASKS = [
    ("behaviors",
     "Produce: a floating back-to-top button (JS-created), scroll-reveal animations for ALL existing "
     "<section> elements via IntersectionObserver (CSS classes + JS), animated number counters for any "
     "elements with digits in stats, sticky nav with scroll-spy active states and a mobile hamburger "
     "toggle (enhance the EXISTING nav via JS), and smooth-scroll for anchor links. At least 2 new "
     "@keyframes. SECTIONS block may be empty for this task."),
    ("gallery+slider",
     "Produce TWO new sections: (1) an interactive image gallery ('Our Work' / portfolio style, 6-8 "
     "items using CSS-styled placeholder tiles with gradients/icons, NO external images) with a working "
     "lightbox (open/close, prev/next arrows, ESC), and (2) an auto-advancing testimonial slider with "
     "dots and pause-on-hover, using 4 new realistic testimonials. Include 2 new @keyframes."),
    ("pricing+faq+form",
     "Produce THREE new sections: (1) a 3-tier pricing/packages section with a highlighted featured tier "
     "and per-tier feature lists, (2) an FAQ accordion (5 questions) with smooth height animation, and "
     "(3) a multi-step (2-step) booking/consultation form with client-side validation, a progress "
     "indicator and an animated success state. Include hover micro-interactions and 1 new @keyframes."),
]


def _design_context(html: str) -> str:
    style = ""
    m = re.search(r"<style[\s\S]*?</style>", html, re.I)
    if m:
        style = m.group(0)[:14000]
    sections = re.findall(r"<section[^>]*>", html)
    title = re.search(r"<title[^>]*>([^<]*)", html, re.I)
    return (f"SITE TITLE: {title.group(1) if title else ''}\n"
            f"EXISTING SECTION TAGS: {sections}\n"
            f"EXISTING CSS (design tokens, fonts, palette, class conventions):\n{style}")


async def _upgrade(html: str, extra_note: str = "") -> str:
    ctx = _design_context(html)
    for task_name, task in UPGRADE_TASKS:
        prompt = (f"{ENHANCE_PROMPT}\nTASK ({task_name}): {task}\n{extra_note}\n\n{ctx}")
        try:
            raw = await _sonnet(prompt, ENHANCE_SYSTEM, timeout=300)
            html = _inject(html, raw)
            print(f"    + {task_name} injected ({len(html)//1024}KB)")
        except asyncio.TimeoutError:
            print(f"    ! {task_name} timed out twice, skipped")
    return html


async def build_flagship(owner_id: str, spec: dict):
    name = spec["business_name"]
    if await db.market_listings.find_one({"title": name, "active": True}):
        print(f"skip (already listed): {name}")
        return
    spec.pop("pages", "")
    print(f"[{name}] pass 1: brief...")
    brief = await _call_llm(_build_brief_prompt(spec), GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
    print(f"[{name}] pass 2: core build (sonnet)...")
    html = clean_html(await _sonnet(_build_site_prompt(spec, brief), GEN_BUILD_SYSTEM))
    print(f"[{name}] core size: {len(html)//1024}KB — pass 3: flagship upgrades (3 calls)...")
    html = await _upgrade(html)
    tpl = {**spec, "quality": "quality", "template_id": f"tpl_{uuid.uuid4().hex[:12]}",
           "user_id": owner_id, "html": html, "flagship": True,
           "created_at": datetime.now(timezone.utc)}
    pricing = await price_template(tpl)
    print(f"[{name}] graded ${pricing['price_usd']} after upgrades ({len(html)//1024}KB)")
    await db.templates.insert_one(dict(tpl))
    listing = await create_listing(tpl, owner_id)
    print(f"LISTED FLAGSHIP: {name} -> ${listing['price_usd']} ({listing['tier']}) | "
          f"{len(tpl['html'])//1024}KB | metrics: {listing['metrics']}")


async def main():
    owner = await db.users.find_one({"email": OWNER_EMAIL})
    if not owner:
        raise SystemExit("Owner not found")
    for spec in FLAGSHIPS:
        try:
            await build_flagship(owner["user_id"], dict(spec))
        except Exception as e:
            print(f"FAILED: {spec['business_name']}: {e!r}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
