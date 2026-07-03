import os, uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
import httpx
from pymongo import MongoClient
import html as html_lib

load_dotenv('/app/backend/.env'); load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
mc = MongoClient(os.environ['MONGO_URL']); db = mc[os.environ['DB_NAME']]

def main():
    c = httpx.Client(timeout=30)
    r = c.post(f"{API}/auth/login", json={"email": os.environ['ADMIN_EMAIL'], "password": os.environ['ADMIN_PASSWORD']})
    assert r.status_code == 200, r.text
    hdr = {"Authorization": f"Bearer {r.cookies.get('session_token')}"}
    uid = c.get(f"{API}/auth/me", headers=hdr).json()['user_id']

    tid = f"tpl_{uuid.uuid4().hex[:12]}"
    tid2 = f"tpl_{uuid.uuid4().hex[:12]}"
    hero_img = "https://images.unsplash.com/photo-1500000000000?auto=format&fit=crop&w=1200"
    html = f"<!DOCTYPE html><html><head><title>Meta Co</title></head><body><img src='{hero_img}'><h1>Meta Co</h1></body></html>"
    db.templates.insert_one({"template_id": tid, "user_id": uid, "business_name": "Meta & Co",
                             "industry": "Testing", "description": "We craft delightful widgets for happy people.",
                             "primary_color": "#0055FF", "html": html, "slug": "meta-co-seed",
                             "published": True, "created_at": datetime.now(timezone.utc)})
    db.templates.insert_one({"template_id": tid2, "user_id": uid, "business_name": "Other Co",
                             "industry": "Testing", "html": "<!DOCTYPE html><html><head></head><body>x</body></html>",
                             "slug": "taken-slug", "published": True, "created_at": datetime.now(timezone.utc)})
    pc = httpx.Client(timeout=30)
    try:
        # SEO page returns HTML with meta
        r = pc.get(f"{API}/p/meta-co-seed")
        assert r.status_code == 200, ("p status", r.status_code, r.text[:200])
        assert "text/html" in r.headers.get("content-type", ""), r.headers.get("content-type")
        body = r.text
        assert 'property="og:title" content="Meta &amp; Co"' in body, "og:title missing/unescaped"
        assert 'og:description' in body and 'delightful widgets' in body, "og:description missing"
        assert f'property="og:image" content="{html_lib.escape(hero_img)}"' in body, "og:image (hero) missing"
        assert 'twitter:card" content="summary_large_image"' in body, "twitter large card missing"
        assert r.headers.get("content-security-policy") == "connect-src 'none'", r.headers.get("content-security-policy")
        assert "<h1>Meta Co</h1>" in body, "site body missing"
        print("SEO /p page OK (og:title/desc/image + CSP + body)")

        # unknown slug -> 404 html
        r = pc.get(f"{API}/p/nope-nope")
        assert r.status_code == 404 and "isn't available" in r.text, ("404 page", r.status_code)
        print("SEO 404 page OK")

        # vanity slug: set custom
        r = c.put(f"{API}/templates/{tid}/slug", headers=hdr, json={"slug": "My Cafe! Downtown"})
        assert r.status_code == 200, ("set slug", r.status_code, r.text)
        newslug = r.json()["slug"]
        assert newslug == "my-cafe-downtown", newslug
        print("vanity slug set + slugified ->", newslug)
        assert pc.get(f"{API}/p/{newslug}").status_code == 200
        assert pc.get(f"{API}/p/meta-co-seed").status_code == 404  # old slug retired
        print("new slug live, old slug retired OK")

        # too short
        r = c.put(f"{API}/templates/{tid}/slug", headers=hdr, json={"slug": "ab"})
        assert r.status_code == 400, ("too short", r.status_code)
        print("slug too-short 400 OK")

        # clash with other template's slug
        r = c.put(f"{API}/templates/{tid}/slug", headers=hdr, json={"slug": "taken-slug"})
        assert r.status_code == 409, ("clash", r.status_code, r.text)
        print("slug clash 409 OK")

        # setting to same slug is a no-op success
        r = c.put(f"{API}/templates/{tid}/slug", headers=hdr, json={"slug": newslug})
        assert r.status_code == 200, ("same slug", r.status_code)
        print("same-slug idempotent OK")

        # ownership guard
        r = c.put(f"{API}/templates/tpl_notmine/slug", headers=hdr, json={"slug": "whatever"})
        assert r.status_code == 404
        print("slug ownership guard OK")

        print("\nPHASE 3 TESTS PASSED")
    finally:
        db.templates.delete_many({"template_id": {"$in": [tid, tid2]}})

if __name__ == "__main__":
    main()
