import os, uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
import httpx
from pymongo import MongoClient

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
mc = MongoClient(os.environ['MONGO_URL'])
db = mc[os.environ['DB_NAME']]

ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']

def main():
    c = httpx.Client(timeout=30)
    # login
    r = c.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, ("login", r.status_code, r.text)
    token = r.cookies.get('session_token')
    hdr = {"Authorization": f"Bearer {token}"}
    me = c.get(f"{API}/auth/me", headers=hdr).json()
    uid = me['user_id']
    print("logged in as", uid)

    # seed a template directly (skip LLM)
    tid = f"tpl_{uuid.uuid4().hex[:12]}"
    html = "<!DOCTYPE html><html><head><title>Test Co</title></head><body><h1>Hello Test Co</h1></body></html>"
    db.templates.insert_one({
        "template_id": tid, "user_id": uid, "business_name": "Test Publish Co",
        "industry": "Testing", "primary_color": "#0055FF", "html": html,
        "created_at": datetime.now(timezone.utc),
    })
    try:
        # publish
        r = c.post(f"{API}/templates/{tid}/publish", headers=hdr)
        assert r.status_code == 200, ("publish", r.status_code, r.text)
        slug = r.json()['slug']
        assert r.json()['published'] is True
        print("published slug:", slug)

        # public GET (no auth)
        pc = httpx.Client(timeout=30)
        r = pc.get(f"{API}/public/site/{slug}")
        assert r.status_code == 200, ("public get", r.status_code, r.text)
        assert r.json()['html'] == html, "html mismatch"
        assert r.json()['business_name'] == "Test Publish Co"
        print("public fetch OK, html len:", len(r.json()['html']))

        # publish again -> same slug (idempotent)
        r2 = c.post(f"{API}/templates/{tid}/publish", headers=hdr)
        assert r2.json()['slug'] == slug, "slug should be stable"
        print("re-publish keeps slug OK")

        # unpublish
        r = c.post(f"{API}/templates/{tid}/unpublish", headers=hdr)
        assert r.status_code == 200 and r.json()['published'] is False, ("unpublish", r.text)
        r = pc.get(f"{API}/public/site/{slug}")
        assert r.status_code == 404, ("public after unpublish should 404", r.status_code)
        print("unpublish -> public 404 OK")

        # unknown slug -> 404
        r = pc.get(f"{API}/public/site/does-not-exist-xyz")
        assert r.status_code == 404
        print("unknown slug 404 OK")

        # publish someone else's template -> 404 (ownership)
        r = c.post(f"{API}/templates/tpl_notmine123/publish", headers=hdr)
        assert r.status_code == 404
        print("ownership guard OK")

        print("\nALL PUBLISH TESTS PASSED")
    finally:
        db.templates.delete_one({"template_id": tid})

if __name__ == "__main__":
    main()
