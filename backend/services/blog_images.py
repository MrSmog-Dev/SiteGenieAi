import asyncio
import base64
import re
import uuid

import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, logger
from database import db

IMAGE_MODEL = "gemini-3.1-flash-image-preview"


async def _store_image(data: bytes, content_type: str, credit: str) -> str:
    image_id = f"img_{uuid.uuid4().hex[:12]}"
    await db.blog_images.insert_one({"image_id": image_id, "data": data,
                                     "content_type": content_type, "credit": credit})
    return image_id


async def _openverse_search(query: str) -> dict | None:
    """Free-to-use stock photos (CC-licensed) via Openverse, no API key."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.openverse.org/v1/images/",
                                 params={"q": query[:200], "license_type": "commercial",
                                         "page_size": 5, "aspect_ratio": "wide"},
                                 headers={"User-Agent": "SiteGenieBlog/1.0"})
        if r.status_code != 200:
            return None
        for res in r.json().get("results", []):
            url = res.get("url")
            if not url:
                continue
            try:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    img = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                ct = (img.headers.get("content-type") or "").split(";")[0]
                if img.status_code == 200 and ct.startswith("image/") and 5_000 < len(img.content) < 8_000_000:
                    creator = res.get("creator") or "Unknown"
                    lic = (res.get("license") or "cc").upper()
                    return {"data": img.content, "content_type": ct,
                            "credit": f"Photo: {creator} ({lic}) via Openverse"}
            except Exception:
                continue
    except Exception:
        logger.exception("openverse search failed")
    return None


async def _generate_image(prompt: str) -> dict | None:
    """AI-generated illustration via Gemini Nano Banana (Emergent LLM key)."""
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"blogimg_{uuid.uuid4().hex[:8]}",
                       system_message="You are an image generator.")
        chat.with_model("gemini", IMAGE_MODEL).with_params(modalities=["image", "text"])
        text, images = await asyncio.wait_for(
            chat.send_message_multimodal_response(UserMessage(
                text=("Create a clean, modern, editorial blog illustration in wide 16:9 format: "
                      f"{prompt}. Professional and engaging, soft lighting, no text overlays."))),
            timeout=120)
        if images:
            return {"data": base64.b64decode(images[0]["data"]),
                    "content_type": images[0].get("mime_type") or "image/png",
                    "credit": "Illustration by SiteGenie AI"}
    except Exception:
        logger.exception("blog image generation failed")
    return None


def _figure(image_id: str, alt: str, credit: str) -> str:
    return (f'<figure style="margin:32px 0"><img src="/api/blog/img/{image_id}" alt="{alt}" '
            'style="width:100%;height:auto;display:block" loading="lazy">'
            f'<figcaption style="color:rgba(255,255,255,.35);font-size:12px;'
            f'font-family:Arial,sans-serif;margin-top:8px">{credit}</figcaption></figure>')


async def resolve_article_images(body: str) -> str:
    """Replaces [IMAGE: description] markers with stored images (free stock first, AI fallback)."""
    matches = list(re.finditer(r"\[IMAGE:\s*([^\]]{3,200})\]", body))[:3]
    for m in matches:
        desc = m.group(1).strip()
        img = await _openverse_search(desc) or await _generate_image(desc)
        fig = ""
        if img:
            image_id = await _store_image(img["data"], img["content_type"], img["credit"])
            fig = _figure(image_id, desc[:110].replace('"', "'"), img["credit"])
        body = body.replace(m.group(0), fig, 1)
    return re.sub(r"\[IMAGE:[^\]]*\]", "", body)
