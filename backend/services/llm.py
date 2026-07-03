import uuid
import re
import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage

from database import db
from config import (
    EMERGENT_LLM_KEY, STRATEGY_MODEL, BUILD_MODEL,
    GEN_MAX_PER_WINDOW, GEN_WINDOW_SECONDS, logger,
)
from security import (
    estimate_cost, deduct_credits, user_is_unlimited, is_owner,
    total_credits, check_rate_limit,
)

GEN_STRATEGY_SYSTEM = (
    "You are a senior brand & web strategist and conversion copywriter with 15+ years building "
    "high-performing small-business websites. A client has described their business. Think deeply, "
    "like a real consultant, and produce a rich CREATIVE BRIEF for a single-page marketing website. "
    "Do NOT write HTML. Write specific, on-brand, ready-to-use content — never placeholders or lorem ipsum. "
    "Structure the brief in clear markdown with these parts:\n"
    "1. POSITIONING: a one-line positioning statement + the core value proposition.\n"
    "2. AUDIENCE: who the ideal customer is, their pains and desires.\n"
    "3. VOICE & TONE: how the copy should sound.\n"
    "4. UNIQUE SELLING POINTS: 3-5 concrete differentiators.\n"
    "5. SECTION-BY-SECTION PLAN — write the ACTUAL final copy for each: "
    "Hero (headline + subheadline + primary CTA), Services/Offerings (name + 1-2 line benefit-led "
    "description for 3-6 items), About (a compelling short story), Testimonials (invent 3 realistic, "
    "specific quotes with believable customer names and roles), FAQ (5 real questions with helpful answers), "
    "Contact/CTA (headline + supporting line + what the form asks).\n"
    "6. DESIGN DIRECTION: a cohesive color palette (hex values, anchored to the brand color), a Google-Fonts "
    "pairing (heading + body), imagery/visual style, and the overall mood.\n"
    "Be concrete and specific to THIS business. Quality and depth over brevity."
)

GEN_BUILD_SYSTEM = (
    "You are an award-winning web designer and front-end engineer. Using the provided CREATIVE BRIEF, "
    "output a SINGLE complete, production-ready, fully responsive HTML5 website. Rules:\n"
    "1) Return ONLY raw HTML starting with <!DOCTYPE html>. No markdown, no code fences, no commentary.\n"
    "2) All CSS in ONE <style> tag in <head>. Vanilla only (no external CSS frameworks). A small amount of "
    "vanilla JS is allowed for a mobile nav toggle, smooth scroll, and FAQ accordion.\n"
    "3) REQUIRED sections, in order: sticky nav, Hero (with primary CTA), Services/Offerings, About, "
    "Testimonials, FAQ (accordion), Contact section (styled form + business contact details), footer. "
    "Use the EXACT copy from the brief — headlines, body, testimonials, FAQ.\n"
    "4) Design: modern, polished, generous whitespace, strong visual hierarchy, tasteful gradients/shadows, "
    "hover states and subtle scroll/entrance animations. Anchor the palette to the brand color. "
    "Load the recommended Google Fonts via <link>. Fully responsive (mobile-first) with a working mobile menu.\n"
    "5) Accessibility: semantic HTML, alt text, sufficient contrast, focus states.\n"
    "6) Use high-quality relevant imagery via https://images.unsplash.com/ source URLs or CSS gradients; "
    "never leave broken images. Make it feel bespoke and premium — not templated."
)


def clean_html(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text.strip())
    idx = text.lower().find("<!doctype")
    if idx > 0:
        text = text[idx:]
    return text.strip()


def _build_brief_prompt(fields: dict) -> str:
    lines = [
        f"Business name: {fields.get('business_name','')}",
        f"Industry / type: {fields.get('industry','')}",
        f"Description: {fields.get('description','')}",
        f"Design style preference: {fields.get('style','modern')}",
        f"Primary brand color: {fields.get('primary_color','#0055FF')}",
    ]
    if fields.get("target_audience"): lines.append(f"Target audience: {fields['target_audience']}")
    if fields.get("key_services"): lines.append(f"Key services / products: {fields['key_services']}")
    if fields.get("brand_keywords"): lines.append(f"Brand vibe / keywords: {fields['brand_keywords']}")
    if fields.get("pages"): lines.append(f"Sections the client wants: {fields['pages']}")
    if fields.get("contact_email"): lines.append(f"Contact email: {fields['contact_email']}")
    if fields.get("phone"): lines.append(f"Phone: {fields['phone']}")
    lines.append("\nWrite the complete creative brief now.")
    return "\n".join(lines)


def _build_site_prompt(fields: dict, brief: str) -> str:
    return (
        f"CREATIVE BRIEF:\n{brief}\n\n"
        f"BUSINESS FACTS:\n"
        f"- Name: {fields.get('business_name','')}\n"
        f"- Brand color: {fields.get('primary_color','#0055FF')}\n"
        f"- Contact email: {fields.get('contact_email','')}\n"
        f"- Phone: {fields.get('phone','')}\n\n"
        "Build the complete, premium website now, using the brief's copy and design direction."
    )


