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
    "monthly":   {"name": "Monthly",  "amount": 19.00,  "credits": 20,  "days": 30,  "interval": "month"},
    "quarterly": {"name": "3-Month",  "amount": 49.00,  "credits": 75,  "days": 90,  "interval": "quarter"},
    "annual":    {"name": "Annual",   "amount": 149.00, "credits": 160, "days": 365, "interval": "year"},
}
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

# ---------------- Auth helpers ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def public_user(u: dict) -> dict:
    return {
        "user_id": u["user_id"],
        "email": u["email"],
        "name": u.get("name", ""),
        "picture": u.get("picture", ""),
        "role": u.get("role", "user"),
        "credits": u.get("credits", 0),
        "plan": u.get("plan"),
        "plan_name": u.get("plan_name"),
        "plan_expires_at": u.get("plan_expires_at"),
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
                        secure=True, samesite="none", max_age=7 * 24 * 3600, path="/")

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
        "role": "user", "credits": 3, "plan": None, "plan_name": None,
        "plan_expires_at": None, "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(doc)
    token = await create_session(user_id)
    set_session_cookie(response, token)
    return public_user(doc)

@api_router.post("/auth/login")
async def login(input: LoginInput, response: Response):
    email = input.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(input.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = await create_session(user["user_id"])
    set_session_cookie(response, token)
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
            "picture": data.get("picture", ""), "role": "user", "credits": 3,
            "plan": None, "plan_name": None, "plan_expires_at": None,
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(user)
    else:
        await db.users.update_one({"email": email}, {"$set": {"picture": data.get("picture", user.get("picture", ""))}})
    token = await create_session(user["user_id"])
    set_session_cookie(response, token)
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

async def _run_generation(job_id: str, user_id: str, input: "GenerateInput"):
    prompt = (
        f"Business name: {input.business_name}\n"
        f"Industry / type: {input.industry}\n"
        f"Description: {input.description}\n"
        f"Design style: {input.style}\n"
        f"Primary brand color: {input.primary_color}\n"
        f"Contact email: {input.contact_email}\n"
        f"Phone: {input.phone}\n"
        "Generate the complete website now."
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"gen_{uuid.uuid4().hex}",
        system_message=GEN_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-6")
    try:
        result = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.exception("generation failed")
        msg = str(e).lower()
        if "budget" in msg or "quota" in msg or "insufficient" in msg:
            err = "AI service is temporarily unavailable. Please try again shortly."
        else:
            err = "Generation failed. Please try again."
        await db.gen_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": err}})
        return

    html = clean_html(result if isinstance(result, str) else str(result))
    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    doc = {
        "template_id": template_id, "user_id": user_id,
        "business_name": input.business_name, "industry": input.industry,
        "description": input.description, "style": input.style,
        "primary_color": input.primary_color, "html": html,
        "created_at": datetime.now(timezone.utc),
    }
    await db.templates.insert_one(doc)
    await db.users.update_one({"user_id": user_id}, {"$inc": {"credits": -CREDIT_COST_PER_TEMPLATE}})
    await db.gen_jobs.update_one({"job_id": job_id},
                                 {"$set": {"status": "done", "template_id": template_id}})

@api_router.post("/templates/generate")
async def generate_template(input: GenerateInput, user: dict = Depends(get_current_user)):
    if user.get("credits", 0) < CREDIT_COST_PER_TEMPLATE:
        raise HTTPException(status_code=402, detail="Not enough credits. Please purchase more.")
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    await db.gen_jobs.insert_one({
        "job_id": job_id, "user_id": user["user_id"], "status": "pending",
        "template_id": None, "error": None, "created_at": datetime.now(timezone.utc),
    })
    asyncio.create_task(_run_generation(job_id, user["user_id"], input))
    return {"job_id": job_id, "status": "pending"}

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
            resp["credits_remaining"] = updated.get("credits", 0)
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
    origin = input.origin_url.rstrip("/")
    success_url = f"{origin}/payment-return?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing"
    metadata = {
        "user_id": user["user_id"], "kind": input.kind, "plan_id": input.plan_id,
        "credits": str(pkg["credits"]),
    }
    stripe = get_stripe(request)
    req = CheckoutSessionRequest(amount=amount, currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session: CheckoutSessionResponse = await stripe.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["user_id"],
        "amount": amount, "currency": "usd", "kind": input.kind,
        "plan_id": input.plan_id, "credits": pkg["credits"],
        "payment_status": "initiated", "status": "open", "processed": False,
        "metadata": metadata, "created_at": datetime.now(timezone.utc),
    })
    return {"url": session.url, "session_id": session.session_id}

async def apply_payment(txn: dict):
    """Grant credits/plan once per session."""
    if txn.get("processed"):
        return
    user_id = txn["user_id"]
    credits = int(txn.get("credits", 0))
    update = {"$inc": {"credits": credits}}
    if txn["kind"] == "subscription":
        plan = SUBSCRIPTION_PLANS.get(txn["plan_id"])
        if plan:
            update["$set"] = {
                "plan": txn["plan_id"], "plan_name": plan["name"],
                "plan_expires_at": (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat(),
            }
    await db.users.update_one({"user_id": user_id}, update)
    await db.payment_transactions.update_one({"session_id": txn["session_id"]}, {"$set": {"processed": True}})

@api_router.get("/checkout/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if event.payment_status == "paid" and event.session_id:
        txn = await db.payment_transactions.find_one({"session_id": event.session_id}, {"_id": 0})
        if txn and not txn.get("processed"):
            await apply_payment(txn)
    return {"received": True}

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
    # seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sitegenie.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "user_id": f"user_{uuid.uuid4().hex[:12]}", "email": admin_email,
            "name": "Admin", "password_hash": hash_password(admin_password), "picture": "",
            "role": "admin", "credits": 100, "plan": "annual", "plan_name": "Annual",
            "plan_expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "created_at": datetime.now(timezone.utc),
        })
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
