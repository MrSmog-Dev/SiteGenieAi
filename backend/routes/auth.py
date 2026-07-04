import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Depends

from database import db
from models import RegisterInput, LoginInput, GoogleSessionInput
from security import (
    hash_password, verify_password, create_session, set_session_cookie, public_user,
    process_subscription, get_current_user, client_ip,
    login_is_locked, record_failed_login, clear_login_attempts,
)

router = APIRouter()


@router.post("/auth/register")
async def register(input: RegisterInput, response: Response):
    email = input.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id, "email": email, "name": input.name,
        "password_hash": hash_password(input.password), "picture": "",
        "role": "user", "plan_credits": 0, "extra_credits": 15,
        "plan": None, "plan_name": None, "subscription_status": "none",
        "current_period_end": None, "next_credit_reset": None, "cancel_at_period_end": False,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db.users.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Email already registered")
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
async def google_session(input: GoogleSessionInput, response: Response):
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
        user = {
            "user_id": user_id, "email": email, "name": data.get("name", ""),
            "picture": data.get("picture", ""), "role": "user",
            "plan_credits": 0, "extra_credits": 15,
            "plan": None, "plan_name": None, "subscription_status": "none",
            "current_period_end": None, "next_credit_reset": None, "cancel_at_period_end": False,
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(user)
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
