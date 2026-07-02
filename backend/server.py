from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import re
import logging
import secrets
import bcrypt
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest,
)

# ---------------- DB ----------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
STRIPE_API_KEY = os.environ['STRIPE_API_KEY']

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sitegenie")

# ---------------- Business config ----------------
SUBSCRIPTION_PLANS = {
    "monthly":   {"name": "Monthly",  "amount": 20.00,  "monthly_credits": 20, "billing_days": 30,  "interval": "month"},
    "quarterly": {"name": "3-Month",  "amount": 49.00,  "monthly_credits": 25, "billing_days": 90,  "interval": "quarter"},
    "annual":    {"name": "Annual",   "amount": 149.00, "monthly_credits": 30, "billing_days": 365, "interval": "year"},
}
CREDIT_RESET_DAYS = 30
CREDIT_PACKS = {
    "pack_10": {"name": "Starter Pack", "amount": 9.00,  "credits": 10},
    "pack_25": {"name": "Growth Pack",  "amount": 19.00, "credits": 25},
    "pack_60": {"name": "Pro Pack",     "amount": 39.00, "credits": 60},
}
CREDIT_COST_PER_TEMPLATE = 1

# ---------------- Models ----------------
class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class GoogleSessionInput(BaseModel):
    session_id: str

class GenerateInput(BaseModel):
    business_name: str
    industry: str
    description: str
    style: Optional[str] = "modern"
    primary_color: Optional[str] = "#0055FF"
    contact_email: Optional[str] = ""
    phone: Optional[str] = ""

class CheckoutInput(BaseModel):
    kind: str          # "subscription" | "credits"
    plan_id: str       # key in SUBSCRIPTION_PLANS or CREDIT_PACKS
    origin_url: str

class EditInput(BaseModel):
    instructions: str

# ---------------- Auth helpers ----------------
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
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
GEN_MAX_PER_WINDOW = 15
GEN_WINDOW_SECONDS = 5 * 60

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

async def login_is_locked(identifier: str) -> bool:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=LOGIN_WINDOW_SECONDS)
    count = await db.login_attempts.count_documents({"identifier": identifier, "ts": {"$gte": window_start}})
    return count >= LOGIN_MAX_ATTEMPTS

async def record_failed_login(identifier: str):
    await db.login_attempts.insert_one({"identifier": identifier, "ts": datetime.now(timezone.utc)})

async def clear_login_attempts(identifier: str):
    await db.login_attempts.delete_many({"identifier": identifier})

async def deduct_one_credit(user_id: str):
    r = await db.users.update_one(
        {"user_id": user_id, "plan_credits": {"$gt": 0}}, {"$inc": {"plan_credits": -1}})
    if r.modified_count == 0:
        await db.users.update_one(
            {"user_id": user_id, "extra_credits": {"$gt": 0}}, {"$inc": {"extra_credits": -1}})

async def process_subscription(user: dict) -> dict:
    """Lazy subscription lifecycle: migrate legacy credits, apply 30-day credit resets,
    handle billing-period renewal (simulated) and cancellation."""
    changed = {}
    if "plan_credits" not in user or "extra_credits" not in user:
        legacy = int(user.get("credits", 0))
        user["extra_credits"] = int(user.get("extra_credits", legacy))
        user["plan_credits"] = int(user.get("plan_credits", 0))
        changed["extra_credits"] = user["extra_credits"]
        changed["plan_credits"] = user["plan_credits"]

    if user.get("subscription_status") == "active":
        now = datetime.now(timezone.utc)
        plan = SUBSCRIPTION_PLANS.get(user.get("plan"))
        cpe = parse_dt(user.get("current_period_end"))
        # billing period end -> renew or cancel
        while plan and cpe and now >= cpe:
            if user.get("cancel_at_period_end"):
                user["subscription_status"] = "cancelled"
                user["plan"] = None
                user["plan_name"] = None
                user["plan_credits"] = 0
                changed.update(subscription_status="cancelled", plan=None, plan_name=None, plan_credits=0)
                cpe = None
                break
            cpe = cpe + timedelta(days=plan["billing_days"])
            user["current_period_end"] = cpe.isoformat()
            changed["current_period_end"] = user["current_period_end"]
            await db.payment_transactions.insert_one({
                "session_id": f"renewal_{uuid.uuid4().hex[:12]}", "user_id": user["user_id"],
                "amount": plan["amount"], "currency": "usd", "kind": "renewal",
                "plan_id": user.get("plan"), "credits": plan["monthly_credits"],
                "payment_status": "paid", "status": "complete", "processed": True,
                "created_at": datetime.now(timezone.utc),
            })
        # 30-day credit resets
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
        "subscription_status": u.get("subscription_status", "none"),
        "current_period_end": u.get("current_period_end"),
        "next_credit_reset": u.get("next_credit_reset"),
        "cancel_at_period_end": bool(u.get("cancel_at_period_end", False)),
    }

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

