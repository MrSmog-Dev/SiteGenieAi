import os
import re
import secrets
import bcrypt
from datetime import datetime, timezone, timedelta

from fastapi import Request, Response, HTTPException

from database import db
from config import (
    SUBSCRIPTION_PLANS, CREDIT_RESET_DAYS, TOKENS_PER_CREDIT, MIN_OPERATION_COST,
    OWNER_EMAIL, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS, logger,
)


# ---------------- Password / helpers ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def parse_dt(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def total_credits(u: dict) -> int:
    return int(u.get("plan_credits", 0)) + int(u.get("extra_credits", 0))


# ---------------- Rate limiting ----------------
def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(key: str, max_count: int, window_seconds: int):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    count = await db.rate_events.count_documents({"key": key, "ts": {"$gte": window_start}})
    if count >= max_count:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down and try again shortly.")
    await db.rate_events.insert_one({"key": key, "ts": now})


_ALLOWED_ORIGINS = {o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()}
_PLATFORM_ORIGIN_RE = re.compile(r"^https://([a-z0-9-]+\.)*(sitegenie-ai\.com|sitegenie\.dev|emergentagent\.com|emergent\.host)$")


def validate_origin(origin_url: str) -> str:
    origin = (origin_url or "").strip().rstrip("/")
    if origin in _ALLOWED_ORIGINS or _PLATFORM_ORIGIN_RE.match(origin):
        return origin
    raise HTTPException(status_code=400, detail="Invalid origin")


async def login_is_locked(identifier: str) -> bool:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    count = await db.login_attempts.count_documents({"identifier": identifier, "ts": {"$gte": window_start}})
    return count >= LOGIN_MAX_ATTEMPTS


async def record_failed_login(identifier: str):
    await db.login_attempts.insert_one({"identifier": identifier, "ts": datetime.now(timezone.utc)})


async def clear_login_attempts(identifier: str):
    await db.login_attempts.delete_many({"identifier": identifier})


# ---------------- Credits / roles ----------------
def estimate_cost(*texts) -> int:
    total_chars = sum(len(t or "") for t in texts)
    tokens = total_chars / 4.0
    return max(MIN_OPERATION_COST, round(tokens / TOKENS_PER_CREDIT))


def is_owner(user: dict) -> bool:
    if not user:
        return False
    if user.get("role") in ("owner", "admin"):
        return True
    return bool(OWNER_EMAIL and (user.get("email", "").lower() == OWNER_EMAIL))


def user_is_unlimited(user: dict) -> bool:
    if is_owner(user):
        return True
    plan = SUBSCRIPTION_PLANS.get(user.get("plan"))
    return bool(plan and plan.get("unlimited") and user.get("subscription_status") == "active")


async def deduct_credits(user_id: str, amount: int):
    """Drain plan_credits first, then extra_credits; never below zero."""
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    pc = int(u.get("plan_credits", 0))
    ec = int(u.get("extra_credits", 0))
    from_plan = min(pc, amount)
    from_extra = min(ec, amount - from_plan)
    if from_plan or from_extra:
        await db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"plan_credits": -from_plan, "extra_credits": -from_extra}})


async def billing_user(user: dict) -> dict:
    """Resolve the account that owns the credit pool for this user. Team MEMBERS draw from (and
    are billed against) their team owner's account; everyone else bills to themselves."""
    tid = user.get("team_id")
    if tid and user.get("team_role") == "member":
        owner = await db.users.find_one({"user_id": user.get("team_owner_id")}, {"_id": 0})
        if owner:
            return owner
    return user


