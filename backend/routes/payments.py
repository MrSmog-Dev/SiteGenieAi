from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends

from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest,
)

from database import db
from models import CheckoutInput
from config import CREDIT_PACKS, logger
from security import get_current_user, public_user, validate_origin
from services.billing import get_stripe, apply_payment

router = APIRouter()


@router.post("/checkout/session")
async def create_checkout(input: CheckoutInput, request: Request, user: dict = Depends(get_current_user)):
    # Subscriptions must go through the native Stripe flow (/subscription/checkout) so renewals
    # are driven by verified webhooks — never by this one-time checkout.
    if input.kind != "credits":
        raise HTTPException(status_code=400, detail="Invalid kind")
    pkg = CREDIT_PACKS.get(input.plan_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid plan")

    amount = float(pkg["amount"])
    pkg_credits = int(pkg["credits"])
    origin = validate_origin(input.origin_url)
    success_url = f"{origin}/payment-return?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"
    metadata = {
        "user_id": user["user_id"], "kind": input.kind, "plan_id": input.plan_id,
        "credits": str(pkg_credits),
    }
    stripe = get_stripe(request)
    req = CheckoutSessionRequest(amount=amount, currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session: CheckoutSessionResponse = await stripe.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["user_id"],
        "amount": amount, "currency": "usd", "kind": input.kind,
        "plan_id": input.plan_id, "credits": pkg_credits,
        "payment_status": "initiated", "status": "open", "processed": False,
        "metadata": metadata, "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/checkout/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one(
        {"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    stripe = get_stripe(request)
    status: CheckoutStatusResponse = await stripe.get_checkout_status(session_id)
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status, "status": status.status}},
    )
    if status.payment_status == "paid" and not txn.get("processed"):
        await apply_payment(txn)
    updated_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {
        "payment_status": status.payment_status, "status": status.status,
        "kind": txn["kind"], "credits": txn["credits"], "plan_id": txn["plan_id"],
        "user": public_user(updated_user),
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    stripe = get_stripe(request)
    try:
        event = await stripe.handle_webhook(body, sig)
    except Exception:
        logger.exception("stripe webhook error")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if event.payment_status == "paid" and event.session_id:
        txn = await db.payment_transactions.find_one({"session_id": event.session_id}, {"_id": 0})
        if txn and not txn.get("processed"):
            await apply_payment(txn)
    return {"received": True}
