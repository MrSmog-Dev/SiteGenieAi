"""Backend tests for P2 analytics and P3 custom domain features."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://genie-deploy-1.preview.emergentagent.com").rstrip("/")
EMAIL = "neobeyondlegacy2@gmail.com"
PASSWORD = "SoloLeveling21!"
TEMPLATE_ID = "tpl_908bc5299b9e"
SLUG = "verdant-vine-fa1b20"
APP_HOST = "builder-hub-795.preview.emergentagent.com"

BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
BOT_UA = "Twitterbot/1.0"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


# ---------------- Analytics ----------------
class TestAnalytics:
    def test_public_page_browser_ua_increments_views(self, sess):
        r0 = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/stats", timeout=10)
        assert r0.status_code == 200
        v0 = r0.json()["views_total"]

        r = requests.get(f"{BASE_URL}/api/p/{SLUG}", headers={"User-Agent": BROWSER_UA}, timeout=10)
        assert r.status_code == 200

        r1 = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/stats", timeout=10)
        v1 = r1.json()["views_total"]
        assert v1 == v0 + 1, f"Expected views to increment by 1: {v0} -> {v1}"

    def test_bot_ua_not_counted(self, sess):
        r0 = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/stats", timeout=10)
        v0 = r0.json()["views_total"]

        r = requests.get(f"{BASE_URL}/api/p/{SLUG}", headers={"User-Agent": BOT_UA}, timeout=10)
        assert r.status_code == 200

        r1 = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/stats", timeout=10)
        v1 = r1.json()["views_total"]
        assert v1 == v0, f"Bot UA should not increment views: {v0} -> {v1}"

    def test_stats_shape(self, sess):
        r = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("views_total", "daily", "published", "slug", "custom_domain", "domain_verified"):
            assert k in data, f"missing key: {k}"
        assert isinstance(data["daily"], list) and len(data["daily"]) == 14
        dates = [d["date"] for d in data["daily"]]
        assert dates == sorted(dates), "daily should be oldest -> today"
        assert data["published"] is True
        assert data["slug"] == SLUG

    def test_stats_not_owner_404(self, sess):
        r = sess.get(f"{BASE_URL}/api/templates/tpl_doesnotexist_zzz/stats", timeout=10)
        assert r.status_code == 404


# ---------------- Custom Domain ----------------
class TestCustomDomain:
    def test_set_invalid_domain_400(self, sess):
        r = sess.put(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain",
                     json={"domain": "not a domain!"}, timeout=10)
        assert r.status_code == 400

    def test_set_normalize_verify_true_and_public_serves(self, sess):
        r = sess.put(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain",
                     json={"domain": f"https://{APP_HOST}/some/path?x=1"}, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["custom_domain"] == APP_HOST
        assert data["domain_verified"] is False

        r2 = sess.post(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain/verify", timeout=20)
        assert r2.status_code == 200, r2.text
        vdata = r2.json()
        assert vdata["domain_verified"] is True, f"Expected verified=true, got {vdata}"
        assert isinstance(vdata.get("domain_ips"), list)
        assert isinstance(vdata.get("expected_ips"), list)

        r3 = requests.get(f"{BASE_URL}/api/public/domain/{APP_HOST}",
                          headers={"User-Agent": BROWSER_UA}, timeout=10)
        assert r3.status_code == 200, r3.text
        assert "html" in r3.json()

    def test_duplicate_domain_409(self, sess):
        r = sess.get(f"{BASE_URL}/api/templates", timeout=10)
        assert r.status_code == 200
        others = [t for t in r.json()
                  if t.get("published") and t.get("template_id") != TEMPLATE_ID]
        if not others:
            pytest.skip("No secondary published template to test 409")
        other_id = others[0]["template_id"]
        r2 = sess.put(f"{BASE_URL}/api/templates/{other_id}/domain",
                      json={"domain": APP_HOST}, timeout=10)
        assert r2.status_code == 409, f"Expected 409, got {r2.status_code} {r2.text}"

    def test_remove_domain_and_public_404(self, sess):
        r = sess.delete(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain", timeout=10)
        assert r.status_code == 200
        r2 = requests.get(f"{BASE_URL}/api/public/domain/{APP_HOST}",
                          headers={"User-Agent": BROWSER_UA}, timeout=10)
        assert r2.status_code == 404

    def test_set_domain_on_unpublished_400(self, sess):
        r = sess.get(f"{BASE_URL}/api/templates", timeout=10)
        unpubs = [t for t in r.json() if not t.get("published")]
        if not unpubs:
            pytest.skip("No unpublished template")
        tid = unpubs[0]["template_id"]
        r2 = sess.put(f"{BASE_URL}/api/templates/{tid}/domain",
                      json={"domain": "myrealdomain.com"}, timeout=10)
        assert r2.status_code == 400

    def test_verify_foreign_domain_false(self, sess):
        r = sess.put(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain",
                     json={"domain": "example.com"}, timeout=10)
        assert r.status_code == 200
        try:
            r2 = sess.post(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain/verify", timeout=20)
            assert r2.status_code == 200
            d = r2.json()
            assert d["domain_verified"] is False
            assert isinstance(d.get("domain_ips"), list)
            assert isinstance(d.get("expected_ips"), list)
        finally:
            sess.delete(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/domain", timeout=10)


# ---------------- Regression ----------------
class TestRegression:
    def test_zip_download(self, sess):
        r = sess.get(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/download-zip", timeout=15)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        assert len(r.content) > 100

    def test_slug_rename_same_ok(self, sess):
        r = sess.put(f"{BASE_URL}/api/templates/{TEMPLATE_ID}/slug",
                     json={"slug": SLUG}, timeout=10)
        assert r.status_code == 200
        assert r.json()["slug"] == SLUG