# ---------------- Auth endpoints ----------------
@api_router.post("/auth/register")
async def register(input: RegisterInput, response: Response):
    email = input.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id, "email": email, "name": input.name,
        "password_hash": hash_password(input.password), "picture": "",
        "role": "user", "plan_credits": 0, "extra_credits": 3,
        "plan": None, "plan_name": None, "subscription_status": "none",
        "current_period_end": None, "next_credit_reset": None, "cancel_at_period_end": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(doc)
    token = await create_session(user_id)
    set_session_cookie(response, token)
    return public_user(doc)

@api_router.post("/auth/login")
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

@api_router.post("/auth/google-session")
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
            "plan_credits": 0, "extra_credits": 3,
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

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"success": True}

# ---------------- Plans ----------------
@api_router.get("/plans")
async def get_plans():
    return {"subscriptions": SUBSCRIPTION_PLANS, "credit_packs": CREDIT_PACKS}

# ---------------- Template generation ----------------
GEN_SYSTEM = (
    "You are an elite web designer. You output a SINGLE complete, production-ready, "
    "responsive HTML5 document for a small business landing page. Rules: "
    "1) Return ONLY raw HTML starting with <!DOCTYPE html>. No markdown, no code fences, no commentary. "
    "2) Put all CSS inside a single <style> tag in the <head>. Do not use external CSS frameworks or JS. "
    "3) Make it visually stunning, modern, fully responsive with a hero, services/features, about, "
    "testimonials, and a contact section with a styled form and footer. "
    "4) Use the provided brand color as the primary accent. Use tasteful gradients, spacing and Google Fonts via <link>. "
    "5) Use real, relevant placeholder copy tailored to the business (no lorem ipsum)."
)

def clean_html(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text.strip())
    idx = text.lower().find("<!doctype")
    if idx > 0:
        text = text[idx:]
    return text.strip()

import asyncio

def _build_prompt(fields: dict) -> str:
    return (
        f"Business name: {fields.get('business_name','')}\n"
        f"Industry / type: {fields.get('industry','')}\n"
        f"Description: {fields.get('description','')}\n"
        f"Design style: {fields.get('style','modern')}\n"
        f"Primary brand color: {fields.get('primary_color','#0055FF')}\n"
        f"Contact email: {fields.get('contact_email','')}\n"
        f"Phone: {fields.get('phone','')}\n"
        "Generate the complete website now."
    )

async def _call_llm(prompt: str) -> str:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"gen_{uuid.uuid4().hex}",
        system_message=GEN_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-6")
    result = await chat.send_message(UserMessage(text=prompt))
    return clean_html(result if isinstance(result, str) else str(result))

async def _fail_job(job_id: str, e: Exception):
    logger.exception("generation failed")
    msg = str(e).lower()
    if "budget" in msg or "quota" in msg or "insufficient" in msg:
        err = "AI service is temporarily unavailable. Please try again shortly."
    else:
        err = "Generation failed. Please try again."
    await db.gen_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": err}})

async def _run_generation(job_id: str, user_id: str, fields: dict, mode: str = "new", template_id: str = None):
    try:
        if mode == "edit":
            existing = await db.templates.find_one({"template_id": template_id, "user_id": user_id}, {"_id": 0})
            prompt = (
                "Here is an existing complete HTML website document. Apply the requested changes and "
                "return the FULL updated HTML document only (starting with <!DOCTYPE html>, no commentary).\n\n"
                f"REQUESTED CHANGES:\n{fields.get('instructions','')}\n\n"
                f"CURRENT HTML:\n{existing.get('html','')}"
            )
        else:
            prompt = _build_prompt(fields)
        html = await _call_llm(prompt)
    except Exception as e:
        await _fail_job(job_id, e)
        return

    if mode == "new":
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        await db.templates.insert_one({
            "template_id": template_id, "user_id": user_id,
            "business_name": fields.get("business_name"), "industry": fields.get("industry"),
            "description": fields.get("description"), "style": fields.get("style"),
            "primary_color": fields.get("primary_color"), "html": html,
            "created_at": datetime.now(timezone.utc),
        })
    else:
        await db.templates.update_one(
            {"template_id": template_id, "user_id": user_id},
            {"$set": {"html": html, "updated_at": datetime.now(timezone.utc)}},
        )
    await deduct_one_credit(user_id)
    await db.gen_jobs.update_one({"job_id": job_id},
                                 {"$set": {"status": "done", "template_id": template_id}})

async def _start_job(user: dict, fields: dict, mode: str = "new", template_id: str = None):
    if total_credits(user) < CREDIT_COST_PER_TEMPLATE:
        raise HTTPException(status_code=402, detail="Not enough credits. Please purchase more.")
    await check_rate_limit(f"gen:{user['user_id']}", GEN_MAX_PER_WINDOW, GEN_WINDOW_SECONDS)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    await db.gen_jobs.insert_one({
        "job_id": job_id, "user_id": user["user_id"], "status": "pending",
        "template_id": template_id, "error": None, "created_at": datetime.now(timezone.utc),
    })
    asyncio.create_task(_run_generation(job_id, user["user_id"], fields, mode, template_id))
    return {"job_id": job_id, "status": "pending"}

