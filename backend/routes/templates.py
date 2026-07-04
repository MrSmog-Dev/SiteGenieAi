import io
import re
import socket
import uuid
import zipfile
import html as html_lib
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pymongo.errors import DuplicateKeyError

from database import db
from models import GenerateInput, EditInput, SlugInput, DomainInput
from security import get_current_user, total_credits, user_is_unlimited, parse_dt
from services.llm import _start_job
from services.og_image import render_og_png
from starlette.concurrency import run_in_threadpool

router = APIRouter()


# ---------------- Generation ----------------
@router.post("/templates/generate")
async def generate_template(input: GenerateInput, user: dict = Depends(get_current_user)):
    return await _start_job(user, input.model_dump(), mode="new")


@router.post("/templates/{template_id}/regenerate")
async def regenerate_template(template_id: str, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    fields = {k: tpl.get(k) for k in ("business_name", "industry", "description", "style",
                                      "primary_color", "contact_email", "phone",
                                      "target_audience", "key_services", "brand_keywords", "pages",
                                      "quality", "model")}
    return await _start_job(user, fields, mode="regenerate", template_id=template_id,
                            free=bool(tpl.get("purchased")))


@router.post("/templates/{template_id}/edit")
async def edit_template(template_id: str, input: EditInput, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return await _start_job(user, {"instructions": input.instructions}, mode="edit", template_id=template_id,
                            free=bool(tpl.get("purchased")))


@router.get("/templates/job/{job_id}")
async def generation_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.gen_jobs.find_one({"job_id": job_id, "user_id": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Safety net: fail jobs orphaned by a restart so the client stops waiting.
    if job["status"] == "pending":
        created = parse_dt(job.get("created_at"))
        if created and (datetime.now(timezone.utc) - created).total_seconds() > 600:
            await db.gen_jobs.update_one({"job_id": job_id},
                {"$set": {"status": "error", "error": "Generation timed out. Please try again."}})
            job["status"], job["error"] = "error", "Generation timed out. Please try again."
    resp = {"status": job["status"], "error": job.get("error")}
    if job["status"] == "done" and job.get("template_id"):
        tpl = await db.templates.find_one({"template_id": job["template_id"]}, {"_id": 0})
        updated = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if tpl:
            resp["template"] = {
                "template_id": tpl["template_id"], "business_name": tpl["business_name"],
                "industry": tpl["industry"], "primary_color": tpl["primary_color"],
                "html": tpl["html"],
            }
            resp["credits_remaining"] = total_credits(updated)
            resp["cost"] = job.get("cost", 0)
            resp["unlimited"] = user_is_unlimited(updated)
    return resp


@router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    docs = await db.templates.find({"user_id": user["user_id"]}, {"_id": 0, "html": 0, "views_daily": 0}).sort("created_at", -1).to_list(200)
    for d in docs:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
    return docs


@router.get("/templates/{template_id}")
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    doc = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    await db.templates.delete_one({"template_id": template_id, "user_id": user["user_id"]})
    return {"success": True}


# ---------------- Publish / hosting ----------------
def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "site").lower().strip()).strip("-")
    return s[:40] or "site"


async def unique_slug(business_name: str) -> str:
    base = slugify(business_name)
    for _ in range(5):
        candidate = f"{base}-{uuid.uuid4().hex[:6]}"
        if not await db.templates.find_one({"slug": candidate}):
            return candidate
    return f"{base}-{uuid.uuid4().hex[:12]}"


@router.post("/templates/{template_id}/publish")
async def publish_template(template_id: str, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    slug = tpl.get("slug") or await unique_slug(tpl.get("business_name", "site"))
    await db.templates.update_one(
        {"template_id": template_id, "user_id": user["user_id"]},
        {"$set": {"published": True, "slug": slug, "published_at": datetime.now(timezone.utc)}})
    return {"published": True, "slug": slug}


@router.post("/templates/{template_id}/unpublish")
async def unpublish_template(template_id: str, user: dict = Depends(get_current_user)):
    res = await db.templates.update_one(
        {"template_id": template_id, "user_id": user["user_id"]},
        {"$set": {"published": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"published": False}


@router.put("/templates/{template_id}/slug")
async def set_slug(template_id: str, input: SlugInput, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    desired = slugify(input.slug)
    if len(desired) < 3:
        raise HTTPException(status_code=400, detail="Link must be at least 3 characters (letters, numbers, hyphens).")
    if desired != tpl.get("slug"):
        clash = await db.templates.find_one({"slug": desired, "template_id": {"$ne": template_id}}, {"_id": 1})
        if clash:
            raise HTTPException(status_code=409, detail="That link is already taken. Try another.")
    try:
        await db.templates.update_one(
            {"template_id": template_id, "user_id": user["user_id"]}, {"$set": {"slug": desired}})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="That link is already taken. Try another.")
    return {"slug": desired}


@router.get("/public/site/{slug}")
async def public_site(slug: str):
    tpl = await db.templates.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Site not found or no longer published")
    return {
        "business_name": tpl.get("business_name", ""),
        "industry": tpl.get("industry", ""),
        "primary_color": tpl.get("primary_color", "#0055FF"),
        "html": tpl.get("html", ""),
    }


# ---------------- Analytics ----------------
_BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegram|discord|slack|"
    r"linkedin|twitterbot|preview|embed|vkshare|pinterest|curl|wget|python-requests|httpx",
    re.IGNORECASE)


def _count_view(request: Request) -> bool:
    return not _BOT_RE.search(request.headers.get("user-agent", ""))


async def _record_view(template_id: str):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.templates.update_one(
        {"template_id": template_id},
        {"$inc": {"views_total": 1, f"views_daily.{today}": 1}})


@router.get("/templates/{template_id}/stats")
async def template_stats(template_id: str, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one(
        {"template_id": template_id, "user_id": user["user_id"]},
        {"_id": 0, "views_total": 1, "views_daily": 1, "published": 1, "slug": 1,
         "custom_domain": 1, "domain_verified": 1})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    daily_map = tpl.get("views_daily") or {}
    now = datetime.now(timezone.utc)
    daily = []
    for i in range(13, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily.append({"date": d, "views": int(daily_map.get(d, 0))})
    return {"views_total": int(tpl.get("views_total", 0)), "daily": daily,
            "published": bool(tpl.get("published")), "slug": tpl.get("slug"),
            "custom_domain": tpl.get("custom_domain"),
            "domain_verified": bool(tpl.get("domain_verified"))}


# ---------------- Custom domains ----------------
_DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def _normalize_domain(raw: str) -> str:
    d = (raw or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    return d.split("/")[0].split("?")[0].split(":")[0].rstrip(".")


def _resolve_ips(host: str) -> set:
    try:
        return {ai[4][0] for ai in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)}
    except OSError:
        return set()


@router.put("/templates/{template_id}/domain")
async def set_domain(template_id: str, input: DomainInput, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0, "published": 1})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if not tpl.get("published"):
        raise HTTPException(status_code=400, detail="Publish your site before connecting a domain.")
    domain = _normalize_domain(input.domain)
    if not _DOMAIN_RE.match(domain):
        raise HTTPException(status_code=400, detail="Enter a valid domain like mybusiness.com or www.mybusiness.com.")
    clash = await db.templates.find_one({"custom_domain": domain, "template_id": {"$ne": template_id}}, {"_id": 1})
    if clash:
        raise HTTPException(status_code=409, detail="That domain is already connected to another site.")
    try:
        await db.templates.update_one(
            {"template_id": template_id, "user_id": user["user_id"]},
            {"$set": {"custom_domain": domain, "domain_verified": False}})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="That domain is already connected to another site.")
    return {"custom_domain": domain, "domain_verified": False}


@router.delete("/templates/{template_id}/domain")
async def remove_domain(template_id: str, user: dict = Depends(get_current_user)):
    res = await db.templates.update_one(
        {"template_id": template_id, "user_id": user["user_id"]},
        {"$unset": {"custom_domain": "", "domain_verified": ""}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"custom_domain": None}


@router.post("/templates/{template_id}/domain/verify")
async def verify_domain(template_id: str, request: Request, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0, "custom_domain": 1})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    domain = tpl.get("custom_domain")
    if not domain:
        raise HTTPException(status_code=400, detail="No domain connected yet.")
    expected_host = _public_base(request).split("://", 1)[1]
    domain_ips, expected_ips = await run_in_threadpool(
        lambda: (_resolve_ips(domain), _resolve_ips(expected_host)))
    verified = bool(domain_ips) and bool(domain_ips & expected_ips)
    await db.templates.update_one({"template_id": template_id}, {"$set": {"domain_verified": verified}})
    return {"custom_domain": domain, "domain_verified": verified, "expected_host": expected_host,
            "domain_ips": sorted(domain_ips), "expected_ips": sorted(expected_ips)}


@router.get("/public/domain/{host}")
async def public_site_by_domain(host: str, request: Request):
    domain = _normalize_domain(host)
    tpl = await db.templates.find_one({"custom_domain": domain, "published": True}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="No published site is connected to this domain")
    if _count_view(request):
        await _record_view(tpl["template_id"])
    return {
        "business_name": tpl.get("business_name", ""),
        "industry": tpl.get("industry", ""),
        "primary_color": tpl.get("primary_color", "#0055FF"),
        "html": tpl.get("html", ""),
    }


# ---------------- SEO-friendly public page (server-rendered HTML w/ social meta) ----------------
_NOT_FOUND_HTML = (
    "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Site not available</title><style>body{margin:0;height:100vh;display:flex;"
    "flex-direction:column;align-items:center;justify-content:center;gap:14px;background:#0b0b0d;"
    "color:#fff;font-family:system-ui,Arial}a{background:#0055FF;color:#fff;padding:12px 22px;"
    "text-decoration:none}</style></head><body><h1>This site isn't available</h1>"
    "<p style='color:#8a8a90'>The link may be wrong or the owner has unpublished it.</p>"
    "<a href='/'>Build your own with SiteGenie</a></body></html>"
)


def _public_base(request: Request) -> str:
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host")
            or request.url.netloc).split(",")[0].strip()
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    return f"{proto}://{host}"


def _inject_social_meta(doc_html: str, *, business_name: str, description: str, industry: str,
                        url: str, image: str) -> str:
    title = html_lib.escape(business_name or "Website")
    raw_desc = (description or f"{business_name} — {industry}").strip()
    desc = html_lib.escape(raw_desc[:200])
    tags = [
        f'<meta name="description" content="{desc}">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{html_lib.escape(url)}">',
        f'<meta property="og:site_name" content="{title}">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{desc}">',
    ]
    if image:
        img = html_lib.escape(image)
        tags += [
            f'<meta property="og:image" content="{img}">',
            f'<meta name="twitter:image" content="{img}">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
    else:
        tags.append('<meta name="twitter:card" content="summary">')
    block = "\n" + "\n".join(tags) + "\n"
    m = re.search(r"<head[^>]*>", doc_html, re.IGNORECASE)
    if m:
        i = m.end()
        return doc_html[:i] + block + doc_html[i:]
    return block + doc_html


@router.get("/p/{slug}")
async def public_page(slug: str, request: Request):
    """Server-rendered public site with social/SEO meta tags (works with link-preview crawlers)."""
    tpl = await db.templates.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not tpl:
        return HTMLResponse(_NOT_FOUND_HTML, status_code=404)
    if _count_view(request):
        await _record_view(tpl["template_id"])
    doc_html = tpl.get("html", "")
    base = _public_base(request)
    out = _inject_social_meta(
        doc_html,
        business_name=tpl.get("business_name", ""),
        description=tpl.get("description", ""),
        industry=tpl.get("industry", ""),
        url=f"{base}/api/p/{slug}",
        image=f"{base}/api/og/{slug}.png",
    )
    # Block generated scripts from calling back to our API (mitigates same-origin abuse).
    return HTMLResponse(out, headers={"Content-Security-Policy": "connect-src 'none'"})


@router.get("/og/{slug}.png")
async def og_card(slug: str):
    """Auto-generated branded 1200x630 social preview card for a published site."""
    tpl = await db.templates.find_one({"slug": slug, "published": True},
                                      {"_id": 0, "business_name": 1, "industry": 1, "primary_color": 1})
    if not tpl:
        raise HTTPException(status_code=404, detail="Not found")
    png = await run_in_threadpool(
        render_og_png, tpl.get("business_name", ""), tpl.get("industry", ""),
        tpl.get("primary_color", "#0055FF"))
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=300"})


@router.get("/templates/{template_id}/download-zip")
async def download_zip(template_id: str, user: dict = Depends(get_current_user)):
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    name = slugify(tpl.get("business_name", "website"))
    readme = (
        f"{tpl.get('business_name','Your website')} — generated by SiteGenie\n"
        f"Industry: {tpl.get('industry','')}\n\n"
        "FILES\n  index.html — your complete website. Open it in any browser or upload it to any host.\n\n"
        "HOSTING\n  This is a single self-contained HTML file. Upload index.html to any static host "
        "(Netlify, Vercel, GitHub Pages, cPanel) or open it directly in a browser. Images load from "
        "hosted URLs and fonts from Google Fonts, so keep an internet connection.\n\n"
        "TIP\n  You can also publish instantly from your SiteGenie dashboard to get a shareable link.\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", tpl.get("html", ""))
        z.writestr("README.txt", readme)
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})
