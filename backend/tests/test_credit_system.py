"""Backend tests for reworked usage-based credit system (iteration 6)."""
import os
import time
import uuid
import asyncio
import pytest
import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin@sitegenie.com"
ADMIN_PW = "Sg!Adm1n_9f3kQ2xL7vB"


def _unique_ip():
    return f"10.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def _register(email=None, password="TestPass!23"):
    # Register endpoint lowercases email; use lowercase 'test_' prefix so
    # our cleanup regex ^TEST_ (case-insensitive) matches, and mongo lookups work.
    email = email or f"test_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"name": "Tester", "email": email, "password": password},
                      headers={"X-Forwarded-For": _unique_ip()})
    assert r.status_code == 200, r.text
    return email, r.cookies.get("session_token")


def _login_admin():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PW},
                      headers={"X-Forwarded-For": _unique_ip()})
    assert r.status_code == 200, r.text
    return r.cookies.get("session_token")


def _me(token):
    return requests.get(f"{API}/auth/me", cookies={"session_token": token})


# ------ Plans ------
def test_plans_endpoint_shape():
    r = requests.get(f"{API}/plans")
    assert r.status_code == 200
    data = r.json()
    subs = data["subscriptions"]
    assert subs["monthly"]["amount"] == 20 and subs["monthly"]["monthly_credits"] == 50 and subs["monthly"]["unlimited"] is False
    assert subs["quarterly"]["amount"] == 49 and subs["quarterly"]["monthly_credits"] == 120 and subs["quarterly"]["unlimited"] is False
    assert subs["annual"]["amount"] == 149 and subs["annual"]["unlimited"] is True
    packs = data["credit_packs"]
    assert packs["pack_25"]["amount"] == 9 and packs["pack_25"]["credits"] == 25
    assert packs["pack_60"]["amount"] == 19 and packs["pack_60"]["credits"] == 60
    assert packs["pack_150"]["amount"] == 39 and packs["pack_150"]["credits"] == 150


# ------ Register grants 15 credits ------
def test_register_grants_15_extra_credits():
    email, token = _register()
    r = _me(token)
    assert r.status_code == 200
    data = r.json()
    assert data["credits"] == 15
    assert data["plan_credits"] == 0
    assert data["extra_credits"] == 15
    assert data["unlimited"] is False


# ------ 402 gating ------
@pytest.mark.asyncio
async def test_402_gating_zero_credits():
    email, token = _register()
    # Set both credits to 0
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.update_one({"email": email},
                               {"$set": {"plan_credits": 0, "extra_credits": 0}})
    client.close()

    r = requests.post(f"{API}/templates/generate",
                       json={"business_name": "T", "industry": "x", "description": "y"},
                       cookies={"session_token": token})
    assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"
    body = r.json()
    assert "credit" in (body.get("detail", "") or "").lower()

    # No job created
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    u = await db.users.find_one({"email": email})
    n_jobs = await db.gen_jobs.count_documents({"user_id": u["user_id"]})
    n_tpls = await db.templates.count_documents({"user_id": u["user_id"]})
    client.close()
    assert n_jobs == 0
    assert n_tpls == 0


# ------ Start job with credits returns job_id and no deduction on error ------
@pytest.mark.asyncio
async def test_start_job_with_credits_and_no_deduction_on_error():
    email, token = _register()
    # Register grants 15 credits - good
    r = requests.post(f"{API}/templates/generate",
                       json={"business_name": "Acme", "industry": "cafe", "description": "d"},
                       cookies={"session_token": token})
    assert r.status_code == 200, r.text
    job = r.json()
    assert "job_id" in job and job.get("status") == "pending"

    # Wait for job to finish (LLM budget exhausted -> should error)
    for _ in range(30):
        st = requests.get(f"{API}/templates/job/{job['job_id']}", cookies={"session_token": token}).json()
        if st.get("status") in ("done", "error"):
            break
        time.sleep(1)
    # Verify credits unchanged if errored
    me = _me(token).json()
    if st.get("status") == "error":
        assert me["credits"] == 15, f"Credits should be unchanged after error, got {me['credits']}"
    else:
        # If somehow LLM succeeded, credits may have been deducted; still allowed
        assert me["credits"] <= 15


# ------ Unlimited (annual) bypass ------
@pytest.mark.asyncio
async def test_annual_unlimited_bypass():
    email, token = _register()
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.update_one(
        {"email": email},
        {"$set": {"plan": "annual", "plan_name": "Annual",
                  "subscription_status": "active",
                  "plan_credits": 0, "extra_credits": 0}})
    client.close()

    # /auth/me shows unlimited
    me = _me(token).json()
    assert me["unlimited"] is True, me
    # /subscription includes unlimited
    sub = requests.get(f"{API}/subscription", cookies={"session_token": token}).json()
    assert sub.get("unlimited") is True

    # generate must NOT be blocked despite 0 credits
    r = requests.post(f"{API}/templates/generate",
                       json={"business_name": "T", "industry": "x", "description": "y"},
                       cookies={"session_token": token})
    assert r.status_code == 200, f"unlimited user blocked: {r.status_code} {r.text}"
    assert "job_id" in r.json()


# ------ Unit-verify estimate_cost + deduct_credits by importing server ------
def test_estimate_cost_and_deduct_credits_unit():
    import sys
    sys.path.insert(0, "/app/backend")
    from server import estimate_cost, TOKENS_PER_CREDIT

    # small op
    assert estimate_cost("hi") == 1
    # ~5 credits ~ create: 60,000 chars -> 15,000 tokens -> 5 credits
    assert estimate_cost("x" * 60000) == 5
    # ~10 credits ~ edit: 120,000 chars -> 30,000 tokens -> 10 credits
    assert estimate_cost("x" * 120000) == 10

    # deduct_credits via mongo
    async def _run():
        from server import deduct_credits, db as srv_db
        uid = f"TEST_deduct_{uuid.uuid4().hex[:8]}"
        await srv_db.users.insert_one({"user_id": uid, "email": f"{uid}@t.io",
                                       "plan_credits": 10, "extra_credits": 5})
        await deduct_credits(uid, 12)
        u = await srv_db.users.find_one({"user_id": uid})
        assert u["plan_credits"] == 0 and u["extra_credits"] == 3, u
        # over-deduct
        await deduct_credits(uid, 999)
        u = await srv_db.users.find_one({"user_id": uid})
        assert u["plan_credits"] == 0 and u["extra_credits"] == 0
        await srv_db.users.delete_one({"user_id": uid})
    asyncio.run(_run())


# ------ Regressions ------
def test_admin_login_and_me():
    token = _login_admin()
    r = _me(token)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == ADMIN_EMAIL

def test_list_templates_admin():
    token = _login_admin()
    r = requests.get(f"{API}/templates", cookies={"session_token": token})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ------ Cleanup ------
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_users():
    yield
    async def _c():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        emails = await db.users.find({"email": {"$regex": "^test_"}}, {"user_id": 1, "email": 1}).to_list(500)
        ids = [u["user_id"] for u in emails]
        if ids:
            await db.users.delete_many({"user_id": {"$in": ids}})
            await db.user_sessions.delete_many({"user_id": {"$in": ids}})
            await db.gen_jobs.delete_many({"user_id": {"$in": ids}})
            await db.templates.delete_many({"user_id": {"$in": ids}})
        client.close()
    try:
        asyncio.run(_c())
    except Exception:
        pass
