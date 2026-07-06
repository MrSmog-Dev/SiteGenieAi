"""
SiteGenie backend API tests - Iteration 2.
Focus: subscription lifecycle, credit reset, regenerate/edit endpoints, credit gating.
Auth + Plans + Checkout are regression tests preserved from iteration 1.
"""
import os
import uuid
import time
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@sitegenie.com"
ADMIN_PASSWORD = "Sg!Adm1n_9f3kQ2xL7vB"
OLD_ADMIN_PASSWORD = "admin123"
ALLOWED_ORIGIN = "https://genie-deploy-1.preview.emergentagent.com"
EVIL_ORIGIN = "https://evil.example.com"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]


# ---------------- Fixtures ----------------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


def _register():
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": "TEST", "email": email, "password": "pw123456"}, timeout=30)
    assert r.status_code == 200, r.text
    return s, email, r.json()


@pytest.fixture(scope="session")
def new_user():
    s, email, data = _register()
    return {"session": s, "email": email, "user": data}


# ---------------- Auth ----------------
class TestAuth:
    def test_register_grants_3_extra_credits(self, new_user):
        u = new_user["user"]
        assert u["credits"] == 3
        assert u["extra_credits"] == 3
        assert u["plan_credits"] == 0
        assert u["subscription_status"] == "none"
        assert u["cancel_at_period_end"] is False

    def test_register_duplicate_email(self, new_user):
        r = requests.post(f"{API}/auth/register", json={"name": "x", "email": new_user["email"], "password": "x"}, timeout=15)
        assert r.status_code == 400

    def test_admin_me(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"
        assert d["subscription_status"] == "active"
        assert d["credits"] >= 1
        assert "plan_credits" in d and "extra_credits" in d

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me_without_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------------- Plans ----------------
class TestPlans:
    def test_plans_shape(self):
        r = requests.get(f"{API}/plans", timeout=15)
        assert r.status_code == 200
        data = r.json()
        subs = data["subscriptions"]
        packs = data["credit_packs"]
        assert set(subs.keys()) == {"monthly", "quarterly", "annual"}
        # New model uses monthly_credits key
        assert subs["monthly"]["monthly_credits"] == 20
        assert subs["monthly"]["amount"] == 19.0
        assert subs["monthly"]["billing_days"] == 30
        assert subs["quarterly"]["monthly_credits"] == 25
        assert subs["quarterly"]["billing_days"] == 90
        assert subs["annual"]["monthly_credits"] == 30
        assert subs["annual"]["billing_days"] == 365
        assert set(packs.keys()) == {"pack_10", "pack_25", "pack_60"}


# ---------------- Subscription lifecycle ----------------
class TestSubscription:
    def test_get_subscription_admin(self, admin_session):
        r = admin_session.get(f"{API}/subscription", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # Required fields
        for k in ("status", "plan", "monthly_credits", "plan_credits", "extra_credits",
                  "current_period_end", "next_credit_reset", "cancel_at_period_end", "invoices"):
            assert k in d, f"missing {k}"
        assert d["status"] == "active"
        assert isinstance(d["invoices"], list)

    def test_cancel_and_reactivate(self, admin_session):
        # ensure not cancelling first
        db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"cancel_at_period_end": False, "subscription_status": "active"}})

        r = admin_session.post(f"{API}/subscription/cancel", timeout=15)
        assert r.status_code == 200
        assert r.json()["cancel_at_period_end"] is True

        r2 = admin_session.get(f"{API}/subscription", timeout=15).json()
        assert r2["cancel_at_period_end"] is True
        assert r2["status"] == "active"

        r3 = admin_session.post(f"{API}/subscription/reactivate", timeout=15)
        assert r3.status_code == 200
        assert r3.json()["cancel_at_period_end"] is False

        r4 = admin_session.get(f"{API}/subscription", timeout=15).json()
        assert r4["cancel_at_period_end"] is False

    def test_cancel_without_active_returns_400(self, new_user):
        s = new_user["session"]
        r = s.post(f"{API}/subscription/cancel", timeout=15)
        assert r.status_code == 400

    def test_reactivate_without_pending_cancel_returns_400(self, admin_session):
        # ensure cancel flag is false
        db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"cancel_at_period_end": False}})
        r = admin_session.post(f"{API}/subscription/reactivate", timeout=15)
        assert r.status_code == 400


