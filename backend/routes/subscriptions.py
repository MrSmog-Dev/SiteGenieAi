from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends

import stripe as stripe_sdk

from database import db
from models import SubCheckoutInput
from config import (
    SUBSCRIPTION_PLANS, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_IDS,
    use_native_stripe, logger,
)
from security import get_current_user, public_user, user_is_unlimited, validate_origin
from services.billing import (
    _get_or_create_customer, _activate_native_sub, _renew_native_sub, _sub_period_end,
)

router = APIRouter()


@router.get("/subscription")
async def get_subscription(user: dict = Depends(get_current_user)):
    plan = SUBSCRIPTION_PLANS.get(user.get("plan"))
    txns = await db.payment_transactions.find(
        {"user_id": user["user_id"], "payment_status": "paid"}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    for t in txns:
        if isinstance(t.get("created_at"), datetime):
            t["created_at"] = t["created_at"].isoformat()
    return {
        "status": user.get("subscription_status", "none"),
        "plan": user.get("plan"),
        "plan_name": user.get("plan_name"),
        "amount": plan["amount"] if plan else None,
        "billing_days": plan["billing_days"] if plan else None,
        "monthly_credits": plan["monthly_credits"] if plan else None,
        "unlimited": user_is_unlimited(user),
        "plan_credits": int(user.get("plan_credits", 0)),
        "extra_credits": int(user.get("extra_credits", 0)),
        "current_period_end": user.get("current_period_end"),
        "next_credit_reset": user.get("next_credit_reset"),
        "cancel_at_period_end": bool(user.get("cancel_at_period_end", False)),
        "invoices": txns,
    }


@router.post("/subscription/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    if user.get("subscription_status") != "active":
        raise HTTPException(status_code=400, detail="No active subscription")
    if user.get("provider") == "stripe_native" and user.get("stripe_subscription_id"):
        try:
            use_native_stripe()
            stripe_sdk.Subscription.modify(user["stripe_subscription_id"], cancel_at_period_end=True)
        except Exception:
            logger.exception("stripe cancel failed")
            raise HTTPException(status_code=502, detail="Could not cancel with Stripe. Try again.")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": True}})
    await db.subscriptions.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": True}})
    return {"success": True, "cancel_at_period_end": True}


@router.post("/subscription/reactivate")
async def reactivate_subscription(user: dict = Depends(get_current_user)):
    if user.get("subscription_status") != "active" or not user.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Nothing to reactivate")
    if user.get("provider") == "stripe_native" and user.get("stripe_subscription_id"):
        try:
            use_native_stripe()
            stripe_sdk.Subscription.modify(user["stripe_subscription_id"], cancel_at_period_end=False)
        except Exception:
            logger.exception("stripe reactivate failed")
            raise HTTPException(status_code=502, detail="Could not reactivate with Stripe. Try again.")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": False}})
    await db.subscriptions.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": False}})
    return {"success": True, "cancel_at_period_end": False}


@router.post("/subscription/checkout")
async def subscription_checkout(input: SubCheckoutInput, user: dict = Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Subscriptions are not configured yet.")
    price = STRIPE_PRICE_IDS.get(input.plan_id)
    plan = SUBSCRIPTION_PLANS.get(input.plan_id)
    if not price or not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    use_native_stripe()
    origin = validate_origin(input.origin_url)
    try:
        customer_id = await _get_or_create_customer(user)
        session = stripe_sdk.checkout.Session.create(
            mode="subscription", customer=customer_id,
            line_items=[{"price": price, "quantity": 1}],
            success_url=f"{origin}/payment-return?type=subscription&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/pricing",
            metadata={"user_id": user["user_id"], "plan_id": input.plan_id},
            subscription_data={"metadata": {"user_id": user["user_id"], "plan_id": input.plan_id}},
        )
    except stripe_sdk.error.AuthenticationError:
        logger.exception("subscription checkout failed: stripe key invalid/expired")
        raise HTTPException(status_code=503,
                            detail="Payments are temporarily unavailable — our Stripe connection needs to be "
                                   "refreshed. Please try again soon.")
    except Exception:
        logger.exception("subscription checkout failed")
        raise HTTPException(status_code=502, detail="Could not start checkout. Please try again.")
    await db.payment_transactions.insert_one({
        "session_id": session.id, "user_id": user["user_id"], "amount": plan["amount"],
        "currency": "usd", "kind": "subscription", "plan_id": input.plan_id,
        "credits": plan["monthly_credits"], "payment_status": "initiated", "status": "open",
        "processed": False, "provider": "stripe_native", "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.id}


@router.get("/subscription/checkout-status/{session_id}")
async def subscription_checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one(
        {"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    use_native_stripe()
    try:
        session = stripe_sdk.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve payment status.")
    payment_status = session.get("payment_status")
    status = session.get("status")
    await db.payment_transactions.update_one(
        {"session_id": session_id}, {"$set": {"payment_status": payment_status, "status": status}})
    if status == "complete" and session.get("subscription"):
        claimed = await db.payment_transactions.find_one_and_update(
            {"session_id": session_id, "processed": {"$ne": True}}, {"$set": {"processed": True}})
        if claimed:
            sub = stripe_sdk.Subscription.retrieve(session["subscription"])
            await _activate_native_sub(user["user_id"], txn["plan_id"], sub)
    updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return {"payment_status": payment_status, "status": status, "kind": "subscription",
            "plan_id": txn["plan_id"], "user": public_user(updated)}


@router.post("/webhook/stripe-native")
async def stripe_native_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("stripe-signature")
    use_native_stripe()
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("native webhook received but STRIPE_WEBHOOK_SECRET is not configured; rejecting")
        raise HTTPException(status_code=400, detail="Webhook not configured")
    try:
        event = stripe_sdk.Webhook.construct_event(body, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        logger.exception("native webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    etype = event["type"]
    obj = event["data"]["object"]
    try:
        if etype == "checkout.session.completed":
            meta = obj.get("metadata") or {}
            uid, plan_id, sub_id = meta.get("user_id"), meta.get("plan_id"), obj.get("subscription")
            if uid and plan_id and sub_id:
                await db.payment_transactions.find_one_and_update(
                    {"session_id": obj["id"], "processed": {"$ne": True}},
                    {"$set": {"processed": True, "payment_status": "paid", "status": "complete"}})
                sub = stripe_sdk.Subscription.retrieve(sub_id)
                await _activate_native_sub(uid, plan_id, sub)
        elif etype == "invoice.paid":
            if obj.get("billing_reason") != "subscription_create":  # first invoice handled at checkout
                sub_id = obj.get("subscription")
                if sub_id:
                    sub = stripe_sdk.Subscription.retrieve(sub_id)
                    meta = (sub.get("metadata") if isinstance(sub, dict) else sub.metadata) or {}
                    if meta.get("user_id") and meta.get("plan_id"):
                        await _renew_native_sub(meta["user_id"], meta["plan_id"], sub)
        elif etype == "customer.subscription.deleted":
            meta = obj.get("metadata") or {}
            if meta.get("user_id"):
                await db.users.update_one({"user_id": meta["user_id"]}, {"$set": {
                    "subscription_status": "cancelled", "plan": None, "plan_name": None,
                    "plan_credits": 0, "cancel_at_period_end": False}})
        elif etype == "customer.subscription.updated":
            meta = obj.get("metadata") or {}
            if meta.get("user_id"):
                upd = {"cancel_at_period_end": bool(obj.get("cancel_at_period_end", False))}
                cpe = _sub_period_end(obj)
                if cpe:
                    upd["current_period_end"] = cpe.isoformat()
                await db.users.update_one({"user_id": meta["user_id"]}, {"$set": upd})
    except Exception:
        logger.exception("native webhook handling error")
    return {"received": True}
