from fastapi import APIRouter, Depends, HTTPException

from config import SUBSCRIPTION_PLANS, CREDIT_PACKS
from database import db
from security import get_current_user, is_owner

router = APIRouter()


MILESTONES = (
    ("first_signup", "First real signup", "A customer creates an account"),
    ("first_published", "First customer site published", "A customer takes their site live"),
    ("first_dollar", "First $1 of revenue", "First real payment lands"),
    ("first_subscriber", "First subscriber", "Someone commits to a plan"),
    ("first_market_sale", "First Template Market sale", "A flagship finds a buyer"),
)


@router.get("/milestones")
async def get_milestones(user: dict = Depends(get_current_user)):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Owner only")
    owner_id = user["user_id"]
    results = {}

    u = await db.users.find_one({"user_id": {"$ne": owner_id}, "role": {"$ne": "owner"}},
                                {"_id": 0, "name": 1, "email": 1, "created_at": 1}, sort=[("created_at", 1)])
    results["first_signup"] = u and {"date": str(u.get("created_at", ""))[:10],
                                     "detail": u.get("name") or u.get("email", "")}

    t = await db.templates.find_one({"published": True, "user_id": {"$ne": owner_id}},
                                    {"_id": 0, "business_name": 1, "updated_at": 1}, sort=[("updated_at", 1)])
    results["first_published"] = t and {"date": str(t.get("updated_at", ""))[:10],
                                        "detail": t.get("business_name", "")}

    p = await db.payment_transactions.find_one(
        {"payment_status": "paid", "amount": {"$gt": 0}, "user_id": {"$ne": owner_id}},
        {"_id": 0, "amount": 1, "created_at": 1, "kind": 1}, sort=[("created_at", 1)])
    results["first_dollar"] = p and {"date": str(p.get("created_at", ""))[:10],
                                     "detail": f"${p.get('amount')} ({p.get('kind', 'payment')})"}

    s = await db.users.find_one({"user_id": {"$ne": owner_id}, "subscription_status": "active"},
                                {"_id": 0, "plan_name": 1, "subscription_started_at": 1}, sort=[("subscription_started_at", 1)])
    results["first_subscriber"] = s and {"date": str(s.get("subscription_started_at", ""))[:10],
                                         "detail": s.get("plan_name") or "Active plan"}

    m = await db.payment_transactions.find_one(
        {"kind": "market_purchase", "payment_status": "paid", "user_id": {"$ne": owner_id}},
        {"_id": 0, "amount": 1, "created_at": 1}, sort=[("created_at", 1)])
    results["first_market_sale"] = m and {"date": str(m.get("created_at", ""))[:10],
                                          "detail": f"${m.get('amount')}"}

    return {"milestones": [
        {"id": mid, "title": title, "hint": hint, "achieved": bool(results.get(mid)),
         **(results.get(mid) or {})} for mid, title, hint in MILESTONES]}


@router.get("/plans")
async def get_plans():
    return {"subscriptions": SUBSCRIPTION_PLANS, "credit_packs": CREDIT_PACKS}
