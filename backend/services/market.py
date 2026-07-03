import uuid
from datetime import datetime, timezone

from database import db
from services.pricing_agent import price_template

GEN_FIELDS = ("business_name", "industry", "description", "style", "primary_color",
              "contact_email", "phone", "target_audience", "key_services",
              "brand_keywords", "pages", "quality")


async def create_listing(tpl: dict, owner_user_id: str) -> dict:
    """Runs the AI pricing agent on a template and creates a Market listing (HTML snapshot)."""
    pricing = await price_template(tpl)
    listing = {
        "market_id": f"mkt_{uuid.uuid4().hex[:12]}",
        "source_template_id": tpl["template_id"],
        "owner_user_id": owner_user_id,
        "title": tpl.get("business_name", "Website Template"),
        "category": tpl.get("industry", ""),
        **{k: tpl.get(k) for k in GEN_FIELDS},
        "html": tpl.get("html", ""),
        "price_usd": pricing["price_usd"],
        "tier": pricing["tier"],
        "summary": pricing["summary"],
        "highlights": pricing["highlights"],
        "rationale": pricing["rationale"],
        "metrics": pricing["metrics"],
        "priced_by": pricing["priced_by"],
        "views": 0, "purchases": 0, "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await db.market_listings.insert_one(dict(listing))
    return listing


async def fulfill_market_purchase(txn: dict):
    """Copies the listing's template to the buyer with free-edit ownership."""
    listing = await db.market_listings.find_one({"market_id": txn.get("market_id")}, {"_id": 0})
    if not listing:
        return
    new_id = f"tpl_{uuid.uuid4().hex[:12]}"
    doc = {k: listing.get(k) for k in GEN_FIELDS}
    doc.update({
        "template_id": new_id,
        "user_id": txn["user_id"],
        "html": listing.get("html", ""),
        "purchased": True,
        "purchased_market_id": listing["market_id"],
        "purchased_price": listing.get("price_usd"),
        "created_at": datetime.now(timezone.utc),
    })
    await db.templates.insert_one(doc)
    await db.market_listings.update_one({"market_id": listing["market_id"]}, {"$inc": {"purchases": 1}})
    await db.payment_transactions.update_one(
        {"session_id": txn["session_id"]}, {"$set": {"fulfilled_template_id": new_id}})