def _build_economy_prompt(fields: dict) -> str:
    lines = [
        "Build a complete single-page marketing website for this business. Invent compelling, "
        "specific, on-brand copy yourself — real headlines, benefit-led service descriptions, an "
        "about story, 3 realistic testimonials with names, and 4-5 FAQ items. No lorem ipsum, no placeholders.",
        "",
        f"Business name: {fields.get('business_name','')}",
        f"Industry / type: {fields.get('industry','')}",
        f"Description: {fields.get('description','')}",
        f"Design style preference: {fields.get('style','modern')}",
        f"Primary brand color: {fields.get('primary_color','#0055FF')}",
    ]
    if fields.get("target_audience"): lines.append(f"Target audience: {fields['target_audience']}")
    if fields.get("key_services"): lines.append(f"Key services / products: {fields['key_services']}")
    if fields.get("brand_keywords"): lines.append(f"Brand vibe / keywords: {fields['brand_keywords']}")
    if fields.get("pages"): lines.append(f"Sections the client wants: {fields['pages']}")
    if fields.get("contact_email"): lines.append(f"Contact email: {fields['contact_email']}")
    if fields.get("phone"): lines.append(f"Phone: {fields['phone']}")
    lines.append("\nBuild the full premium website now.")
    return "\n".join(lines)


async def _call_llm(prompt: str, system_message: str, model: str) -> str:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"gen_{uuid.uuid4().hex}",
        system_message=system_message,
    ).with_model("anthropic", model)
    result = await chat.send_message(UserMessage(text=prompt))
    return result if isinstance(result, str) else str(result)


async def _fail_job(job_id: str, e: Exception):
    logger.exception("generation failed")
    msg = str(e).lower()
    if "budget" in msg or "quota" in msg or "insufficient" in msg:
        err = "AI service is temporarily unavailable. Please try again shortly."
    else:
        err = "Generation failed. Please try again."
    await db.gen_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": err}})


async def _run_generation(job_id: str, user_id: str, fields: dict, mode: str = "new", template_id: str = None):
    cost_inputs = []
    try:
        if mode == "edit":
            existing = await db.templates.find_one({"template_id": template_id, "user_id": user_id}, {"_id": 0})
            prompt = (
                "Here is an existing complete HTML website document. Apply the requested changes with the care "
                "of a senior designer and return the FULL updated HTML document only (starting with <!DOCTYPE html>, "
                "no commentary). Preserve everything that works; improve, don't regress.\n\n"
                f"REQUESTED CHANGES:\n{fields.get('instructions','')}\n\n"
                f"CURRENT HTML:\n{existing.get('html','')}"
            )
            html = clean_html(await _call_llm(prompt, GEN_BUILD_SYSTEM, BUILD_MODEL))
            cost_inputs = [prompt, html]
        else:
            quality = (fields.get("quality") or "quality").lower()
            if quality == "economy":
                # Fast single-pass build on the lighter model (fewer credits).
                site_prompt = _build_economy_prompt(fields)
                html = clean_html(await _call_llm(site_prompt, GEN_BUILD_SYSTEM, STRATEGY_MODEL))
                cost_inputs = [site_prompt, html]
            else:
                # Step 1 — strategist thinks and writes a creative brief
                brief_prompt = _build_brief_prompt(fields)
                brief = await _call_llm(brief_prompt, GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
                # Step 2 — builder crafts the site from the brief
                site_prompt = _build_site_prompt(fields, brief)
                html = clean_html(await _call_llm(site_prompt, GEN_BUILD_SYSTEM, BUILD_MODEL))
                cost_inputs = [brief_prompt, brief, site_prompt, html]
    except Exception as e:
        await _fail_job(job_id, e)
        return

    cost = estimate_cost(*cost_inputs)
    if mode == "new":
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        await db.templates.insert_one({
            "template_id": template_id, "user_id": user_id,
            "business_name": fields.get("business_name"), "industry": fields.get("industry"),
            "description": fields.get("description"), "style": fields.get("style"),
            "primary_color": fields.get("primary_color"),
            "contact_email": fields.get("contact_email"), "phone": fields.get("phone"),
            "target_audience": fields.get("target_audience"), "key_services": fields.get("key_services"),
            "brand_keywords": fields.get("brand_keywords"), "pages": fields.get("pages"),
            "quality": fields.get("quality", "quality"),
            "html": html, "created_at": datetime.now(timezone.utc),
        })
    else:
        await db.templates.update_one(
            {"template_id": template_id, "user_id": user_id},
            {"$set": {"html": html, "updated_at": datetime.now(timezone.utc)}},
        )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    charged = 0 if user_is_unlimited(user) else cost
    if charged:
        await deduct_credits(user_id, charged)
    await db.gen_jobs.update_one({"job_id": job_id},
                                 {"$set": {"status": "done", "template_id": template_id,
                                           "cost": charged, "mode": mode}})


async def _start_job(user: dict, fields: dict, mode: str = "new", template_id: str = None):
    if not user_is_unlimited(user) and total_credits(user) <= 0:
        raise HTTPException(status_code=402, detail="You're out of credits. Purchase a credit pack to keep building.")
    if not is_owner(user):
        await check_rate_limit(f"gen:{user['user_id']}", GEN_MAX_PER_WINDOW, GEN_WINDOW_SECONDS)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    await db.gen_jobs.insert_one({
        "job_id": job_id, "user_id": user["user_id"], "status": "pending",
        "template_id": template_id, "error": None, "created_at": datetime.now(timezone.utc),
    })
    asyncio.create_task(_run_generation(job_id, user["user_id"], fields, mode, template_id))
    return {"job_id": job_id, "status": "pending"}
