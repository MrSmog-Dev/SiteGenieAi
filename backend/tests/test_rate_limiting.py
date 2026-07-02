"""
Iteration 4 - Rate Limiting tests
Covers:
  (A) Login brute-force IP+email lockout (5/15min)
  (B) Successful login clears attempt counter
  (C) Generation rate limit per-user (15/5min)
  (D) Per-user isolation of generation limit
  (E) Regression sanity for core flows (register, /auth/me, templates, subscription)
"""
import os
import uuid
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@sitegenie.com"
ADMIN_PASSWORD = "Sg!Adm1n_9f3kQ2xL7vB"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


def _unique_ip(tag: str) -> str:
    # deterministic-ish but unique per test run; use 10.x private range
    n = uuid.uuid4().int
    return f"10.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{n & 0xFF}"


def _cleanup_login(identifier_prefix_email: str, ips=None):
    q = {"identifier": {"$regex": f":{identifier_prefix_email}$"}}
    db.login_attempts.delete_many(q)
    if ips:
        for ip in ips:
            db.login_attempts.delete_many({"identifier": f"{ip}:{identifier_prefix_email}"})


def _register_user():
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:10]}@example.com"
    pw = "pw123456"
    r = s.post(f"{API}/auth/register", json={"name": "TEST", "email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, r.text
    return s, email, pw, r.json()


# ---------------- (A) brute-force lock ----------------
class TestLoginBruteForce:
    def test_five_wrong_then_locked_same_ip_correct_locked_diff_ip_ok(self):
        _, email, pw, _ = _register_user()
        ip_a = _unique_ip("A")
        ip_b = _unique_ip("B")
        # ensure clean
        db.login_attempts.delete_many({"identifier": {"$in": [f"{ip_a}:{email}", f"{ip_b}:{email}"]}})

        headers_a = {"X-Forwarded-For": ip_a}
        # 5 wrong -> all 401
        for i in range(5):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "wrong"},
                              headers=headers_a, timeout=30)
            assert r.status_code == 401, f"Attempt {i+1}: expected 401, got {r.status_code} {r.text}"

        # 6th wrong -> 429
        r = requests.post(f"{API}/auth/login",
                          json={"email": email, "password": "wrong"},
                          headers=headers_a, timeout=30)
        assert r.status_code == 429, f"Expected 429 on 6th, got {r.status_code} {r.text}"

        # correct pw same IP -> still 429 (locked)
        r = requests.post(f"{API}/auth/login",
                          json={"email": email, "password": pw},
                          headers=headers_a, timeout=30)
        assert r.status_code == 429, f"Locked IP with correct pw should be 429, got {r.status_code}"

        # correct pw different IP -> 200
        r = requests.post(f"{API}/auth/login",
                          json={"email": email, "password": pw},
                          headers={"X-Forwarded-For": ip_b}, timeout=30)
        assert r.status_code == 200, f"Different IP correct pw should be 200, got {r.status_code} {r.text}"

        # cleanup
        db.login_attempts.delete_many({"identifier": {"$in": [f"{ip_a}:{email}", f"{ip_b}:{email}"]}})

    def test_successful_login_clears_counter(self):
        _, email, pw, _ = _register_user()
        ip = _unique_ip("C")
        db.login_attempts.delete_many({"identifier": f"{ip}:{email}"})
        headers = {"X-Forwarded-For": ip}

        # 3 wrong
        for i in range(3):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"},
                              headers=headers, timeout=30)
            assert r.status_code == 401

        # correct -> 200
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw},
                          headers=headers, timeout=30)
        assert r.status_code == 200

        # counter should be cleared -> 3 more wrong should NOT lock (would need 5 in a row)
        for i in range(3):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"},
                              headers=headers, timeout=30)
            assert r.status_code == 401, f"Post-clear wrong #{i+1} expected 401 got {r.status_code}"

        # 4th wrong still 401 (only 4 in window)
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"},
                          headers=headers, timeout=30)
        assert r.status_code == 401

        db.login_attempts.delete_many({"identifier": f"{ip}:{email}"})


