import uuid
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import Request

import stripe as stripe_sdk
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest,
)

from database import db
from config import (
    STRIPE_API_KEY, SUBSCRIPTION_PLANS, CREDIT_RESET_DAYS, use_native_stripe, logger,
)
from security import process_subscription
from services.market import fulfill_market_purchase


# ---------------- Emergent-proxied one-time checkout ----------------
def get_stripe(request: Request) -> StripeCheckout:
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


async def apply_payment(txn: dict):
    """Grant credits/plan once per session. Atomic idempotency guard prevents double-credit."""
    # Atomically claim the transaction; if already processed, another call handled it.
    claimed = await db.payment_transactions.find_one_and_update(
        {"session_id": txn["session_id"], "processed": {"$ne": True}},
        {"$set": {"processed": True}},
    )
    if not claimed:
        return
    user_id = claimed["user_id"]
    if claimed["kind"] == "credits":
        await db.users.update_one({"user_id": user_id}, {"$inc": {"extra_credits": int(claimed.get("credits", 0))}})
    elif claimed["kind"] == "market_purchase":
        await fulfill_market_purchase(claimed)


# ---------------- Native Stripe recurring subscriptions ----------------
def _sub_period_end(sub) -> datetime:
    ts = sub.get("current_period_end") if isinstance(sub, dict) else getattr(sub, "current_period_end", None)
    if ts:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return None


async def _get_or_create_customer(user: dict) -> str:
    use_native_stripe()
    cid = user.get("stripe_customer_id")
    if cid:
        try:
            c = stripe_sdk.Customer.retrieve(cid)
            if not getattr(c, "deleted", False):
                return cid
        except Exception:
            pass  # stale/invalid id (e.g. test->live switch) -> recreate below
    cust = stripe_sdk.Customer.create(
        email=user["email"], name=user.get("name", ""), metadata={"user_id": user["user_id"]})
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"stripe_customer_id": cust.id}})
    return cust.id


async def _activate_native_sub(user_id: str, plan_id: str, sub):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return
    now = datetime.now(timezone.utc)
    cpe = _sub_period_end(sub) or (now + timedelta(days=plan["billing_days"]))
    sub_id = sub["id"] if isinstance(sub, dict) else sub.id
    cancel_flag = bool(sub.get("cancel_at_period_end") if isinstance(sub, dict) else getattr(sub, "cancel_at_period_end", False))
    await db.users.update_one({"user_id": user_id}, {"$set": {
        "plan": plan_id, "plan_name": plan["name"], "subscription_status": "active",
        "cancel_at_period_end": cancel_flag, "plan_credits": plan["monthly_credits"],
        "current_period_end": cpe.isoformat(),
        "next_credit_reset": (now + timedelta(days=CREDIT_RESET_DAYS)).isoformat(),
        "provider": "stripe_native", "stripe_subscription_id": sub_id,
        "subscription_started_at": now.isoformat(),
    }})
    await db.subscriptions.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "plan": plan_id, "status": "active",
                  "stripe_subscription_id": sub_id, "started_at": now.isoformat()}},
        upsert=True,
    )


async def _renew_native_sub(user_id: str, plan_id: str, sub):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return
    now = datetime.now(timezone.utc)
    cpe = _sub_period_end(sub) or (now + timedelta(days=plan["billing_days"]))
    sub_id = sub["id"] if isinstance(sub, dict) else sub.id
    await db.users.update_one({"user_id": user_id}, {"$set": {
        "subscription_status": "active", "plan": plan_id, "plan_name": plan["name"],
        "plan_credits": plan["monthly_credits"], "current_period_end": cpe.isoformat(),
        "next_credit_reset": (now + timedelta(days=CREDIT_RESET_DAYS)).isoformat(),
        "provider": "stripe_native", "stripe_subscription_id": sub_id,
    }})
    await db.payment_transactions.insert_one({
        "session_id": f"inv_{sub_id}_{int(now.timestamp())}", "user_id": user_id,
        "amount": plan["amount"], "currency": "usd", "kind": "renewal", "plan_id": plan_id,
        "credits": plan["monthly_credits"], "payment_status": "paid", "status": "complete",
        "processed": True, "provider": "stripe_native", "created_at": now,
    })


async def subscription_worker():
    """Periodically process active subscriptions for credit resets and renewals."""
    while True:
        try:
            cursor = db.users.find({"subscription_status": "active"}, {"_id": 0}).limit(2000)
            async for u in cursor:
                await process_subscription(u)
        except Exception:
            logger.exception("subscription_worker error")
        await asyncio.sleep(3600)
