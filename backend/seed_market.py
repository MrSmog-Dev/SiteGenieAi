"""Seeds the Template Market with AI-generated, AI-priced templates. Run once: python seed_market.py"""
import asyncio
import uuid
from datetime import datetime, timezone

from database import db, client
from config import OWNER_EMAIL, STRATEGY_MODEL, BUILD_MODEL
from services.llm import (
    _build_brief_prompt, _build_site_prompt, _call_llm, clean_html,
    GEN_STRATEGY_SYSTEM, GEN_BUILD_SYSTEM,
)
from services.market import create_listing

SEEDS = [
    {"business_name": "Ember & Oak", "industry": "Restaurant & Fine Dining",
     "description": "An upscale wood-fired bistro serving seasonal tasting menus, house-cured charcuterie and curated natural wines in a candle-lit dining room.",
     "style": "elegant", "primary_color": "#C2410C",
     "target_audience": "Couples and food lovers looking for a memorable night out",
     "key_services": "Wood-fired dinners, Seasonal tasting menus, Private events, Wine pairings",
     "brand_keywords": "warm, artisanal, refined, intimate",
     "contact_email": "reservations@emberandoak.com", "phone": "(415) 555-0142"},
    {"business_name": "IronPulse Fitness", "industry": "Gym & Fitness Studio",
     "description": "A high-energy strength and conditioning gym with certified coaches, small-group HIIT classes and personalized nutrition programming.",
     "style": "bold", "primary_color": "#DC2626",
     "target_audience": "Busy professionals aged 25-45 who want structured, results-driven training",
     "key_services": "Personal training, HIIT classes, Strength programs, Nutrition coaching",
     "brand_keywords": "powerful, energetic, disciplined, community",
     "contact_email": "team@ironpulsefit.com", "phone": "(312) 555-0177"},
    {"business_name": "Northwind Creative", "industry": "Marketing & Branding Agency",
     "description": "A boutique creative agency that builds brands, websites and campaigns for ambitious startups — strategy-first work with measurable results.",
     "style": "modern", "primary_color": "#4F46E5",
     "target_audience": "Startup founders and marketing leads at growth-stage companies",
     "key_services": "Brand strategy, Web design, Content marketing, Paid advertising",
     "brand_keywords": "sharp, strategic, bold, contemporary",
     "contact_email": "hello@northwindcreative.co", "phone": "(206) 555-0135"},
    {"business_name": "Lumen Studio", "industry": "Photography Portfolio",
     "description": "An award-winning photography studio specializing in editorial portraits, weddings and brand shoots with a cinematic, light-driven style.",
     "style": "minimal", "primary_color": "#0EA5E9",
     "target_audience": "Engaged couples, magazines and lifestyle brands",
     "key_services": "Editorial portraits, Weddings, Brand photography, Fine-art prints",
     "brand_keywords": "cinematic, timeless, luminous, editorial",
     "contact_email": "book@lumenstudio.photo", "phone": "(646) 555-0189"},
    {"business_name": "Flowdesk", "industry": "SaaS Productivity Software",
     "description": "An all-in-one workspace that unifies tasks, team inbox and analytics so remote teams ship faster — with automation that kills busywork.",
     "style": "sleek", "primary_color": "#2563EB",
     "target_audience": "Remote-first product teams of 5-50 people",
     "key_services": "Task automation, Shared team inbox, Analytics dashboard, 50+ integrations",
     "brand_keywords": "efficient, clean, smart, trustworthy",
     "contact_email": "sales@flowdesk.io", "phone": "(628) 555-0121"},
    {"business_name": "Velvet & Sage", "industry": "Beauty Salon & Spa",
     "description": "A luxury salon and day spa offering precision hair styling, glow facials, massage therapy and full bridal beauty packages.",
     "style": "luxurious", "primary_color": "#DB2777",
     "target_audience": "Women 25-55 seeking premium self-care and bridal services",
     "key_services": "Hair styling & color, Signature facials, Massage therapy, Bridal packages",
     "brand_keywords": "indulgent, serene, polished, feminine",
     "contact_email": "bookings@velvetandsage.com", "phone": "(305) 555-0163"},
    {"business_name": "Harborline Realty", "industry": "Real Estate Agency",
     "description": "A coastal real-estate team helping families buy and sell waterfront homes, with data-backed valuations and white-glove relocation support.",
     "style": "professional", "primary_color": "#0E7490",
     "target_audience": "Home buyers and sellers in coastal communities",
     "key_services": "Home buying, Home selling, Property valuation, Relocation support",
     "brand_keywords": "trusted, coastal, established, personal",
     "contact_email": "info@harborlinerealty.com", "phone": "(508) 555-0154"},
    {"business_name": "Driftwood Coffee Co.", "industry": "Coffee Shop & Bakery",
     "description": "A neighborhood roastery café pouring single-origin espresso beside fresh sourdough pastries, weekend brunch and monthly coffee subscriptions.",
     "style": "cozy", "primary_color": "#92400E",
     "target_audience": "Locals, students and remote workers who care about specialty coffee",
     "key_services": "Specialty espresso, Fresh pastries, Weekend brunch, Coffee subscriptions",
     "brand_keywords": "warm, handcrafted, welcoming, rustic",
     "contact_email": "hi@driftwoodcoffee.co", "phone": "(503) 555-0118"},
]


async def build_one(owner_id: str, spec: dict, sem: asyncio.Semaphore):
    async with sem:
        if await db.market_listings.find_one({"title": spec["business_name"], "active": True}):
            print(f"skip (already listed): {spec['business_name']}")
            return
        print(f"generating: {spec['business_name']} ...")
        brief = await _call_llm(_build_brief_prompt(spec), GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
        html = clean_html(await _call_llm(_build_site_prompt(spec, brief), GEN_BUILD_SYSTEM, BUILD_MODEL))
        tpl = {**spec, "quality": "quality", "template_id": f"tpl_{uuid.uuid4().hex[:12]}",
               "user_id": owner_id, "html": html, "created_at": datetime.now(timezone.utc)}
        await db.templates.insert_one(dict(tpl))
        listing = await create_listing(tpl, owner_id)
        print(f"LISTED: {spec['business_name']} -> ${listing['price_usd']} ({listing['tier']}, {listing['priced_by']})")


async def main():
    owner = await db.users.find_one({"email": OWNER_EMAIL})
    if not owner:
        raise SystemExit("Owner user not found — check OWNER_EMAIL in backend/.env")
    sem = asyncio.Semaphore(3)
    results = await asyncio.gather(*(build_one(owner["user_id"], dict(s), sem) for s in SEEDS),
                                   return_exceptions=True)
    for s, r in zip(SEEDS, results):
        if isinstance(r, Exception):
            print(f"FAILED: {s['business_name']}: {r!r}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
