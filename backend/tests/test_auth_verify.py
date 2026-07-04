"""Auth verification tests for preview env (SiteGenie iter 15)."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://builder-hub-795.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "neobeyondlegacy2@gmail.com"
OWNER_PASSWORD = "SoloLeveling21!"


@pytest.fixture
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_health_plans_no_db_dependency_ok(client):
    r = client.get(f"{BASE_URL}/api/plans", timeout=15)
    assert r.status_code == 200


def test_login_owner_success_sets_cookie(client):
    r = client.post(f"{BASE_URL}/api/auth/login",
                    json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    # httpOnly session cookie should be set
    assert "session_token" in client.cookies, f"no session_token cookie set; cookies={client.cookies.get_dict()}"
    data = r.json()
    # Response body may/may not include token; email should be present in user info at least via /me
    me = client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me.status_code == 200, f"/me failed: {me.status_code} {me.text}"
    user = me.json()
    assert user.get("email") == OWNER_EMAIL
    assert user.get("role") == "owner"


def test_wrong_password_returns_401(client):
    email = f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"
    # Use random unknown user to avoid rate limiting owner account
    r = client.post(f"{BASE_URL}/api/auth/login",
                    json={"email": email, "password": "totallyWrong!"}, timeout=15)
    # Expect 401 (or 429 if rate-limited — treat as acceptable per instructions)
    assert r.status_code in (401, 429), f"expected 401/429, got {r.status_code}: {r.text}"
    assert r.status_code != 500


def test_register_login_logout_flow(client):
    uniq = uuid.uuid4().hex[:10]
    email = f"testuser_{uniq}@example.com"
    password = "TestPass123!"
    name = f"Test {uniq}"

    # Register
    r = client.post(f"{BASE_URL}/api/auth/register",
                    json={"name": name, "email": email, "password": password}, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    assert "session_token" in client.cookies, "register should set session cookie"

    # /me works after register
    me = client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me.status_code == 200
    assert me.json().get("email") == email

    # Logout
    lo = client.post(f"{BASE_URL}/api/auth/logout", timeout=15)
    assert lo.status_code in (200, 204), f"logout failed: {lo.status_code} {lo.text}"

    # After logout, /me should be unauthorized
    me2 = client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me2.status_code in (401, 403), f"/me still authorized after logout: {me2.status_code}"

    # Login with same account
    li = client.post(f"{BASE_URL}/api/auth/login",
                     json={"email": email, "password": password}, timeout=20)
    assert li.status_code == 200, f"relogin failed: {li.status_code} {li.text}"
    assert "session_token" in client.cookies

    me3 = client.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me3.status_code == 200
    assert me3.json().get("email") == email


def test_session_persistence_across_new_client(client):
    # login
    r = client.post(f"{BASE_URL}/api/auth/login",
                    json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=20)
    assert r.status_code == 200
    cookie = client.cookies.get("session_token")
    assert cookie, "session_token cookie missing"

    # simulate reload: new session, reuse cookie
    s2 = requests.Session()
    s2.cookies.set("session_token", cookie)
    me = s2.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me.status_code == 200
    assert me.json().get("email") == OWNER_EMAIL