# ---------------- (C,D) generation rate limit ----------------
class TestGenerateRateLimit:
    @pytest.fixture
    def user_a(self):
        s, email, pw, data = _register_user()
        # Give user plenty of credits so 402 doesn't interfere
        db.users.update_one({"user_id": data["user_id"]}, {"$set": {"extra_credits": 100}})
        # clear rate_events for this user
        db.rate_events.delete_many({"key": f"gen:{data['user_id']}"})
        return {"session": s, "email": email, "user_id": data["user_id"]}

    @pytest.fixture
    def user_b(self):
        s, email, pw, data = _register_user()
        db.users.update_one({"user_id": data["user_id"]}, {"$set": {"extra_credits": 100}})
        db.rate_events.delete_many({"key": f"gen:{data['user_id']}"})
        return {"session": s, "email": email, "user_id": data["user_id"]}

    def test_16th_generate_returns_429_and_other_user_unaffected(self, user_a, user_b):
        payload = {
            "business_name": "TestCo",
            "industry": "Tech",
            "description": "A test business for rate limiting.",
            "tone": "professional",
            "color_scheme": "blue",
        }
        s = user_a["session"]
        statuses = []
        for i in range(15):
            r = s.post(f"{API}/templates/generate", json=payload, timeout=30)
            statuses.append(r.status_code)
        assert all(sc == 200 for sc in statuses), f"First 15 should be 200 but got: {statuses}"

        # 16th
        r = s.post(f"{API}/templates/generate", json=payload, timeout=30)
        assert r.status_code == 429, f"16th should be 429, got {r.status_code} {r.text}"

        # user_b unaffected
        r2 = user_b["session"].post(f"{API}/templates/generate", json=payload, timeout=30)
        assert r2.status_code == 200, f"User B first generate should be 200, got {r2.status_code} {r2.text}"

        # cleanup
        db.rate_events.delete_many({"key": f"gen:{user_a['user_id']}"})
        db.rate_events.delete_many({"key": f"gen:{user_b['user_id']}"})


# ---------------- (E) regression sanity ----------------
class TestRegressionCore:
    def test_admin_login_still_works_and_me(self):
        # use unique IP to avoid interfering with any leftover locks
        ip = _unique_ip("adm")
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                          headers={"X-Forwarded-For": ip}, timeout=30)
        assert r.status_code == 200, r.text
        # HttpOnly + Secure + SameSite=Lax
        raw = r.raw.headers
        set_cookies = [v for k, v in raw.items() if k.lower() == "set-cookie"]
        session_cookie = next((c for c in set_cookies if c.startswith("session_token=")), None)
        assert session_cookie, f"No session_token cookie set: {set_cookies}"
        low = session_cookie.lower()
        assert "httponly" in low
        assert "secure" in low
        assert "samesite=lax" in low
        # cleanup any admin attempts we may have created
        db.login_attempts.delete_many({"identifier": f"{ip}:{ADMIN_EMAIL}"})

        s = requests.Session()
        s.cookies.set("session_token", r.cookies.get("session_token"))
        me = s.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json()["email"] == ADMIN_EMAIL

    def test_old_admin_password_rejected(self):
        ip = _unique_ip("oldp")
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "admin123"},
                          headers={"X-Forwarded-For": ip}, timeout=30)
        assert r.status_code == 401
        db.login_attempts.delete_many({"identifier": f"{ip}:{ADMIN_EMAIL}"})

    def test_subscription_cancel_reactivate(self):
        ip = _unique_ip("sub")
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                   headers={"X-Forwarded-For": ip}, timeout=30)
        assert r.status_code == 200
        r = s.get(f"{API}/subscription", timeout=30)
        assert r.status_code == 200
        cancel = s.post(f"{API}/subscription/cancel", timeout=30)
        assert cancel.status_code == 200
        assert cancel.json().get("cancel_at_period_end") is True
        react = s.post(f"{API}/subscription/reactivate", timeout=30)
        assert react.status_code == 200
        assert react.json().get("cancel_at_period_end") is False
        db.login_attempts.delete_many({"identifier": f"{ip}:{ADMIN_EMAIL}"})

    def test_402_gating_zero_credits(self):
        s, email, pw, data = _register_user()
        db.users.update_one({"user_id": data["user_id"]},
                            {"$set": {"extra_credits": 0, "plan_credits": 0}})
        payload = {
            "business_name": "ZeroCo",
            "industry": "Tech",
            "description": "no credits",
            "tone": "professional",
            "color_scheme": "blue",
        }
        r = s.post(f"{API}/templates/generate", json=payload, timeout=30)
        assert r.status_code == 402, f"Zero-credit should return 402, got {r.status_code} {r.text}"

    def test_list_templates(self):
        ip = _unique_ip("lst")
        s = requests.Session()
        r = s.post(f"{API}/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                   headers={"X-Forwarded-For": ip}, timeout=30)
        assert r.status_code == 200
        r = s.get(f"{API}/templates", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        db.login_attempts.delete_many({"identifier": f"{ip}:{ADMIN_EMAIL}"})


# ---------------- teardown cleanup ----------------
@pytest.fixture(scope="module", autouse=True)
def final_cleanup():
    yield
    # remove any leftover rate_events / login_attempts for admin
    db.login_attempts.delete_many({"identifier": {"$regex": f":{ADMIN_EMAIL}$"}})
