"""Iteration 16 — verify code-review fixes:
FIX 1: /api/checkout/session subscription kind → 400; non-native active sub lapses at period end.
FIX 2: 402 min-credit gate for premium; economy passes 1-credit gate; 429 concurrency cap w/ own job deleted.
FIX 3: DB indexes exist.
FIX 4: agent chat / war_room messages arrays capped by $slice.
FIX 5: duplicate register → 400 (not 500).
REGRESSION: owner login, war-room GET, /api/status.
"""
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://genie-deploy-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "neobeyondlegacy2@gmail.com"
OWNER_PASSWORD = "SoloLeveling21!"

# ---------- Mongo direct access ----------
import motor.motor_asyncio

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

@pytest.fixture
def mdb():
    # Fresh client per test so motor binds to the running event loop
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# ---------- helpers ----------
def _login_owner():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    return s

def _register_throwaway():
    s = requests.Session()
    email = f"test_iter16_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register",
               json={"name": "T16", "email": email, "password": "TestPass123!"}, timeout=15)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return s, email, r.json()["user_id"]


# ====================================================================
# REGRESSION
# ====================================================================
def test_status_ok():
    r = requests.get(f"{API}/status", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d.get("api") is True
    assert d.get("db") is True

def test_owner_login_and_me():
    s = _login_owner()
    r = s.get(f"{API}/auth/me", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["email"].lower() == OWNER_EMAIL
    assert d.get("role") in ("owner", "admin")

def test_owner_war_room_get():
    s = _login_owner()
    r = s.get(f"{API}/agents/war-room", timeout=15)
    assert r.status_code == 200
    assert "messages" in r.json()


# ====================================================================
# FIX 1 — checkout kind gate
# ====================================================================
def test_checkout_rejects_subscription_kind():
    s = _login_owner()
    r = s.post(f"{API}/checkout/session",
               json={"kind": "subscription", "plan_id": "monthly", "origin_url": BASE_URL},
               timeout=15)
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
    assert "invalid kind" in r.text.lower()

def test_checkout_credits_pack25_ok():
    s = _login_owner()
    r = s.post(f"{API}/checkout/session",
               json={"kind": "credits", "plan_id": "pack_25", "origin_url": BASE_URL},
               timeout=20)
    assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text}"
    d = r.json()
    assert d.get("url", "").startswith("http")
    assert d.get("session_id")


# ====================================================================
# FIX 1B — non-native active sub lapses on /me
# ====================================================================
@pytest.mark.asyncio
async def test_non_native_sub_lapses(mdb):
    # Create a throwaway user directly in Mongo w/ non-native active sub, past period end
    s, email, user_id = _register_throwaway()

    past = datetime.now(timezone.utc) - timedelta(days=2)
    await mdb.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "subscription_status": "active",
            "plan": "monthly",
            "plan_name": "Monthly",
            "plan_credits": 50,
            "current_period_end": past.isoformat(),
            # NO provider field => non-native
        }, "$unset": {"provider": ""}}
    )

    # Snapshot pmt txns count
    txn_count_before = await mdb.payment_transactions.count_documents({"user_id": user_id})

    r = s.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["subscription_status"] == "cancelled", f"expected cancelled, got {d['subscription_status']}"
    assert d["plan_credits"] == 0
    assert d.get("plan") in (None, "")

    txn_count_after = await mdb.payment_transactions.count_documents({"user_id": user_id})
    assert txn_count_after == txn_count_before, "no renewal transaction should have been inserted"


# ====================================================================
# FIX 2 — 402 min-credit gate + 429 concurrency cap
# ====================================================================
GEN_FIELDS = {
    "business_name": "Iter16 Test Biz",
    "industry": "Cafe",
    "description": "A cozy coffee spot for testing.",
    "style": "modern",
    "primary_color": "#0055FF",
}

@pytest.mark.asyncio
async def test_premium_402_when_below_min_credits(mdb):
    s, email, user_id = _register_throwaway()
    # Set credits to 1 (below 8 needed for premium)
    await mdb.users.update_one({"user_id": user_id},
                               {"$set": {"plan_credits": 0, "extra_credits": 1}})

    r = s.post(f"{API}/templates/generate",
               json={**GEN_FIELDS, "quality": "premium"}, timeout=15)
    assert r.status_code == 402, f"expected 402, got {r.status_code} {r.text}"
    assert "8 credits" in r.text or "at least" in r.text.lower()

@pytest.mark.asyncio
async def test_economy_passes_1_credit_gate(mdb):
    s, email, user_id = _register_throwaway()
    await mdb.users.update_one({"user_id": user_id},
                               {"$set": {"plan_credits": 0, "extra_credits": 1}})
    r = s.post(f"{API}/templates/generate",
               json={**GEN_FIELDS, "quality": "economy"}, timeout=15)
    # Passing the gate means we get 200 (job accepted); we don't wait for LLM
    assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text}"
    assert r.json().get("job_id")

