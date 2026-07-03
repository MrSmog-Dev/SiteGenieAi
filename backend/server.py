from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from database import db, client
from config import (
    logger, CREDIT_RESET_DAYS, GEN_WINDOW_SECONDS, LOGIN_WINDOW_SECONDS, OWNER_EMAIL,
)
from security import hash_password, verify_password
from services.billing import subscription_worker
from routes.auth import router as auth_router
from routes.plans import router as plans_router
from routes.templates import router as templates_router
from routes.payments import router as payments_router
from routes.subscriptions import router as subscriptions_router
from routes.market import router as market_router
from routes.agents import router as agents_router

app = FastAPI()
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "SiteGenie API"}


api_router.include_router(auth_router)
api_router.include_router(plans_router)
api_router.include_router(templates_router)
api_router.include_router(payments_router)
api_router.include_router(subscriptions_router)
api_router.include_router(market_router)
api_router.include_router(agents_router)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token")
    await db.templates.create_index("user_id")
    await db.templates.create_index("slug", unique=True, sparse=True)
    await db.templates.create_index("custom_domain", unique=True, sparse=True)
    await db.gen_jobs.create_index("job_id")
    await db.market_listings.create_index("market_id", unique=True)
    await db.market_listings.create_index("active")
    await db.rate_events.create_index("ts", expireAfterSeconds=GEN_WINDOW_SECONDS + 60)
    await db.login_attempts.create_index("ts", expireAfterSeconds=LOGIN_WINDOW_SECONDS + 60)
    await db.login_attempts.create_index("identifier")
    # seed admin (requires ADMIN_EMAIL + ADMIN_PASSWORD from env; no weak defaults)
    admin_email = (os.environ.get("ADMIN_EMAIL") or "").lower().strip()
    admin_password = os.environ.get("ADMIN_PASSWORD") or ""
    now = datetime.now(timezone.utc)
    if admin_email and len(admin_password) >= 12:
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({
                "user_id": f"user_{uuid.uuid4().hex[:12]}", "email": admin_email,
                "name": "Admin", "password_hash": hash_password(admin_password), "picture": "",
                "role": "admin", "plan_credits": 300, "extra_credits": 100,
                "plan": "annual", "plan_name": "Annual", "subscription_status": "active",
                "cancel_at_period_end": False,
                "current_period_end": (now + timedelta(days=365)).isoformat(),
                "next_credit_reset": (now + timedelta(days=CREDIT_RESET_DAYS)).isoformat(),
                "created_at": now,
            })
        elif not verify_password(admin_password, existing.get("password_hash", "")):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
    else:
        logger.warning("Admin seeding skipped: ADMIN_EMAIL and a >=12 char ADMIN_PASSWORD are required.")
    # seed owner (unlimited, all features; sign-in via Google or password)
    owner_email = OWNER_EMAIL
    owner_password = os.environ.get("OWNER_PASSWORD") or ""
    if owner_email:
        owner = await db.users.find_one({"email": owner_email})
        if not owner:
            await db.users.insert_one({
                "user_id": f"user_{uuid.uuid4().hex[:12]}", "email": owner_email,
                "name": "Owner", "picture": "",
                "password_hash": hash_password(owner_password) if len(owner_password) >= 8 else "",
                "role": "owner", "plan_credits": 0, "extra_credits": 0,
                "plan": None, "plan_name": None, "subscription_status": "none",
                "cancel_at_period_end": False, "current_period_end": None,
                "next_credit_reset": None, "created_at": now,
            })
        else:
            upd = {"role": "owner"}
            if len(owner_password) >= 8 and not verify_password(owner_password, owner.get("password_hash", "")):
                upd["password_hash"] = hash_password(owner_password)
            await db.users.update_one({"email": owner_email}, {"$set": upd})
    # backfill legacy credit model
    async for u in db.users.find({"extra_credits": {"$exists": False}}, {"_id": 0, "user_id": 1, "credits": 1}):
        await db.users.update_one({"user_id": u["user_id"]},
                                  {"$set": {"extra_credits": int(u.get("credits", 0)), "plan_credits": 0}})
    asyncio.create_task(subscription_worker())


app.include_router(api_router)
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.(emergentagent\.com|emergent\.host)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
