"""Tests for POST /api/auth/admin/reset-business-data (owner-only fresh-start)."""
import os
import time
import uuid
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
OWNER_EMAIL = os.environ["OWNER_EMAIL"]
OWNER_PASSWORD = os.environ["OWNER_PASSWORD"]
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


def _register(name, email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"name": name, "email": email, "password": password}, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def owner_session():
    return _login(OWNER_EMAIL, OWNER_PASSWORD)


@pytest.fixture(scope="module")
def mdb():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


@pytest.mark.asyncio
async def test_non_owner_403(mdb):
    # register a throwaway
    email = f"reset_nonowner_{uuid.uuid4().hex[:8]}@example.com"
    s = _register("Non Owner", email, "TestPass123!")
    r = s.post(f"{API}/auth/admin/reset-business-data", json={"confirm": "RESET"}, timeout=30)
    assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"


@pytest.mark.asyncio
async def test_owner_wrong_confirm_400(owner_session):
    r = owner_session.post(f"{API}/auth/admin/reset-business-data", json={"confirm": "reset"}, timeout=30)
    assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"


@pytest.mark.asyncio
async def test_reset_flow(owner_session, mdb):
    # Create throwaway user with a template
    email = f"reset_toclear_{uuid.uuid4().hex[:8]}@example.com"
    throwaway = _register("Throwaway", email, "TestPass123!")
    me = throwaway.get(f"{API}/auth/me", timeout=30)
    assert me.status_code == 200
    throwaway_id = me.json()["user_id"]

    # Insert a template directly for the throwaway user (avoids credit/generation load)
    await mdb.templates.insert_one({
        "template_id": f"tpl_{uuid.uuid4().hex[:8]}",
        "user_id": throwaway_id,
        "name": "TEST throwaway tpl",
        "created_at": time.time(),
    })

    # Owner identity
    om = owner_session.get(f"{API}/auth/me", timeout=30)
    assert om.status_code == 200
    owner_id = om.json()["user_id"]

    # Snapshot counts BEFORE
    before = {
        "users": await mdb.users.count_documents({}),
        "market_listings": await mdb.market_listings.count_documents({}),
        "blog_posts": await mdb.blog_posts.count_documents({}),
        "owner_templates": await mdb.templates.count_documents({"user_id": owner_id}),
        "leads": await mdb.leads.count_documents({}),
        "throwaway_templates": await mdb.templates.count_documents({"user_id": throwaway_id}),
    }
    assert before["throwaway_templates"] >= 1
    assert before["users"] >= 2

    # Reset with include_leads=false
    r = owner_session.post(f"{API}/auth/admin/reset-business-data",
                            json={"confirm": "RESET", "include_leads": False}, timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    assert body["reset"] is True
    assert body["removed_users"] >= 1
    assert body.get("leads_cleared") is False

    # Verify AFTER
    users_after = await mdb.users.count_documents({})
    assert users_after == 1, f"expected only owner, got {users_after}"
    owner_still = await mdb.users.find_one({"user_id": owner_id})
    assert owner_still is not None

    for col in ["payment_transactions", "subscriptions", "gen_jobs", "agent_jobs",
                "agent_chats", "war_room", "war_room_meetings", "team_memos", "team_tasks"]:
        cnt = await mdb[col].count_documents({})
        assert cnt == 0, f"{col} not empty after reset: {cnt}"

    # Throwaway templates gone
    assert await mdb.templates.count_documents({"user_id": throwaway_id}) == 0
    # Owner templates unchanged
    owner_tpls_after = await mdb.templates.count_documents({"user_id": owner_id})
    assert owner_tpls_after == before["owner_templates"], f"owner templates changed: {before['owner_templates']} -> {owner_tpls_after}"
    # Market/blog unchanged
    assert await mdb.market_listings.count_documents({}) == before["market_listings"]
    assert await mdb.blog_posts.count_documents({}) == before["blog_posts"]
    # leads not cleared
    assert await mdb.leads.count_documents({}) == before["leads"]

    # Owner session survives
    me2 = owner_session.get(f"{API}/auth/me", timeout=30)
    assert me2.status_code == 200, f"owner session broke: {me2.status_code} {me2.text}"


@pytest.mark.asyncio
async def test_titan_reflects_zero(owner_session):
    # After reset, titan should not report old numbers
    r = owner_session.post(f"{API}/agents/titan/chat",
                            json={"message": "give me the key numbers"}, timeout=90)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    text = (r.json().get("reply") or r.json().get("message") or "").lower()
    # allow variance — just confirm it doesn't claim ~6 users or $80
    assert "$80" not in text and "80.00" not in text, f"titan still cites $80: {text}"
    assert "6 users" not in text and "6 total users" not in text, f"titan still cites 6 users: {text}"
    print(f"TITAN REPLY: {text[:400]}")
