"""One depth pass on listed flagships + reprice. Run: python deepen_flagships.py"""
import asyncio
from datetime import datetime, timezone

from database import db, client
from services.pricing_agent import price_template
from build_flagships import _sonnet, _inject, _design_context, ENHANCE_SYSTEM, ENHANCE_PROMPT

DEPTH_TASK = (
    "Produce THREE new sections: (1) a 'How We Work' process timeline with 4-5 steps and an animated "
    "connector line, (2) a leadership/team profiles section with 4 members using elegant CSS-styled "
    "avatar tiles (initials, no external images) and role/bio, and (3) a case studies / proven results "
    "section with 3 rich cards plus an animated stats bar. Include 2 new @keyframes, staggered reveal "
    "animations and refined hover micro-interactions. Everything responsive."
)


async def deepen(title: str):
    listing = await db.market_listings.find_one({"title": title, "active": True})
    if not listing:
        print(f"no listing: {title}")
        return
    html = listing["html"]
    print(f"[{title}] depth pass on {len(html)//1024}KB...")
    prompt = f"{ENHANCE_PROMPT}\nTASK (depth): {DEPTH_TASK}\n\n{_design_context(html)}"
    html = _inject(html, await _sonnet(prompt, ENHANCE_SYSTEM, timeout=300))
    tpl = {k: listing.get(k) for k in ("business_name", "industry", "description", "quality")}
    tpl["html"] = html
    pricing = await price_template(tpl)
    print(f"[{title}] regraded ${pricing['price_usd']} ({pricing['tier']}) at {len(html)//1024}KB")
    now = datetime.now(timezone.utc).isoformat()
    await db.market_listings.update_one({"market_id": listing["market_id"]}, {"$set": {
        "html": html, "price_usd": pricing["price_usd"], "tier": pricing["tier"],
        "summary": pricing["summary"], "highlights": pricing["highlights"],
        "rationale": pricing["rationale"], "metrics": pricing["metrics"], "updated_at": now}})
    await db.templates.update_one({"template_id": listing["source_template_id"]},
                                  {"$set": {"html": html}})


async def main():
    for t in ("Sterling & Vale", "Auréa Med Spa", "Hartwell & Cross LLP"):
        try:
            await deepen(t)
        except Exception as e:
            print(f"FAILED {t}: {e!r}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