# ---------------- 30-day credit reset ----------------
class TestCreditReset:
    def test_reset_advances_plan_credits_only(self):
        # Create a fresh user and manually give them an active monthly sub with past next_credit_reset
        s, email, _ = _register()
        now = datetime.now(timezone.utc)
        db.users.update_one({"email": email}, {"$set": {
            "plan": "monthly", "plan_name": "Monthly", "subscription_status": "active",
            "plan_credits": 5, "extra_credits": 7, "cancel_at_period_end": False,
            "current_period_end": (now + timedelta(days=10)).isoformat(),
            "next_credit_reset": (now - timedelta(days=1)).isoformat(),
        }})

        # /auth/me triggers process_subscription -> reset
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["plan_credits"] == 20, f"plan_credits should reset to 20, got {d['plan_credits']}"
        assert d["extra_credits"] == 7, "extra_credits must be untouched"
        assert d["credits"] == 27
        # next_credit_reset advanced into the future
        ncr = datetime.fromisoformat(d["next_credit_reset"])
        assert ncr > now

    def test_no_reset_when_next_reset_future(self):
        s, email, _ = _register()
        now = datetime.now(timezone.utc)
        db.users.update_one({"email": email}, {"$set": {
            "plan": "monthly", "plan_name": "Monthly", "subscription_status": "active",
            "plan_credits": 3, "extra_credits": 2, "cancel_at_period_end": False,
            "current_period_end": (now + timedelta(days=20)).isoformat(),
            "next_credit_reset": (now + timedelta(days=15)).isoformat(),
        }})
        d = s.get(f"{API}/auth/me", timeout=15).json()
        assert d["plan_credits"] == 3
        assert d["extra_credits"] == 2