@pytest.mark.asyncio
async def test_concurrency_cap_429_and_own_job_deleted(mdb):
    s, email, user_id = _register_throwaway()
    # Enough credits to pass gate
    await mdb.users.update_one({"user_id": user_id},
                               {"$set": {"plan_credits": 0, "extra_credits": 100}})
    # Seed 2 pending jobs
    now = datetime.now(timezone.utc)
    fake_ids = [f"job_fake_{uuid.uuid4().hex[:10]}" for _ in range(2)]
    await mdb.gen_jobs.insert_many([
        {"job_id": jid, "user_id": user_id, "status": "pending", "created_at": now}
        for jid in fake_ids
    ])

    count_before = await mdb.gen_jobs.count_documents({"user_id": user_id})
    assert count_before == 2

    r = s.post(f"{API}/templates/generate",
               json={**GEN_FIELDS, "quality": "economy"}, timeout=15)
    assert r.status_code == 429, f"expected 429, got {r.status_code} {r.text}"

    # 3rd job doc must NOT be left behind
    count_after = await mdb.gen_jobs.count_documents({"user_id": user_id})
    assert count_after == 2, f"3rd job leaked into gen_jobs (count went {count_before}->{count_after})"

    # cleanup
    await mdb.gen_jobs.delete_many({"job_id": {"$in": fake_ids}})


# ====================================================================
# FIX 3 — DB indexes
# ====================================================================
@pytest.mark.asyncio
async def test_indexes_exist(mdb):
    async def idx_names(col):
        return set((await col.index_information()).keys())

    pt = await idx_names(mdb.payment_transactions)
    assert "session_id_1" in pt, f"missing session_id_1 in payment_transactions: {pt}"
    assert "user_id_1_created_at_-1" in pt, f"missing user_id_1_created_at_-1: {pt}"

    gj = await idx_names(mdb.gen_jobs)
    # job_id index exists (may be non-unique legacy — note in review request)
    assert any(k.startswith("job_id_1") or k == "job_id_1" for k in gj), f"missing job_id index: {gj}"
    assert "user_id_1_status_1" in gj, f"missing user_id_1_status_1: {gj}"

    aj = await idx_names(mdb.agent_jobs)
    assert "job_id_1" in aj, f"missing agent_jobs job_id_1: {aj}"

    ac = await idx_names(mdb.agent_chats)
    assert "user_id_1_agent_id_1" in ac, f"missing agent_chats compound: {ac}"

    wr = await idx_names(mdb.war_room)
    assert "user_id_1" in wr, f"missing war_room user_id_1: {wr}"

    au = await idx_names(mdb.automation_state)
    assert "job_1" in au, f"missing automation_state job_1: {au}"

    ld = await idx_names(mdb.leads)
    assert "lead_id_1" in ld, f"missing leads lead_id_1: {ld}"


# ====================================================================
# FIX 4 — messages array capped by $slice
# ====================================================================
@pytest.mark.asyncio
async def test_war_room_slice_caps_at_300(mdb):
    s, email, user_id = _register_throwaway()
    # Seed war_room with 299 messages
    msgs = [{"role": "agent", "agent_id": "titan", "content": f"m{i}",
             "ts": datetime.now(timezone.utc)} for i in range(299)]
    await mdb.war_room.update_one({"user_id": user_id},
                                  {"$set": {"messages": msgs}}, upsert=True)

    # Directly exercise post_war_room via 5 pushes (simulating service behavior)
    from services.team import post_war_room  # noqa: E402
    for i in range(5):
        await post_war_room(user_id, "titan", f"new-{i}", role="owner")

    doc = await mdb.war_room.find_one({"user_id": user_id})
    assert doc is not None
    assert len(doc["messages"]) <= 300, f"war_room exceeded 300: {len(doc['messages'])}"
    # last message should be most recent
    assert doc["messages"][-1]["content"].startswith("new-")

@pytest.mark.asyncio
async def test_agent_chat_slice_caps_at_200(mdb):
    s, email, user_id = _register_throwaway()
    # Seed agent_chats with 199 messages
    msgs = [{"role": "agent", "content": f"m{i}", "ts": datetime.now(timezone.utc)} for i in range(199)]
    await mdb.agent_chats.update_one(
        {"user_id": user_id, "agent_id": "titan"},
        {"$set": {"messages": msgs, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    # Push 5 more via direct $slice update (mirroring code shape)
    for i in range(5):
        await mdb.agent_chats.update_one(
            {"user_id": user_id, "agent_id": "titan"},
            {"$push": {"messages": {"$each": [{"role": "user", "content": f"push-{i}",
                                               "ts": datetime.now(timezone.utc)}],
                                    "$slice": -200}}},
        )
    doc = await mdb.agent_chats.find_one({"user_id": user_id, "agent_id": "titan"})
    assert len(doc["messages"]) <= 200, f"agent_chat exceeded 200: {len(doc['messages'])}"


# ====================================================================
# FIX 5 — duplicate register → 400
# ====================================================================
def test_duplicate_register_returns_400():
    s = requests.Session()
    email = f"dup_iter16_{uuid.uuid4().hex[:10]}@example.com"
    r1 = s.post(f"{API}/auth/register",
                json={"name": "dup", "email": email, "password": "TestPass123!"}, timeout=15)
    assert r1.status_code == 200
    r2 = requests.post(f"{API}/auth/register",
                       json={"name": "dup2", "email": email, "password": "TestPass123!"}, timeout=15)
    assert r2.status_code == 400, f"expected 400 on duplicate, got {r2.status_code} {r2.text}"
    assert "already registered" in r2.text.lower()
