import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Depends

from database import db
from models import RegisterInput, LoginInput, GoogleSessionInput, ResetBusinessInput
from security import (
    hash_password, verify_password, create_session, set_session_cookie, public_user,
    process_subscription, get_current_user, client_ip, is_owner,
    login_is_locked, record_failed_login, clear_login_attempts,
)

router = APIRouter()

# Bump this when the Terms/Privacy/Refund policies materially change so consent is re-captured.
LEGAL_TERMS_VERSION = "2026-07-07"


@router.post("/auth/register")
async def register(input: RegisterInput, request: Request, response: Response):
    if not input.consent:
        raise HTTPException(status_code=400,
                            detail="Please agree to the Terms of Service, Privacy and Refund Policy to continue.")
    email = input.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    consent_record = {
        "agreed": True,
        "terms_version": LEGAL_TERMS_VERSION,
        "documents": ["terms", "refund", "privacy"],
        "method": "clickwrap_checkbox",
        "ip": client_ip(request),
        "user_agent": request.headers.get("user-agent", "")[:300],
        "agreed_at": now.isoformat(),
    }
    doc = {
        "user_id": user_id, "email": email, "name": input.name,
        "password_hash": hash_password(input.password), "picture": "",
        "role": "user", "plan_credits": 0, "extra_credits": 15,
        "plan": None, "plan_name": None, "subscription_status": "none",
        "current_period_end": None, "next_credit_reset": None, "cancel_at_period_end": False,
        "legal_consent": consent_record,
        "created_at": now,
    }
    try:
        await db.users.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Immutable audit trail of the consent event (kept even if the user is later deleted from users).
    await db.consent_events.insert_one({
        "consent_id": f"consent_{uuid.uuid4().hex[:12]}", "user_id": user_id,
        "email": email, **consent_record})
    token = await create_session(user_id)
    set_session_cookie(response, token)
    return public_user(doc)


@router.post("/auth/login")
async def login(input: LoginInput, request: Request, response: Response):
    email = input.email.lower()
    identifier = f"{client_ip(request)}:{email}"
    if await login_is_locked(identifier):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(input.password, user["password_hash"]):
        await record_failed_login(identifier)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await clear_login_attempts(identifier)
    token = await create_session(user["user_id"])
    set_session_cookie(response, token)
    user = await process_subscription(user)
    return public_user(user)


@router.post("/auth/google-session")
async def google_session(input: GoogleSessionInput, request: Request, response: Response):
    async with httpx.AsyncClient() as hc:
        r = await hc.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": input.session_id},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google session")
    data = r.json()
    email = data["email"].lower()
    user = await db.users.find_one({"email": email})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        consent_record = {
            "agreed": True, "terms_version": LEGAL_TERMS_VERSION,
            "documents": ["terms", "refund", "privacy"], "method": "clickwrap_google_signup",
            "ip": client_ip(request), "user_agent": request.headers.get("user-agent", "")[:300],
            "agreed_at": now.isoformat(),
        }
        user = {
            "user_id": user_id, "email": email, "name": data.get("name", ""),
            "picture": data.get("picture", ""), "role": "user",
            "plan_credits": 0, "extra_credits": 15,
            "plan": None, "plan_name": None, "subscription_status": "none",
            "current_period_end": None, "next_credit_reset": None, "cancel_at_period_end": False,
            "legal_consent": consent_record,
            "created_at": now,
        }
        await db.users.insert_one(user)
        await db.consent_events.insert_one({
            "consent_id": f"consent_{uuid.uuid4().hex[:12]}", "user_id": user_id,
            "email": email, **consent_record})
    else:
        await db.users.update_one({"email": email}, {"$set": {"picture": data.get("picture", user.get("picture", ""))}})
    token = await create_session(user["user_id"])
    set_session_cookie(response, token)
    user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    user = await process_subscription(user)
    return public_user(user)


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"success": True}


@router.post("/auth/admin/reset-business-data")
async def reset_business_data(input: ResetBusinessInput, user: dict = Depends(get_current_user)):
    """Owner-only: wipe test users/revenue/jobs/AI-chat history for a true fresh start.
    Keeps: owner account, owner templates, Market listings, blog posts, automation state.
    IMPORTANT: `agent_memory` (the 12 agents' persistent brain) is intentionally PRESERVED so
    the team remembers your preferences and open work across resets — never add it here."""
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Owner only")
    if input.confirm != "RESET":
        raise HTTPException(status_code=400, detail='Type "RESET" to confirm')
    owner_id = user["user_id"]
    other_ids = [u["user_id"] async for u in db.users.find(
        {"user_id": {"$ne": owner_id}}, {"_id": 0, "user_id": 1})]
    await db.users.delete_many({"user_id": {"$ne": owner_id}})
    await db.user_sessions.delete_many({"user_id": {"$ne": owner_id}})
    await db.templates.delete_many({"user_id": {"$in": other_ids}})
    for col in (db.payment_transactions, db.subscriptions, db.gen_jobs, db.agent_jobs,
                db.team_tasks, db.team_memos, db.war_room, db.war_room_meetings,
                db.agent_chats, db.rate_events, db.login_attempts):
        await col.delete_many({})
    leads_cleared = False
    if input.include_leads:
        await db.leads.delete_many({})
        leads_cleared = True
    return {"reset": True, "removed_users": len(other_ids), "leads_cleared": leads_cleared}
