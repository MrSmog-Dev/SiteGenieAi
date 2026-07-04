from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from database import db
from services.blog import render_index, render_post, render_sitemap

router = APIRouter()


def _host(request: Request) -> str:
    return request.headers.get("x-forwarded-host") or request.url.netloc


@router.get("/blog")
async def blog_index(request: Request):
    posts = await db.blog_posts.find({}, {"_id": 0, "body": 0}).sort("created_at", -1).to_list(100)
    return HTMLResponse(render_index(posts, _host(request)))


@router.get("/blog/sitemap.xml")
async def blog_sitemap(request: Request):
    posts = await db.blog_posts.find({}, {"_id": 0, "slug": 1, "created_at": 1}).sort(
        "created_at", -1).to_list(500)
    return Response(render_sitemap(posts, _host(request)), media_type="application/xml")


@router.get("/blog/img/{image_id}")
async def blog_image(image_id: str):
    doc = await db.blog_images.find_one({"image_id": image_id})
    if not doc:
        return Response(status_code=404)
    return Response(bytes(doc["data"]), media_type=doc.get("content_type") or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.get("/blog/{slug}")
async def blog_post(slug: str, request: Request):
    post = await db.blog_posts.find_one({"slug": slug}, {"_id": 0})
    if not post:
        return HTMLResponse("<h1>Article not found</h1>", status_code=404)
    related = await db.blog_posts.find({"slug": {"$ne": slug}}, {"_id": 0, "title": 1, "slug": 1}).sort(
        "created_at", -1).to_list(3)
    return HTMLResponse(render_post(post, related, _host(request)))
