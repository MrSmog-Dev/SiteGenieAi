"""Iteration 13 tests — market price override + generator model/quality."""
import os
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

OWNER = {"email": "neobeyondlegacy2@gmail.com", "password": "SoloLeveling21!"}
ADMIN = {"email": "admin@sitegenie.com", "password": "Sg!Adm1n_9f3kQ2xL7vB"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def owner():
    return _login(OWNER)


@pytest.fixture(scope="session")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="session")
def anon():
    return requests.Session()


def test_market_listings_public(anon):
    r = anon.get(f"{API}/market", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    flagships = [d for d in data if d.get("tier") == "Premium" or float(d.get("price_usd", 0)) >= 400]
    assert len(flagships) >= 1, "no flagship listing found"
    print(f"Total listings: {len(data)}; flagships: {len(flagships)}")


def test_market_owned(owner):
    r = owner.get(f"{API}/market/owned", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_price_override_unauth(anon):
    mid = anon.get(f"{API}/market", timeout=30).json()[0]["market_id"]
    r = requests.put(f"{API}/market/{mid}/price", json={"price_usd": 100}, timeout=30)
    assert r.status_code in (401, 403), f"got {r.status_code}: {r.text}"


def test_price_override_non_owner(admin, anon):
    mid = anon.get(f"{API}/market", timeout=30).json()[0]["market_id"]
    r = admin.put(f"{API}/market/{mid}/price", json={"price_usd": 100}, timeout=30)
    assert r.status_code == 403, f"got {r.status_code}: {r.text}"


def test_price_override_owner_success(owner, anon):
    listings = anon.get(f"{API}/market", timeout=30).json()
    target = listings[0]
    mid = target["market_id"]
    original_price = float(target["price_usd"])
    new_price = 333.0 if original_price != 333.0 else 444.0
    r = owner.put(f"{API}/market/{mid}/price", json={"price_usd": new_price}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["price_usd"]) == new_price
    assert body.get("priced_by") == "owner_override"
    fresh = anon.get(f"{API}/market", timeout=30).json()
    updated = next((x for x in fresh if x["market_id"] == mid), None)
    assert updated and float(updated["price_usd"]) == new_price
    # restore
    owner.put(f"{API}/market/{mid}/price", json={"price_usd": original_price}, timeout=30)


def test_price_override_invalid(owner, anon):
    mid = anon.get(f"{API}/market", timeout=30).json()[0]["market_id"]
    r = owner.put(f"{API}/market/{mid}/price", json={"price_usd": -5}, timeout=30)
    assert r.status_code == 400
    r2 = owner.put(f"{API}/market/{mid}/price", json={"price_usd": 200000}, timeout=30)
    assert r2.status_code == 400


def test_price_override_unknown(owner):
    r = owner.put(f"{API}/market/nonexistent-market-id-xyz/price",
                  json={"price_usd": 100}, timeout=30)
    assert r.status_code == 404


def test_market_preview(anon):
    mid = anon.get(f"{API}/market", timeout=30).json()[0]["market_id"]
    r = anon.get(f"{API}/market/{mid}/preview", timeout=30)
    assert r.status_code == 200
    assert "<" in r.text


def test_generate_haiku_economy(owner):
    """Verify /templates/generate accepts model + quality=economy, completes."""
    payload = {
        "business_name": "TEST_HaikuEcon Co",
        "industry": "coffee shop",
        "description": "A cozy test coffee shop for haiku economy regression.",
        "quality": "economy",
        "model": "claude-haiku-4-5",
        "brand_keywords": "cozy warm",
        "style": "modern",
    }
    r = owner.post(f"{API}/templates/generate", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    deadline = time.time() + 180
    final = None
    while time.time() < deadline:
        jr = owner.get(f"{API}/templates/job/{job_id}", timeout=30)
        assert jr.status_code == 200
        j = jr.json()
        if j.get("status") in ("done", "error"):
            final = j
            break
        time.sleep(3)
    assert final is not None, "job did not complete in time"
    assert final["status"] == "done", f"job errored: {final}"
    tpl = final.get("template") or {}
    assert tpl.get("template_id")
    model_str = str(tpl.get("model") or tpl.get("build_model") or tpl.get("meta") or "").lower()
    if "haiku" not in model_str:
        # non-fatal - just print
        print(f"WARN: model field may not be persisted. tpl keys: {list(tpl.keys())}")
