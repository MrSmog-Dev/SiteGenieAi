"""Tests for Rex's refined lead accuracy: smart confidence scoring, the 200,000/month discovery
cap, and systematic 50-state rotation. hunt_places()'s Google Places call itself isn't exercised
here (needs a real/mocked network + API key) - these cover the deterministic logic around it."""
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


@pytest.fixture(scope="module")
def owner_session():
    return _login(OWNER_EMAIL, OWNER_PASSWORD)


@pytest.fixture(scope="module")
def mdb():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


# ------ Unit-verify _lead_confidence by importing services.leads ------
def test_lead_confidence_scoring_unit():
    import sys
    sys.path.insert(0, "/app/backend")
    from services.leads import _lead_confidence

    # Strong lead: lots of reviews, great rating, fully contactable -> hot
    strong = _lead_confidence(reviews=250, rating=4.9, phone="555-1234", address="123 Main St")
    assert strong["confidence_score"] > 90
    assert strong["tier"] == "hot"
    assert sum(c["max"] for c in strong["confidence_breakdown"]) == 100

    # Borderline: just clears the Places hunt floor (15 reviews, 3.5 rating), no contact info -> low tier
    weak = _lead_confidence(reviews=15, rating=3.5, phone=None, address=None)
    assert weak["confidence_score"] < strong["confidence_score"]
    assert weak["tier"] in (None, "warm")

    # Monotonic: more reviews at the same rating/contactability never scores lower
    lo = _lead_confidence(reviews=20, rating=4.0, phone="x", address="y")
    hi = _lead_confidence(reviews=150, rating=4.0, phone="x", address="y")
    assert hi["confidence_score"] >= lo["confidence_score"]


@pytest.mark.asyncio
async def test_monthly_cap_counts_only_discovery_sources(mdb):
    import sys
    sys.path.insert(0, "/app/backend")
    from services.leads import leads_this_month_count
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    marker = uuid.uuid4().hex[:8]
    before = await leads_this_month_count()

    await mdb.leads.insert_one({
        "lead_id": f"lead_test_{marker}_a", "dedupe_key": f"place:test_{marker}_a",
        "source": "no_website", "business_name": f"Cap Test A {marker}", "status": "new",
        "created_at": now, "updated_at": now,
    })
    await mdb.leads.insert_one({
        "lead_id": f"lead_test_{marker}_b", "dedupe_key": f"site:test_{marker}_b",
        "source": "weak_website", "business_name": f"Cap Test B {marker}", "status": "new",
        "created_at": now, "updated_at": now,
    })
    after = await leads_this_month_count()
    assert after == before + 2


@pytest.mark.asyncio
async def test_state_rotation_prefers_never_hunted_then_oldest(mdb):
    import sys
    sys.path.insert(0, "/app/backend")
    from services.leads import least_recent_states, mark_state_hunted, US_STATES

    marker = uuid.uuid4().hex[:8]
    fake_state = f"Testlandia{marker}"
    # Not a real state, so it should never surface from least_recent_states (only real US_STATES rotate)
    await mark_state_hunted(fake_state)
    ranked = await least_recent_states(len(US_STATES))
    assert fake_state not in ranked
    assert set(ranked) == set(US_STATES)

    # Hunting the top-ranked state should push it to the back of the rotation
    top = ranked[0]
    await mark_state_hunted(top)
    time.sleep(0.01)
    ranked_after = await least_recent_states(len(US_STATES))
    assert ranked_after[-1] == top


@pytest.mark.asyncio
async def test_hunt_status_reports_monthly_budget(owner_session):
    r = owner_session.get(f"{API}/leads/hunt/status", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "leads_remaining_this_month" in data
    assert "monthly_lead_cap" in data
    assert data["monthly_lead_cap"] == 200_000
    assert 0 <= data["leads_remaining_this_month"] <= 200_000
