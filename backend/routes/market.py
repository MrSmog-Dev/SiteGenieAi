from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse

from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest, CheckoutStatusResponse

from database import db
from models import MarketListInput, MarketCheckoutInput
from security import get_current_user, is_owner
from services.billing import get_stripe, apply_payment
from services.market import create_listing
from routes.templates import _count_view

router = APIRouter()

_LIST_PROJECTION = {"_id": 0, "html": 0, "metrics": 0}


def _serialize(doc: dict) -> dict:
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@router.get("/market")
async def market_listings():
    docs = await db.market_listings.find({"active": True}, _LIST_PROJECTION).sort("created_at", -1).to_list(200)
    def score(d):
        return int(d.get("purchases", 0)) * 10 + int(d.get("views", 0))
    top = max(docs, key=score, default=None)
    for d in docs:
        d["popular"] = bool(top) and d["market_id"] == top["market_id"] and score(top) > 0
    return [_serialize(d) for d in docs]


@router.get("/market/mine")
async def market_mine(user: dict = Depends(get_current_user)):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Only the store owner can manage Market listings.")
    docs = await db.market_listings.find({"active": True}, _LIST_PROJECTION).sort("created_at", -1).to_list(200)
    return [_serialize(d) for d in docs]


@router.get("/market/owned")
async def market_owned(user: dict = Depends(get_current_user)):
    docs = await db.templates.find(
        {"user_id": user["user_id"], "purchased": True},
        {"_id": 0, "template_id": 1, "purchased_market_id": 1}).to_list(500)
    return {d["purchased_market_id"]: d["template_id"] for d in docs if d.get("purchased_market_id")}


@router.post("/market/list")
async def list_on_market(input: MarketListInput, user: dict = Depends(get_current_user)):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Only the store owner can list templates on the Market.")
    tpl = await db.templates.find_one({"template_id": input.template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    existing = await db.market_listings.find_one(
        {"source_template_id": input.template_id, "active": True}, {"_id": 1})
    if existing:
        raise HTTPException(status_code=409, detail="This template is already listed on the Market.")
    listing = await create_listing(tpl, user["user_id"])
    listing.pop("html", None)
    listing.pop("metrics", None)
    return _serialize(listing)


@router.get("/market/purchase/status/{session_id}")
async def market_purchase_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one(
        {"session_id": session_id, "user_id": user["user_id"], "kind": "market_purchase"}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    stripe = get_stripe(request)
    status: CheckoutStatusResponse = await stripe.get_checkout_status(session_id)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status, "status": status.status}})
    if status.payment_status == "paid" and not txn.get("processed"):
        await apply_payment(txn)
    fresh = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    return {
        "payment_status": status.payment_status, "status": status.status,
        "market_id": txn["market_id"], "amount": txn["amount"],
        "template_id": fresh.get("fulfilled_template_id"),
    }


@router.post("/market/{market_id}/checkout")
async def market_checkout(market_id: str, input: MarketCheckoutInput, request: Request,
                          user: dict = Depends(get_current_user)):
    listing = await db.market_listings.find_one({"market_id": market_id, "active": True}, _LIST_PROJECTION)
    if not listing:
        raise HTTPException(status_code=404, detail="This template is no longer available.")
    already = await db.templates.find_one(
        {"user_id": user["user_id"], "purchased_market_id": market_id}, {"_id": 1})
    if already:
        raise HTTPException(status_code=409, detail="You already own this template.")
    amount = float(listing["price_usd"])
    origin = input.origin_url.rstrip("/")
    metadata = {"user_id": user["user_id"], "kind": "market_purchase", "market_id": market_id}
    stripe = get_stripe(request)
    req = CheckoutSessionRequest(
        amount=amount, currency="usd",
        success_url=f"{origin}/market/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/market", metadata=metadata)
    session = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["user_id"],
        "amount": amount, "currency": "usd", "kind": "market_purchase",
        "market_id": market_id, "plan_id": None, "credits": 0,
        "payment_status": "initiated", "status": "open", "processed": False,
        "metadata": metadata, "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/market/{market_id}/preview")
async def market_preview(market_id: str, request: Request, count: int = 0):
    listing = await db.market_listings.find_one({"market_id": market_id, "active": True}, {"_id": 0, "html": 1})
    if not listing:
        return HTMLResponse("<h1>Template not found</h1>", status_code=404)
    if count and _count_view(request):
        await db.market_listings.update_one({"market_id": market_id}, {"$inc": {"views": 1}})
    return HTMLResponse(listing.get("html", ""),
                        headers={"Content-Security-Policy": "connect-src 'none'"})


@router.delete("/market/{market_id}")
async def delist_market(market_id: str, user: dict = Depends(get_current_user)):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Only the store owner can remove Market listings.")
    res = await db.market_listings.update_one({"market_id": market_id}, {"$set": {"active": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"active": False}
