"""
Backend tests for Premium Upgrade bug-fix verification.
- Owner login
- 409 when re-upgrading already-premium template
- Premium templates listed on Market are priced higher (Professional/Premium tier)
- End-to-end upgrade job: HTML grows meaningfully, quality flips to 'premium',
  and rendered site contains new interactive sections (gallery/lightbox/faq/accordion).
- Regression: regenerate & edit endpoints still respond correctly.
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    "https://genie-deploy-1.preview.emergentagent.com"
OWNER_EMAIL = "neobeyondlegacy2@gmail.com"
OWNER_PASSWORD = "SoloLeveling21!"
PREMIUM_TPL = "tpl_908bc5299b9e"           # already premium
NON_PREMIUM_TPL = "tpl_29decf25c01f"       # First Growth Capital (non-premium)
POLL_TIMEOUT_S = 360                       # 6 min


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("role") == "owner"
    assert data.get("unlimited") is True
    return s


# ---------------- Auth ----------------
def test_owner_login_and_me(client):
    r = client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    d = r.json()
    assert d["email"] == OWNER_EMAIL
    assert d["role"] == "owner"


# ---------------- Idempotent 409 ----------------
def test_upgrade_already_premium_returns_409(client):
    tpl = client.get(f"{BASE_URL}/api/templates/{PREMIUM_TPL}").json()
    assert tpl.get("quality") == "premium", "Expected tpl_908bc5299b9e to already be premium"
    r = client.post(f"{BASE_URL}/api/templates/{PREMIUM_TPL}/upgrade")
    assert r.status_code == 409, f"Expected 409 for re-upgrade, got {r.status_code}: {r.text}"
    assert "premium" in r.json().get("detail", "").lower()


# ---------------- Premium pricing check ----------------
def test_premium_template_priced_high_on_market(client):
    listings = client.get(f"{BASE_URL}/api/market").json()
    listings = listings if isinstance(listings, list) else listings.get("listings", [])
    match = next((l for l in listings if l.get("source_template_id") == PREMIUM_TPL), None)
    assert match is not None, "Premium template not listed on market"
    price = float(match["price_usd"])
    tier = match.get("tier")
    assert price >= 350, f"Premium template priced too low: ${price} (expected >=350)"
    assert tier in ("Professional", "Premium"), f"Unexpected tier: {tier}"


# ---------------- End-to-end upgrade ----------------
@pytest.mark.slow
def test_upgrade_grows_html_and_adds_interactive_sections(client):
    # Snapshot before
    before = client.get(f"{BASE_URL}/api/templates/{NON_PREMIUM_TPL}").json()
    if (before.get("quality") or "") == "premium":
        pytest.skip("Template is already premium — cannot test upgrade growth here.")
    before_len = len(before.get("html", "") or "")
    assert before_len > 0

    # Start job
    r = client.post(f"{BASE_URL}/api/templates/{NON_PREMIUM_TPL}/upgrade")
    assert r.status_code == 200, f"Upgrade start failed: {r.status_code} {r.text}"
    job_id = r.json()["job_id"]

    # Poll until done
    deadline = time.time() + POLL_TIMEOUT_S
    status = "pending"
    last = {}
    while time.time() < deadline:
        j = client.get(f"{BASE_URL}/api/templates/job/{job_id}").json()
        last = j
        status = j.get("status")
        if status in ("done", "error"):
            break
        time.sleep(6)

    assert status == "done", f"Upgrade job did not complete cleanly: {last}"

    after = client.get(f"{BASE_URL}/api/templates/{NON_PREMIUM_TPL}").json()
    after_len = len(after.get("html", "") or "")
    assert after.get("quality") == "premium", f"quality not flipped to premium: {after.get('quality')}"
    # Meaningful growth (>=15% and at least +5KB)
    growth = after_len - before_len
    assert growth >= 5000 and after_len >= int(before_len * 1.15), \
        f"HTML did not grow meaningfully: {before_len} -> {after_len} (+{growth})"

    html_lower = after.get("html", "").lower()
    # Look for new interactive keywords the upgrade injects
    signals = ["lightbox", "gallery", "faq", "accordion", "@keyframes", "addeventlistener"]
    hits = [s for s in signals if s in html_lower]
    assert len(hits) >= 3, f"Expected new interactive signals, only found: {hits}"

    # Idempotent 409 now
    r2 = client.post(f"{BASE_URL}/api/templates/{NON_PREMIUM_TPL}/upgrade")
    assert r2.status_code == 409


# ---------------- Regression: regenerate & edit still work ----------------
def test_regenerate_endpoint_still_starts_job(client):
    # Use the already-premium template (owner => free), just verify it queues a job
    r = client.post(f"{BASE_URL}/api/templates/{PREMIUM_TPL}/regenerate")
    assert r.status_code == 200, f"Regenerate returned {r.status_code}: {r.text}"
    body = r.json()
    assert "job_id" in body and body.get("status") == "pending"


def test_edit_endpoint_still_starts_job(client):
    r = client.post(f"{BASE_URL}/api/templates/{PREMIUM_TPL}/edit",
                    json={"instructions": "Change the hero headline color to a slightly warmer green."})
    assert r.status_code == 200, f"Edit returned {r.status_code}: {r.text}"
    body = r.json()
    assert "job_id" in body and body.get("status") == "pending"
