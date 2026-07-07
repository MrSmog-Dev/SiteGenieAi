"""Failed / abandoned payment recovery — Rex detects, Mara drafts the win-back.

A checkout that was created but never reached `paid` within a grace window is treated as an
abandoned/failed payment. Rex surfaces it in the owner's Team Pulse and Mara drafts a
personalized recovery email into her chat. Each recoverable payment is handled once.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from config import OWNER_EMAIL, STRATEGY_MODEL, SUBSCRIPTION_PLANS, CREDIT_PACKS, logger
from database import db
from services.agents import AGENT_MAP, post_agent_message
from services.activity import log_activity
from services.llm import _call_llm

# Grace period before a still-unpaid checkout counts as abandoned, and how long to keep trying.
ABANDON_AFTER_MIN = 30
ABANDON_LOOKBACK_HOURS = 72


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kind_label(txn: dict) -> str:
    kind = txn.get("kind")
    if kind == "subscription":
        plan = SUBSCRIPTION_PLANS.get(txn.get("plan_id") or "")
        return f"the {plan['name']} plan" if plan else "a subscription"
    if kind == "credits":
        pack = CREDIT_PACKS.get(txn.get("plan_id") or "")
        return f"the {pack['name']} ({pack['credits']} credits)" if pack else "a credit pack"
    if kind == "market_purchase":
        return "a Template Market website"
    return "a purchase"


async def run_payment_recovery(owner_id: str):
    """Find newly-abandoned checkouts, alert Rex (Team Pulse) and queue Mara win-back drafts."""
    now = datetime.now(timezone.utc)
    older_than = now - timedelta(minutes=ABANDON_AFTER_MIN)
    lookback = now - timedelta(hours=ABANDON_LOOKBACK_HOURS)
    candidates = await db.payment_transactions.find(
        {"processed": {"$ne": True},
         "payment_status": {"$nin": ["paid"]},
         "recovery_flagged": {"$ne": True},
         "kind": {"$in": ["subscription", "credits", "market_purchase"]},
         "created_at": {"$lte": older_than, "$gte": lookback}},
        {"_id": 0}).sort("created_at", -1).to_list(25)
    for txn in candidates:
        try:
            await _recover_one(owner_id, txn)
        except Exception:
            logger.exception("payment recovery failed for %s", txn.get("session_id"))


async def _recover_one(owner_id: str, txn: dict):
    # Claim it so we only surface each abandoned payment once.
    claimed = await db.payment_transactions.find_one_and_update(
        {"session_id": txn["session_id"], "recovery_flagged": {"$ne": True}},
        {"$set": {"recovery_flagged": True, "recovery_flagged_at": _now()}})
    if not claimed:
        return
    buyer = await db.users.find_one({"user_id": txn.get("user_id")},
                                    {"_id": 0, "name": 1, "email": 1}) or {}
    label = _kind_label(txn)
    amount = txn.get("amount")
    who = buyer.get("name") or buyer.get("email") or "A visitor"

    # Rex surfaces it in Team Pulse.
    await post_agent_message(owner_id, "rex",
        f"💸 Payment didn't complete — {who} started checking out for {label}"
        f"{f' (${amount})' if amount else ''} but didn't finish. That's warm money left on the table. "
        "I've asked Mara to draft a win-back — hit send and we recover it.")
    await log_activity(owner_id, "rex", "recovery",
        f"Abandoned checkout: {who} — {label}{f' (${amount})' if amount else ''}.",
        detail="Warm lead — recovery email drafted by Mara.", link="/team?agent=mara")

    # Mara drafts a personalized recovery email into her chat.
    try:
        await _mara_recovery_draft(owner_id, who, buyer.get("email"), label, amount, txn.get("kind"))
    except Exception:
        logger.exception("mara recovery draft failed")


MARA_RECOVERY_SYSTEM = (
    "You are Mara, SiteGenie's empathetic lifecycle email marketer. Write a short, warm, high-converting "
    "cart-recovery email to a person who started checking out on SiteGenie but didn't finish. Be helpful, "
    "not pushy: acknowledge it happens, restate the value, remove friction (offer help), and give one clear "
    "CTA to complete their purchase. Provide 2 subject line options and a tight body (<140 words). No "
    "markdown tables. Sign as the SiteGenie team."
)


async def _mara_recovery_draft(owner_id: str, who: str, email: str, label: str, amount, kind: str):
    prompt = (f"Draft a recovery email now.\nCustomer: {who}\n"
              f"They were purchasing: {label}{f' for ${amount}' if amount else ''} (type: {kind}).\n"
              "SiteGenie facts: AI builds a full premium website in minutes; 15 free credits on signup; "
              "Template Market sites are one-of-one with free unlimited AI edits. Reassure and make it easy "
              "to finish.")
    reply = await _call_llm(prompt, MARA_RECOVERY_SYSTEM, STRATEGY_MODEL)
    to_line = f" (send to {email})" if email else ""
    await post_agent_message(owner_id, "mara",
        f"✉️ Recovery draft — Rex flagged an abandoned checkout for {label}{to_line}. "
        f"Ready to send:\n\n{str(reply).strip()}")
    await log_activity(owner_id, "mara", "recovery",
        f"Drafted a win-back email for {who} ({label}).",
        detail="Cart-recovery draft ready to send.", link="/team?agent=mara")
