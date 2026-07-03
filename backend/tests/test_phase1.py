import os, uuid, io, zipfile
from datetime import datetime, timezone
from dotenv import load_dotenv
import httpx
from pymongo import MongoClient

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
    html = "<!DOCTYPE html><html><head><title>Zip Co</title></head><body><h1>Zip Co</h1></body></html>"
    db.templates.insert_one({"template_id": tid, "user_id": uid, "business_name": "Zip Test Co",
                             "industry": "Testing", "primary_color": "#0055FF", "html": html,
                             "created_at": datetime.now(timezone.utc)})
    try:
        # ZIP download
        r = c.get(f"{API}/templates/{tid}/download-zip", headers=hdr)
        assert r.status_code == 200, ("zip status", r.status_code, r.text[:200])
        assert r.headers.get("content-type") == "application/zip", r.headers
        assert "zip-test-co.zip" in r.headers.get("content-disposition", ""), r.headers.get("content-disposition")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "index.html" in names and "README.txt" in names, names
        assert zf.read("index.html").decode() == html
        print("ZIP export OK ->", names)

        # ownership guard on zip
        r = c.get(f"{API}/templates/tpl_notmine/download-zip", headers=hdr)
        assert r.status_code == 404
        print("ZIP ownership guard OK")

        # economy mode accepted -> returns job_id
        payload = {"business_name": "Econ Co", "industry": "Cafe", "description": "A cozy cafe.", "quality": "economy"}
        r = c.post(f"{API}/templates/generate", headers=hdr, json=payload)
        assert r.status_code == 200 and r.json().get("job_id"), ("economy generate", r.status_code, r.text)
        print("economy generate accepted -> job", r.json()["job_id"])

        # quality default still accepted
        r = c.post(f"{API}/templates/generate", headers=hdr, json={"business_name": "Q Co", "industry": "Gym", "description": "A gym."})
        assert r.status_code == 200 and r.json().get("job_id")
        print("quality (default) generate accepted -> job", r.json()["job_id"])

        print("\nPHASE 1 BACKEND TESTS PASSED")
    finally:
        db.templates.delete_one({"template_id": tid})
        db.gen_jobs.delete_many({"user_id": uid, "template_id": None})

if __name__ == "__main__":
    main()