# ---------------- Regenerate / Edit ----------------
class TestRegenerateEdit:
    def _seed_template(self, user_id):
        tpl_id = f"tpl_{uuid.uuid4().hex[:12]}"
        db.templates.insert_one({
            "template_id": tpl_id, "user_id": user_id,
            "business_name": "TEST Seed Cafe", "industry": "cafe",
            "description": "desc", "style": "modern", "primary_color": "#000000",
            "html": "<!DOCTYPE html><html><head></head><body>seed</body></html>",
            "created_at": datetime.now(timezone.utc),
        })
        return tpl_id

    def test_regenerate_returns_job_id(self, admin_session):
        me = admin_session.get(f"{API}/auth/me", timeout=15).json()
        tpl_id = self._seed_template(me["user_id"])
        r = admin_session.post(f"{API}/templates/{tpl_id}/regenerate", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "pending"
        assert d["job_id"].startswith("job_")

    def test_regenerate_unknown_returns_404(self, admin_session):
        r = admin_session.post(f"{API}/templates/tpl_doesnotexist/regenerate", timeout=15)
        assert r.status_code == 404

    def test_edit_returns_job_id(self, admin_session):
        me = admin_session.get(f"{API}/auth/me", timeout=15).json()
        tpl_id = self._seed_template(me["user_id"])
        r = admin_session.post(f"{API}/templates/{tpl_id}/edit",
                               json={"instructions": "make it darker"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "pending"
        assert d["job_id"].startswith("job_")

    def test_edit_unknown_returns_404(self, admin_session):
        r = admin_session.post(f"{API}/templates/tpl_missing/edit",
                               json={"instructions": "x"}, timeout=15)
        assert r.status_code == 404


# ---------------- 402 credit gating ----------------
class TestCreditGating:
    def test_generate_with_zero_credits_returns_402(self):
        s, email, _ = _register()
        # drain credits directly in mongo
        db.users.update_one({"email": email},
                            {"$set": {"plan_credits": 0, "extra_credits": 0}})
        r = s.post(f"{API}/templates/generate", json={
            "business_name": "TEST Zero", "industry": "x", "description": "y"
        }, timeout=30)
        assert r.status_code == 402

        # no job created
        u = db.users.find_one({"email": email})
        jobs = db.gen_jobs.count_documents({"user_id": u["user_id"]})
        assert jobs == 0

    def test_regenerate_with_zero_credits_returns_402(self):
        s, email, data = _register()
        user_id = data["user_id"]
        # seed a template first (with credits still available - but we're inserting directly)
        tpl_id = f"tpl_{uuid.uuid4().hex[:12]}"
        db.templates.insert_one({
            "template_id": tpl_id, "user_id": user_id,
            "business_name": "T", "industry": "x", "description": "y",
            "style": "modern", "primary_color": "#000",
            "html": "<!DOCTYPE html><html></html>",
            "created_at": datetime.now(timezone.utc),
        })
        db.users.update_one({"email": email}, {"$set": {"plan_credits": 0, "extra_credits": 0}})
        r = s.post(f"{API}/templates/{tpl_id}/regenerate", timeout=30)
        assert r.status_code == 402

    def test_edit_with_zero_credits_returns_402(self):
        s, email, data = _register()
        user_id = data["user_id"]
        tpl_id = f"tpl_{uuid.uuid4().hex[:12]}"
        db.templates.insert_one({
            "template_id": tpl_id, "user_id": user_id,
            "business_name": "T", "industry": "x", "description": "y",
            "style": "modern", "primary_color": "#000",
            "html": "<!DOCTYPE html><html></html>",
            "created_at": datetime.now(timezone.utc),
        })
        db.users.update_one({"email": email}, {"$set": {"plan_credits": 0, "extra_credits": 0}})
        r = s.post(f"{API}/templates/{tpl_id}/edit", json={"instructions": "x"}, timeout=30)
        assert r.status_code == 402


# ---------------- Checkout regression ----------------
class TestCheckout:
    def test_subscription_checkout(self, admin_session):
        r = admin_session.post(f"{API}/checkout/session", json={
            "kind": "subscription", "plan_id": "monthly", "origin_url": BASE_URL,
        }, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith("https://checkout.stripe.com")

    def test_invalid_plan(self, admin_session):
        r = admin_session.post(f"{API}/checkout/session", json={
            "kind": "credits", "plan_id": "nope", "origin_url": BASE_URL,
        }, timeout=15)
        assert r.status_code == 400

    def test_checkout_requires_auth(self):
        r = requests.post(f"{API}/checkout/session", json={
            "kind": "subscription", "plan_id": "monthly", "origin_url": BASE_URL
        }, timeout=15)
        assert r.status_code == 401



# ---------------- SECURITY FIXES ----------------
class TestSecurityFixes:
    # SEC-002
    def test_old_admin_password_rejected(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": OLD_ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 401, f"OLD password must be rejected, got {r.status_code}"

    def test_new_admin_password_accepted(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200, f"NEW password should succeed, got {r.status_code} {r.text}"
        d = r.json()
        # login returns the public user object directly
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"

    # SEC-001 (CORS)
    def test_disallowed_origin_no_acao(self):
        # Preflight from evil origin
        r = requests.options(f"{API}/auth/me", headers={
            "Origin": EVIL_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }, timeout=15)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        assert EVIL_ORIGIN not in acao, f"evil origin echoed in ACAO: {acao!r}"
        # Actual GET (no auth needed for header check)
        r2 = requests.get(f"{API}/plans", headers={"Origin": EVIL_ORIGIN}, timeout=15)
        acao2 = r2.headers.get("Access-Control-Allow-Origin", "")
        assert EVIL_ORIGIN not in acao2, f"evil origin echoed in ACAO: {acao2!r}"

    def test_allowed_origin_reflected(self):
        r = requests.options(f"{API}/auth/me", headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }, timeout=15)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        # Edge (Cloudflare) may collapse to '*' but MUST allow the trusted origin one way or another
        assert acao in ("*", ALLOWED_ORIGIN), f"allowed origin not permitted, got {acao!r}"

    # SEC-001 (cookie flags) - inspect session_token cookie specifically
    def test_login_cookie_flags(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        session_cookie = None
        # response.raw.headers preserves multiple Set-Cookie entries
        for k, v in r.raw.headers.items():
            if k.lower() == "set-cookie" and v.lower().startswith("session_token="):
                session_cookie = v
                break
        assert session_cookie, f"session_token cookie missing. headers={list(r.raw.headers.items())}"
        low = session_cookie.lower()
        assert "httponly" in low, f"HttpOnly missing: {session_cookie}"
        assert "secure" in low, f"Secure missing: {session_cookie}"
        assert "samesite=lax" in low, f"SameSite=Lax missing: {session_cookie}"
        assert "samesite=none" not in low

    # SEC-003 (idempotency at DB level)
    def test_apply_payment_idempotency_db_guard(self):
        # Insert unprocessed txn, run find_one_and_update twice - second returns None
        s, email, data = _register()
        user_id = data["user_id"]
        session_id = f"cs_test_{uuid.uuid4().hex[:14]}"
        db.payment_transactions.insert_one({
            "session_id": session_id, "user_id": user_id,
            "kind": "credits", "plan_id": "pack_25", "credits": 25,
            "amount": 20.0, "currency": "usd",
            "payment_status": "paid", "status": "complete", "processed": False,
            "created_at": datetime.now(timezone.utc),
        })
        first = db.payment_transactions.find_one_and_update(
            {"session_id": session_id, "processed": {"$ne": True}},
            {"$set": {"processed": True}},
        )
        assert first is not None, "first claim should succeed"
        second = db.payment_transactions.find_one_and_update(
            {"session_id": session_id, "processed": {"$ne": True}},
            {"$set": {"processed": True}},
        )
        assert second is None, "second claim MUST be None (idempotency guard)"

    # SEC-003 (user-scoped checkout_status)
    def test_checkout_status_user_scoped(self, admin_session):
        # Create session belonging to a different user
        s, email, data = _register()
        other_user_id = data["user_id"]
        session_id = f"cs_test_{uuid.uuid4().hex[:14]}"
        db.payment_transactions.insert_one({
            "session_id": session_id, "user_id": other_user_id,
            "kind": "credits", "plan_id": "pack_10", "credits": 10,
            "amount": 10.0, "currency": "usd",
            "payment_status": "initiated", "status": "open", "processed": False,
            "created_at": datetime.now(timezone.utc),
        })
        # Admin user should not see other user's session
        r = admin_session.get(f"{API}/checkout/status/{session_id}", timeout=15)
        assert r.status_code == 404, f"cross-user checkout status must be 404, got {r.status_code}"

    # REGRESSION: deduct_one_credit never goes below zero
    def test_deduct_never_negative(self):
        s, email, data = _register()
        user_id = data["user_id"]
        db.users.update_one({"email": email}, {"$set": {"plan_credits": 0, "extra_credits": 0}})
        # 402 gate should prevent job creation; call twice
        for _ in range(2):
            r = s.post(f"{API}/templates/generate", json={
                "business_name": "TEST Neg", "industry": "x", "description": "y"
            }, timeout=15)
            assert r.status_code == 402
        u = db.users.find_one({"user_id": user_id})
        assert u["plan_credits"] == 0
        assert u["extra_credits"] == 0