@api_router.post("/templates/generate")
async def generate_template(input: GenerateInput, user: dict = Depends(get_current_user)):
    return await _start_job(user, input.model_dump(), mode="new")

@api_router.post("/templates/{template_id}/regenerate")
async def regenerate_template(template_id: str, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    fields = {k: tpl.get(k) for k in ("business_name", "industry", "description", "style", "primary_color")}
    return await _start_job(user, fields, mode="regenerate", template_id=template_id)

@api_router.post("/templates/{template_id}/edit")
async def edit_template(template_id: str, input: EditInput, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return await _start_job(user, {"instructions": input.instructions}, mode="edit", template_id=template_id)

@api_router.get("/templates/job/{job_id}")
async def generation_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.gen_jobs.find_one({"job_id": job_id, "user_id": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    resp = {"status": job["status"], "error": job.get("error")}
    if job["status"] == "done" and job.get("template_id"):
        tpl = await db.templates.find_one({"template_id": job["template_id"]}, {"_id": 0})
        updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if tpl:
            resp["template"] = {
                "template_id": tpl["template_id"], "business_name": tpl["business_name"],
                "industry": tpl["industry"], "primary_color": tpl["primary_color"],
                "html": tpl["html"],
            }
            resp["credits_remaining"] = total_credits(updated)
    return resp

@api_router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    docs = await db.templates.find({"user_id": user["user_id"]}, {"_id": 0, "html": 0}).sort("created_at", -1).to_list(200)
    for d in docs:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
    return docs

@api_router.get("/templates/{template_id}")
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    doc = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

@api_router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    await db.templates.delete_one({"template_id": template_id, "user_id": user["user_id"]})
    return {"success": True}

# ---------------- Payments ----------------
def get_stripe(request: Request) -> StripeCheckout:
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

@api_router.post("/checkout/session")
async def create_checkout(input: CheckoutInput, request: Request, user: dict = Depends(get_current_user)):
    if input.kind == "subscription":
        pkg = SUBSCRIPTION_PLANS.get(input.plan_id)
    elif input.kind == "credits":
        pkg = CREDIT_PACKS.get(input.plan_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid kind")
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid plan")

    amount = float(pkg["amount"])
    pkg_credits = int(pkg["monthly_credits"]) if input.kind == "subscription" else int(pkg["credits"])
    origin = input.origin_url.rstrip("/")
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
    elif claimed["kind"] == "subscription":
        plan = SUBSCRIPTION_PLANS.get(claimed["plan_id"])
        if plan:
            now = datetime.now(timezone.utc)
            await db.users.update_one({"user_id": user_id}, {"$set": {
                "plan": claimed["plan_id"], "plan_name": plan["name"],
                "subscription_status": "active", "cancel_at_period_end": False,
                "plan_credits": plan["monthly_credits"],
                "current_period_end": (now + timedelta(days=plan["billing_days"])).isoformat(),
                "next_credit_reset": (now + timedelta(days=CREDIT_RESET_DAYS)).isoformat(),
                "subscription_started_at": now.isoformat(),
            }})
            await db.subscriptions.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "plan": claimed["plan_id"], "status": "active",
                          "started_at": now.isoformat()}},
                upsert=True,
            )

@api_router.get("/checkout/status/{session_id}")
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

@api_router.post("/webhook/stripe")
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

# ---------------- Subscription management ----------------
@api_router.get("/subscription")
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
        "plan_credits": int(user.get("plan_credits", 0)),
        "extra_credits": int(user.get("extra_credits", 0)),
        "current_period_end": user.get("current_period_end"),
        "next_credit_reset": user.get("next_credit_reset"),
        "cancel_at_period_end": bool(user.get("cancel_at_period_end", False)),
        "invoices": txns,
    }

@api_router.post("/subscription/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    if user.get("subscription_status") != "active":
        raise HTTPException(status_code=400, detail="No active subscription")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": True}})
    await db.subscriptions.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": True}})
    return {"success": True, "cancel_at_period_end": True}

@api_router.post("/subscription/reactivate")
async def reactivate_subscription(user: dict = Depends(get_current_user)):
    if user.get("subscription_status") != "active" or not user.get("cancel_at_period_end"):
        raise HTTPException(status_code=400, detail="Nothing to reactivate")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": False}})
    await db.subscriptions.update_one({"user_id": user["user_id"]}, {"$set": {"cancel_at_period_end": False}})
    return {"success": True, "cancel_at_period_end": False}

async def subscription_worker():
    """Periodically process active subscriptions for credit resets and renewals."""
    while True:
        try:
            cursor = db.users.find({"subscription_status": "active"}, {"_id": 0})
            async for u in cursor:
                await process_subscription(u)
        except Exception:
            logger.exception("subscription_worker error")
        await asyncio.sleep(3600)

# ---------------- startup ----------------
@api_router.get("/")
async def root():
    return {"message": "SiteGenie API"}

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token")
    await db.templates.create_index("user_id")
    await db.gen_jobs.create_index("job_id")
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
                "role": "admin", "plan_credits": 30, "extra_credits": 100,
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
