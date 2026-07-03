"""AI Team feature backend tests"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://builder-hub-795.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "neobeyondlegacy2@gmail.com"
OWNER_PASSWORD = "SoloLeveling21!"

EXPECTED_AGENTS = {"titan", "nova", "atlas", "ledger", "quill", "ivy",
                   "blaze", "mara", "rex", "halo", "forge", "zephyr"}


# --- fixtures ---
@pytest.fixture(scope="module")
def owner_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_session():
    s = requests.Session()
    email = f"TEST_aiteam_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register",
               json={"name": "TEST User", "email": email, "password": "TestPass123!"}, timeout=30)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return s


# --- owner gating ---
class TestOwnerGating:
    def test_unauthed_agents_list(self):
        r = requests.get(f"{API}/agents", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_owner_lists_12_agents(self, owner_session):
        r = owner_session.get(f"{API}/agents", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) and len(data) == 12
        ids = {a["id"] for a in data}
        assert ids == EXPECTED_AGENTS
        for a in data:
            for k in ("id", "name", "role", "color", "tagline", "quick_actions"):
                assert k in a, f"missing {k} in {a}"
            assert isinstance(a["quick_actions"], list) and len(a["quick_actions"]) >= 1

    def test_non_owner_forbidden(self, user_session):
        r = user_session.get(f"{API}/agents", timeout=30)
        assert r.status_code == 403, f"expected 403 for non-owner, got {r.status_code}"


# --- chat with live data + history ---
class TestChat:
    def test_invalid_agent_404(self, owner_session):
        r = owner_session.post(f"{API}/agents/notanagent/chat", json={"message": "hi"}, timeout=30)
        assert r.status_code == 404

    def test_empty_message_400(self, owner_session):
        r = owner_session.post(f"{API}/agents/ledger/chat", json={"message": "   "}, timeout=30)
        assert r.status_code in (400, 422)

    def test_clear_then_chat_and_history_and_multi_turn(self, owner_session):
        # clear
        r = owner_session.delete(f"{API}/agents/ledger/chat", timeout=30)
        assert r.status_code == 200
        # verify empty history
        r = owner_session.get(f"{API}/agents/ledger/chat", timeout=30)
        assert r.status_code == 200
        assert r.json()["messages"] == []

        # first message
        r = owner_session.post(
            f"{API}/agents/ledger/chat",
            json={"message": "What is our all-time revenue by stream? one line"},
            timeout=180)
        assert r.status_code == 200, r.text
        reply1 = r.json()["reply"]
        assert isinstance(reply1, str) and len(reply1) > 5
        # should mention a revenue-related keyword
        low = reply1.lower()
        assert any(k in low for k in ("subscription", "credit", "market", "revenue", "$", "mrr")), \
            f"reply not grounded: {reply1}"

        # multi-turn follow-up
        r2 = owner_session.post(
            f"{API}/agents/ledger/chat",
            json={"message": "Now repeat the first number you just gave me."},
            timeout=180)
        assert r2.status_code == 200, r2.text
        reply2 = r2.json()["reply"]
        assert isinstance(reply2, str) and len(reply2) > 0

        # history has all 4 messages
        r3 = owner_session.get(f"{API}/agents/ledger/chat", timeout=30)
        assert r3.status_code == 200
        msgs = r3.json()["messages"]
        assert len(msgs) == 4
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "agent"
        assert msgs[3]["role"] == "agent"

    def test_clear_wipes_history(self, owner_session):
        r = owner_session.delete(f"{API}/agents/ledger/chat", timeout=30)
        assert r.status_code == 200
        r = owner_session.get(f"{API}/agents/ledger/chat", timeout=30)
        assert r.json()["messages"] == []


# --- forge build ---
class TestForge:
    def test_non_owner_forge_forbidden(self, user_session):
        r = user_session.post(f"{API}/agents/forge/build",
                              json={"brief": "modern pet grooming salon"}, timeout=30)
        assert r.status_code == 403

    def test_forge_build_flow(self, owner_session):
        # start
        r = owner_session.post(f"{API}/agents/forge/build",
                               json={"brief": "modern pet grooming salon"}, timeout=30)
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        assert job_id.startswith("forge_")

        # concurrent -> 409
        r2 = owner_session.post(f"{API}/agents/forge/build",
                                json={"brief": "another niche"}, timeout=30)
        assert r2.status_code == 409, f"expected 409 concurrent, got {r2.status_code}"

        # poll up to ~6 min
        deadline = time.time() + 360
        final = None
        while time.time() < deadline:
            r = owner_session.get(f"{API}/agents/jobs/{job_id}", timeout=30)
            assert r.status_code == 200
            data = r.json()
            status = data.get("status")
            if status in ("done", "error"):
                final = data
                break
            time.sleep(10)
        assert final is not None, "forge job never completed within 6 min"
        assert final["status"] == "done", f"forge job failed: {final}"
        result = final.get("result") or {}
        assert "market_id" in result
        assert "title" in result and result["title"]
        price = result.get("price_usd")
        assert isinstance(price, (int, float)) and 200 <= price <= 500
        assert result.get("tier")

        # verify listing appears on market
        rm = owner_session.get(f"{API}/market", timeout=30)
        assert rm.status_code == 200
        market_body = rm.json()
        listings = market_body if isinstance(market_body, list) else market_body.get("listings", [])
        ids = [l.get("market_id") for l in listings]
        assert result["market_id"] in ids, "new forge listing not on market"


# --- regression ---
class TestRegression:
    def test_market_public(self):
        r = requests.get(f"{API}/market", timeout=30)
        assert r.status_code == 200
