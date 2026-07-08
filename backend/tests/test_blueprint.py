"""Tests for the Website Blueprint API (/api/blueprints/*).

A Blueprint is standalone - created with no template_id and no generated website.
Covers create/list/get, progressive spec updates with version bump + history,
status transitions, ownership scoping, and delete.
"""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"


def _register(name, email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"name": name, "email": email, "password": password}, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    email = f"blueprint_user_{uuid.uuid4().hex[:8]}@example.com"
    return _register("Blueprint Tester", email, "TestPass123!")


@pytest.mark.asyncio
async def test_create_blueprint_standalone_no_template(user_session):
    r = user_session.post(f"{API}/blueprints", json={"name": "Coffee Shop Project"}, timeout=30)
    assert r.status_code == 200, r.text
    bp = r.json()
    assert bp["name"] == "Coffee Shop Project"
    assert bp["status"] == "draft"
    assert bp["version"] == 1
    assert bp["spec"] == {}
    assert "template_id" not in bp


@pytest.mark.asyncio
async def test_create_with_partial_spec(user_session):
    r = user_session.post(f"{API}/blueprints",
                           json={"name": "Bakery", "spec": {"business_name": "Flour & Co", "industry": "bakery"}},
                           timeout=30)
    assert r.status_code == 200, r.text
    bp = r.json()
    assert bp["spec"]["business_name"] == "Flour & Co"
    assert bp["spec"]["industry"] == "bakery"


@pytest.mark.asyncio
async def test_progressive_update_bumps_version_and_history(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "Gym"}, timeout=30).json()
    bp_id = created["blueprint_id"]

    r1 = user_session.put(f"{API}/blueprints/{bp_id}",
                           json={"spec": {"business_name": "Iron Yard"}}, timeout=30)
    assert r1.status_code == 200, r1.text
    bp1 = r1.json()
    assert bp1["version"] == 2
    assert bp1["spec"]["business_name"] == "Iron Yard"
    assert len(bp1["history"]) == 1
    assert bp1["history"][0]["version"] == 1

    r2 = user_session.put(f"{API}/blueprints/{bp_id}",
                           json={"spec": {"industry": "fitness"}}, timeout=30)
    assert r2.status_code == 200, r2.text
    bp2 = r2.json()
    assert bp2["version"] == 3
    # merge semantics: prior fields survive an update that only sets new ones
    assert bp2["spec"]["business_name"] == "Iron Yard"
    assert bp2["spec"]["industry"] == "fitness"
    assert len(bp2["history"]) == 2


@pytest.mark.asyncio
async def test_status_transition_to_ready(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "Salon"}, timeout=30).json()
    bp_id = created["blueprint_id"]
    r = user_session.put(f"{API}/blueprints/{bp_id}/status", json={"status": "ready"}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_status_rejects_invalid_value(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "Salon 2"}, timeout=30).json()
    bp_id = created["blueprint_id"]
    r = user_session.put(f"{API}/blueprints/{bp_id}/status", json={"status": "not_a_real_status"}, timeout=30)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_and_get(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "Detail List Test"}, timeout=30).json()
    bp_id = created["blueprint_id"]

    lst = user_session.get(f"{API}/blueprints", timeout=30)
    assert lst.status_code == 200
    assert any(b["blueprint_id"] == bp_id for b in lst.json())
    # list projection omits history to stay small
    assert all("history" not in b for b in lst.json())

    got = user_session.get(f"{API}/blueprints/{bp_id}", timeout=30)
    assert got.status_code == 200
    assert got.json()["blueprint_id"] == bp_id


@pytest.mark.asyncio
async def test_other_user_cannot_access(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "Private"}, timeout=30).json()
    bp_id = created["blueprint_id"]

    other = _register("Other User", f"blueprint_other_{uuid.uuid4().hex[:8]}@example.com", "TestPass123!")
    r = other.get(f"{API}/blueprints/{bp_id}", timeout=30)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_blueprint(user_session):
    created = user_session.post(f"{API}/blueprints", json={"name": "To Delete"}, timeout=30).json()
    bp_id = created["blueprint_id"]
    r = user_session.delete(f"{API}/blueprints/{bp_id}", timeout=30)
    assert r.status_code == 200
    assert r.json()["success"] is True

    got = user_session.get(f"{API}/blueprints/{bp_id}", timeout=30)
    assert got.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_rejected():
    r = requests.post(f"{API}/blueprints", json={"name": "No Auth"}, timeout=30)
    assert r.status_code in (401, 403)