async def process_subscription(user: dict) -> dict:
    """Lazy subscription lifecycle: migrate legacy credits, apply 30-day credit resets,
    handle billing-period renewal (simulated) and cancellation."""
    changed = {}
    if OWNER_EMAIL and user.get("email", "").lower() == OWNER_EMAIL and user.get("role") != "owner":
        user["role"] = "owner"
        changed["role"] = "owner"
    if "plan_credits" not in user or "extra_credits" not in user:
        legacy = int(user.get("credits", 0))
        user["extra_credits"] = int(user.get("extra_credits", legacy))
        user["plan_credits"] = int(user.get("plan_credits", 0))
        changed["extra_credits"] = user["extra_credits"]
        changed["plan_credits"] = user["plan_credits"]

    if user.get("subscription_status") == "active":
        now = datetime.now(timezone.utc)
        plan = SUBSCRIPTION_PLANS.get(user.get("plan"))
        is_native = user.get("provider") == "stripe_native"
        cpe = parse_dt(user.get("current_period_end"))
        # Non-native subscriptions have no real recurring charge — they LAPSE at period end
        # (native subs are renewed exclusively by verified Stripe webhooks).
        if not is_native and cpe and now >= cpe:
            user["subscription_status"] = "cancelled"
            user["plan"] = None
            user["plan_name"] = None
            user["plan_credits"] = 0
            changed.update(subscription_status="cancelled", plan=None, plan_name=None, plan_credits=0)
            if user.get("team_role") == "owner" and user.get("team_id"):
                try:
                    from services.teams import disband_team
                    await disband_team(user["user_id"])
                    user["team_id"] = None; user["team_owner_id"] = None; user["team_role"] = None
                except Exception:
                    logger.exception("team disband on lapse failed")
        # 30-day credit resets (applies to both native and simulated)
        if user.get("subscription_status") == "active" and plan:
            ncr = parse_dt(user.get("next_credit_reset"))
            while ncr and now >= ncr:
                user["plan_credits"] = plan["monthly_credits"]
                ncr = ncr + timedelta(days=CREDIT_RESET_DAYS)
                user["next_credit_reset"] = ncr.isoformat()
                changed["plan_credits"] = user["plan_credits"]
                changed["next_credit_reset"] = user["next_credit_reset"]

    if changed:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": changed})
    return user


def public_user(u: dict) -> dict:
    plan = SUBSCRIPTION_PLANS.get(u.get("plan"))
    return {
        "user_id": u["user_id"],
        "email": u["email"],
        "name": u.get("name", ""),
        "picture": u.get("picture", ""),
        "role": u.get("role", "user"),
        "credits": total_credits(u),
        "plan_credits": int(u.get("plan_credits", 0)),
        "extra_credits": int(u.get("extra_credits", 0)),
        "plan": u.get("plan"),
        "plan_name": u.get("plan_name"),
        "monthly_credits": plan["monthly_credits"] if plan else None,
        "unlimited": user_is_unlimited(u),
        "subscription_status": u.get("subscription_status", "none"),
        "current_period_end": u.get("current_period_end"),
        "next_credit_reset": u.get("next_credit_reset"),
        "cancel_at_period_end": bool(u.get("cancel_at_period_end", False)),
    }


async def public_user_view(u: dict) -> dict:
    """public_user, but a team MEMBER sees the shared team pool (owner's credits/plan)."""
    pub = public_user(u)
    if u.get("team_id") and u.get("team_role") == "member" and u.get("team_owner_id"):
        owner = await db.users.find_one({"user_id": u["team_owner_id"]}, {"_id": 0})
        if owner:
            pub["credits"] = total_credits(owner)
            pub["plan_credits"] = int(owner.get("plan_credits", 0))
            pub["extra_credits"] = int(owner.get("extra_credits", 0))
            pub["unlimited"] = user_is_unlimited(owner)
            pub["shared_pool"] = True
    pub["team_id"] = u.get("team_id")
    pub["team_role"] = u.get("team_role")
    return pub


# ---------------- Sessions ----------------
async def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc),
    })
    return token


def set_session_cookie(response: Response, token: str):
    response.set_cookie(key="session_token", value=token, httponly=True,
                        secure=True, samesite="lax", max_age=7 * 24 * 3600, path="/")


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    exp = session["expires_at"]
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user = await process_subscription(user)
    return user
