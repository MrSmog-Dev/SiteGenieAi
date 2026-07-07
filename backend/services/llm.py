import uuid
import re
import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage

from database import db
from config import (
    EMERGENT_LLM_KEY, STRATEGY_MODEL, BUILD_MODEL,
    GEN_MAX_PER_WINDOW, GEN_WINDOW_SECONDS, logger,
)

# Per-LLM-call ceiling. Sonnet 4.6 builds usually return in 40-120s; anything
# beyond this is treated as an upstream stall so the job doesn't hang forever.
LLM_CALL_TIMEOUT_S = 240
from security import (
    estimate_cost, deduct_credits, user_is_unlimited, is_owner,
    total_credits, check_rate_limit,
)

GEN_STRATEGY_SYSTEM = (
    "You are a world-class brand strategist and direct-response conversion copywriter behind luxury "
    "small-business websites that feel expensive yet warm and approachable. A client described their "
    "business. Think like a $20k-agency consultant and produce a rich CREATIVE BRIEF for a "
    "high-converting single-page marketing website. Do NOT write HTML. Write specific, on-brand, "
    "ready-to-use content — never placeholders or lorem ipsum. Use markdown with these parts:\n"
    "1. POSITIONING: a one-line positioning statement + the core value proposition (premium but human).\n"
    "2. AUDIENCE: the ideal customer, their pains and aspirations.\n"
    "3. VOICE & TONE: confident, elegant, welcoming — luxury that doesn't intimidate.\n"
    "4. UNIQUE SELLING POINTS: 3-5 concrete differentiators.\n"
    "5. TRUST BADGES: 4 short credibility badges tailored to THIS business/industry "
    "(e.g. 'Licensed & Insured', '15+ Years', '5-Star Rated', '100% Satisfaction Guarantee', "
    "'Award-Winning', 'Free Consultation') — each a 2-4 word label.\n"
    "6. SECTION-BY-SECTION PLAN — write the ACTUAL final copy for each:\n"
    "   • HERO: a bold benefit-driven HEADLINE, a supporting SUBHEADLINE, a PRIMARY CTA label and a "
    "SECONDARY CTA label, plus a one-line trust strip.\n"
    "   • ABOUT: a compelling short brand story PLUS 3-4 'value cards' (icon idea + short title + 1-line "
    "benefit) and the 4 trust badges above.\n"
    "   • SERVICES/OFFERINGS: 3-6 items, each name + 1-2 line benefit-led description, presented as cards.\n"
    "   • SOCIAL PROOF: 3 realistic, specific testimonials with believable names + roles, and a stats row "
    "(3-4 impressive numbers with labels).\n"
    "   • FAQ: 5 real high-intent questions with helpful answers.\n"
    "   • CONTACT/CTA: a closing headline + supporting line + what the form asks + the primary action.\n"
    "7. PRIMARY CONVERSION ACTION: name the single most valuable action for this business (e.g. Book a "
    "Consultation, Get a Quote, Reserve a Table, Shop Now, Call Now) — every CTA should drive toward it.\n"
    "8. DESIGN DIRECTION: a refined color palette (hex, anchored to the brand color, with an elegant "
    "accent + neutrals), a premium Google-Fonts pairing (an elegant display heading + clean readable body), "
    "imagery/visual style, and the overall luxurious-yet-approachable mood.\n"
    "Be concrete and specific to THIS business. Quality and depth over brevity."
)

GEN_BUILD_SYSTEM = (
    "You are an award-winning luxury web designer and senior front-end engineer. Using the provided "
    "CREATIVE BRIEF, output a SINGLE complete, production-ready, fully responsive HTML5 website that looks "
    "like a premium agency built it — high-converting, luxurious but approachable. Rules:\n"
    "1) Return ONLY raw HTML starting with <!DOCTYPE html>. No markdown, no code fences, no commentary.\n"
    "2) All CSS in ONE <style> tag in <head>. Vanilla only (no external CSS frameworks). Vanilla JS is "
    "allowed for: mobile nav toggle, smooth in-page scrolling, FAQ accordion, scroll-reveal animations, "
    "and animated stat counters.\n"
    "3) REQUIRED sections, in order, each a <section> with a matching id: sticky glassy nav (with anchor "
    "links to every section + a prominent CTA button); HERO (id='home') — a strong HEADLINE, a SUBHEADLINE, "
    "a PRIMARY CTA button and a SECONDARY CTA button, plus a small trust strip; ABOUT (id='about') — brand "
    "story + a row of 3-4 professional VALUE CARDS (icon + title + line) and a row of 4 TRUST BADGES "
    "(pill/chip style with an icon); SERVICES (id='services') — 3-6 elegant CARDS; SOCIAL PROOF — a STATS "
    "row (3-4 animated counters) + 3 TESTIMONIAL cards; FAQ (id='faq') — accordion; CONTACT (id='contact') "
    "— a styled, validated form + business contact details; footer with nav links. Use the EXACT copy from "
    "the brief.\n"
    "4) FUNCTIONAL CTAs — this is critical: EVERY button and nav link must actually work. In-page CTAs "
    "(Book, Get a Quote, Contact, Learn More, View Services) MUST link to the correct section anchor "
    "(href='#contact', '#services', '#about', etc.) and smooth-scroll there. 'Call' buttons use "
    "href='tel:'+the phone, 'Email' uses href='mailto:'+the email. The contact form must have a working "
    "client-side submit handler that validates and shows a success state. No dead '#' links, no buttons "
    "that do nothing.\n"
    "5) LUXURY DESIGN: generous whitespace, strong typographic hierarchy with an elegant display font for "
    "headings, refined color palette anchored to the brand color with a tasteful accent, soft shadows, "
    "rounded-but-crisp cards, subtle gradients, elegant hover states, and gentle scroll-triggered entrance "
    "animations. Feel expensive but warm and inviting — never cold or intimidating. Fully responsive "
    "(mobile-first) with a working mobile menu.\n"
    "6) Accessibility: semantic HTML, alt text, sufficient contrast, visible focus states.\n"
    "7) Imagery via https://images.unsplash.com/ source URLs relevant to the business, or refined CSS "
    "gradients/patterns; never leave broken images. Make it feel bespoke and premium — not templated."
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


def _design_block(fields: dict) -> str:
    try:
        from services.design_intel import design_directive
        return "\n\n" + design_directive(fields)
    except Exception:
        return ""


def _build_site_prompt(fields: dict, brief: str) -> str:
    return (
        f"CREATIVE BRIEF:\n{brief}\n\n"
        f"BUSINESS FACTS:\n"
        f"- Name: {fields.get('business_name','')}\n"
        f"- Brand color: {fields.get('primary_color','#0055FF')}\n"
        f"- Contact email: {fields.get('contact_email','')}\n"
        f"- Phone: {fields.get('phone','')}\n\n"
        "Build the complete, LUXURY, high-converting website now, using the brief's copy and design "
        "direction. Make EVERY CTA and nav link functional: in-page CTAs smooth-scroll to the right "
        "section anchor; wire 'Call' to tel: and 'Email'/'Contact' to mailto: using the contact details "
        "above (or the #contact form); the form must validate and show a success state. Include the "
        "professional trust badges and value cards in the About section."
        + _design_block(fields)
    )


def _build_economy_prompt(fields: dict) -> str:
    lines = [
        "Build a complete, high-converting, LUXURY-but-approachable single-page marketing website for this "
        "business. Invent compelling, specific, on-brand copy yourself — no lorem ipsum, no placeholders.",
        "",
        "REQUIRED sections, each a <section> with a matching id: sticky nav with anchor links + a CTA "
        "button; HERO (id='home') with a bold HEADLINE, a SUBHEADLINE, a PRIMARY CTA button and a SECONDARY "
        "CTA button and a small trust strip; ABOUT (id='about') with a short brand story, 3-4 professional "
        "VALUE CARDS (icon + title + line) and 4 TRUST BADGES tailored to this business (e.g. Licensed & "
        "Insured, 15+ Years, 5-Star Rated, Satisfaction Guaranteed); SERVICES (id='services') as elegant "
        "cards; a STATS row (3-4 numbers) + 3 TESTIMONIALS with real names; FAQ (id='faq') accordion; "
        "CONTACT (id='contact') with a validated form + contact details; footer.",
        "FUNCTIONAL CTAs: every button/nav link must work — in-page CTAs link to the right section anchor "
        "and smooth-scroll; 'Call' uses tel:, 'Email' uses mailto:; the form validates and shows success. "
        "No dead links.",
        "Design: luxury but warm — elegant display heading font, generous whitespace, refined palette "
        "anchored to the brand color, soft shadows, rounded cards, tasteful hover + scroll-reveal "
        "animations. Fully responsive with a working mobile menu.",
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
    return "\n".join(lines) + _design_block(fields)


async def _call_llm(prompt: str, system_message: str, model: str, timeout: int = None) -> str:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"gen_{uuid.uuid4().hex}",
        system_message=system_message,
    ).with_model("anthropic", model)
    result = await asyncio.wait_for(
        chat.send_message(UserMessage(text=prompt)),
        timeout=timeout or LLM_CALL_TIMEOUT_S,
    )
    return result if isinstance(result, str) else str(result)


async def _call_build_llm(prompt: str, model: str = None) -> str:
    """Quality build with auto-fallback: if the heavy model times out, retry once on the fast model."""
    primary = model or BUILD_MODEL
    try:
        return await _call_llm(prompt, GEN_BUILD_SYSTEM, primary)
    except asyncio.TimeoutError:
        logger.warning("build model %s timed out after %ss; falling back to economy model", primary, LLM_CALL_TIMEOUT_S)
        return await _call_llm(prompt, GEN_BUILD_SYSTEM, STRATEGY_MODEL)


PREMIUM_POLISH_SYSTEM = (
    "You are a senior front-end engineer polishing a premium marketing website. You will receive a "
    "complete HTML5 document. Return the FULL updated HTML (starting with <!DOCTYPE html>, no commentary, "
    "no code fences) with these upgrades — do NOT regress anything:\n"
    "• Add subtle scroll-triggered entrance animations (IntersectionObserver-based) and gentle hover "
    "micro-interactions.\n"
    "• Add a functional lightbox gallery OR an image slider (3-6 items) in an appropriate section.\n"
    "• Add a stats/counter row (3-4 numbers animating up when in view).\n"
    "• Add an FAQ accordion (if not already present) with 5 high-intent Q&As.\n"
    "• Improve the contact form: multi-step or richer fields (name, email, phone, service, message) with "
    "client-side validation.\n"
    "• Refine typography scale, spacing rhythm, section transitions and add a subtle scroll-progress bar.\n"
    "Keep all existing copy and structure; only enhance."
)


async def _premium_polish(html: str) -> str:
    """Extra depth pass for Premium tier. Falls back gracefully if the model times out."""
    prompt = (
        "Apply the premium polish upgrades to the following HTML. Return the full updated document.\n\n"
        f"CURRENT HTML:\n{html}"
    )
    try:
        polished = await _call_llm(prompt, PREMIUM_POLISH_SYSTEM, BUILD_MODEL)
    except asyncio.TimeoutError:
        logger.warning("premium polish pass timed out; keeping quality build")
        return html
    cleaned = clean_html(polished)
    # Guard against a truncated response — only accept if it grew or stayed roughly the same size.
    if len(cleaned) < len(html) * 0.85 or not cleaned.lower().startswith("<!doctype"):
        logger.warning("premium polish returned short/invalid output; keeping quality build")
        return html
    return cleaned


# ---------------- Premium upgrade (existing sites) — addendum injection ----------------
# Full-HTML rewrites of large existing sites reliably time out; instead the model returns
# small STYLE/SECTIONS/SCRIPT addendum blocks that we inject into the existing document.

UPGRADE_ENHANCE_SYSTEM = (
    "You are a principal front-end engineer adding premium upgrades to an existing single-file website. "
    "You receive its design context. You respond with ONLY three blocks in this EXACT format and nothing "
    "else:\n"
    "===STYLE===\n<style>/* all new CSS, matching the site's existing design tokens */</style>\n"
    "===SECTIONS===\n<!-- all NEW full <section> elements, matching the site's class conventions -->\n"
    "===SCRIPT===\n<script>/* all vanilla JS, defensive with null checks so it never throws */</script>"
)

UPGRADE_ENHANCE_PROMPT = (
    "You are upgrading an existing single-file website to Premium tier. Below is its design context "
    "(palette, fonts, class conventions, existing sections). Everything you produce must match that "
    "design system exactly and be self-contained (no external assets). JS must be defensive (null "
    "checks, no errors if an element is missing)."
)

UPGRADE_TASKS = [
    ("behaviors",
     "Produce: scroll-reveal entrance animations for ALL existing <section> elements via "
     "IntersectionObserver (CSS classes + JS), a thin scroll-progress bar fixed at the top, animated "
     "number counters for elements containing digits in stats, a floating back-to-top button "
     "(JS-created), smooth-scroll for anchor links and gentle hover micro-interactions. At least 2 new "
     "@keyframes. SECTIONS block may be empty for this task."),
    ("sections",
     "Produce THREE new sections: (1) an interactive gallery ('Our Work' style, 6 items using CSS-styled "
     "placeholder tiles with gradients/icons, NO external images) with a working lightbox (open/close, "
     "prev/next, ESC), (2) an FAQ accordion with 5 high-intent Q&As and smooth height animation, and "
     "(3) a richer contact/booking section with a validated multi-field form (name, email, phone, "
     "service, message) and an animated success state. Include 2 new @keyframes."),
]


def _extract_block(block: str, raw: str, next_marker: str = None) -> str:
    if f"==={block}===" not in raw:
        return ""
    part = raw.split(f"==={block}===", 1)[1]
    if next_marker and f"==={next_marker}===" in part:
        part = part.split(f"==={next_marker}===", 1)[0]
    return part.strip()


def _inject_addendum(html: str, raw: str) -> str:
    style = _extract_block("STYLE", raw, "SECTIONS")
    sections = _extract_block("SECTIONS", raw, "SCRIPT")
    script = _extract_block("SCRIPT", raw)
    if not (style or sections or script):
        return html
    if style and "</head>" in html:
        html = html.replace("</head>", f"\n{style}\n</head>", 1)
    if sections:
        anchor = "<footer" if "<footer" in html else "</body>"
        html = html.replace(anchor, f"\n{sections}\n{anchor}", 1)
    if script and "</body>" in html:
        html = html.replace("</body>", f"\n{script}\n</body>", 1)
    return html


def _upgrade_design_context(html: str) -> str:
    style = ""
    m = re.search(r"<style[\s\S]*?</style>", html, re.I)
    if m:
        style = m.group(0)[:14000]
    sections = re.findall(r"<section[^>]*>", html)
    title = re.search(r"<title[^>]*>([^<]*)", html, re.I)
    return (f"SITE TITLE: {title.group(1) if title else ''}\n"
            f"EXISTING SECTION TAGS: {sections}\n"
            f"EXISTING CSS (design tokens, fonts, palette, class conventions):\n{style}")


async def _premium_upgrade(html: str):
    """Upgrade an existing site to Premium via addendum injection. Returns (html, llm_outputs)."""
    ctx = _upgrade_design_context(html)
    outputs = []
    for task_name, task in UPGRADE_TASKS:
        prompt = f"{UPGRADE_ENHANCE_PROMPT}\nTASK ({task_name}): {task}\n\n{ctx}"
        try:
            raw = await _call_llm(prompt, UPGRADE_ENHANCE_SYSTEM, BUILD_MODEL, timeout=300)
        except asyncio.TimeoutError:
            logger.warning("premium upgrade task %s timed out on %s; retrying on fast model", task_name, BUILD_MODEL)
            try:
                raw = await _call_llm(prompt, UPGRADE_ENHANCE_SYSTEM, STRATEGY_MODEL, timeout=240)
            except asyncio.TimeoutError:
                logger.warning("premium upgrade task %s timed out twice; skipped", task_name)
                continue
        new_html = _inject_addendum(html, str(raw))
        if new_html != html:
            outputs.append(str(raw))
            html = new_html
    return html, outputs


async def _fail_job(job_id: str, e: Exception):
    logger.exception("generation failed")
    if isinstance(e, asyncio.TimeoutError):
        err = "The AI took too long to respond. Please try again — Economy mode is faster if the site is simple."
    else:
        msg = str(e).lower()
        if "budget" in msg or "quota" in msg or "insufficient" in msg:
            err = "AI service is temporarily unavailable. Please try again shortly."
        else:
            err = "Generation failed. Please try again."
    await db.gen_jobs.update_one({"job_id": job_id}, {"$set": {"status": "error", "error": err}})


async def _set_stage(job_id: str, stage: str):
    await db.gen_jobs.update_one({"job_id": job_id}, {"$set": {"stage": stage}})


async def _run_generation(job_id: str, user_id: str, fields: dict, mode: str = "new", template_id: str = None, free: bool = False):
    cost_inputs = []
    build_model = (fields.get("model") or "").strip() or None
    try:
        if mode == "upgrade":
            existing = await db.templates.find_one({"template_id": template_id, "user_id": user_id}, {"_id": 0})
            html, outputs = await _premium_upgrade(existing.get("html", ""))
            if not outputs:
                await db.gen_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "error",
                              "error": "The premium upgrade didn't complete this time — please try again."}})
                return
            cost_inputs = outputs
        elif mode == "edit":
            await _set_stage(job_id, "refining")
            existing = await db.templates.find_one({"template_id": template_id, "user_id": user_id}, {"_id": 0})
            prompt = (
                "Here is an existing complete HTML website document. Apply the requested changes with the care "
                "of a senior designer and return the FULL updated HTML document only (starting with <!DOCTYPE html>, "
                "no commentary). Preserve everything that works; improve, don't regress.\n\n"
                f"REQUESTED CHANGES:\n{fields.get('instructions','')}\n\n"
                f"CURRENT HTML:\n{existing.get('html','')}"
            )
            html = clean_html(await _call_build_llm(prompt, build_model))
            cost_inputs = [prompt, html]
        else:
            quality = (fields.get("quality") or "quality").lower()
            if quality == "economy":
                # Fast single-pass build on the lighter model (fewer credits).
                await _set_stage(job_id, "building")
                site_prompt = _build_economy_prompt(fields)
                html = clean_html(await _call_llm(site_prompt, GEN_BUILD_SYSTEM, STRATEGY_MODEL))
                cost_inputs = [site_prompt, html]
            else:
                # Step 1 — strategist thinks and writes a creative brief
                await _set_stage(job_id, "designing")
                brief_prompt = _build_brief_prompt(fields)
                brief = await _call_llm(brief_prompt, GEN_STRATEGY_SYSTEM, STRATEGY_MODEL)
                # Step 2 — builder crafts the site from the brief
                await _set_stage(job_id, "building")
                site_prompt = _build_site_prompt(fields, brief)
                html = clean_html(await _call_build_llm(site_prompt, build_model))
                cost_inputs = [brief_prompt, brief, site_prompt, html]
                # Step 3 (Premium only) — polish pass for depth, animations, gallery, counters
                if quality == "premium":
                    await _set_stage(job_id, "polishing")
                    polished = await _premium_polish(html)
                    if polished != html:
                        cost_inputs.append(polished)
                        html = polished
    except Exception as e:
        await _fail_job(job_id, e)
        return

    cost = estimate_cost(*cost_inputs)
    # Small conversational tweaks are billed at a discount (half, min 1 credit).
    if mode == "edit" and fields.get("tweak"):
        cost = max(1, cost // 2)
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
            "model": build_model,
            "html": html, "created_at": datetime.now(timezone.utc),
        })
    else:
        update = {"html": html, "updated_at": datetime.now(timezone.utc)}
        if mode == "upgrade":
            update["quality"] = "premium"
        await db.templates.update_one(
            {"template_id": template_id, "user_id": user_id},
            {"$set": update},
        )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    charged = 0 if free or user_is_unlimited(user) else cost
    if charged:
        await deduct_credits(user_id, charged)
    await db.gen_jobs.update_one({"job_id": job_id},
                                 {"$set": {"status": "done", "template_id": template_id,
                                           "cost": charged, "mode": mode}})


def _min_cost(mode: str, fields: dict) -> int:
    if mode == "new":
        return {"economy": 1, "quality": 4, "premium": 8}.get((fields or {}).get("quality") or "quality", 4)
    if mode in ("upgrade", "regenerate"):
        return 4
    return 1


async def _start_job(user: dict, fields: dict, mode: str = "new", template_id: str = None, free: bool = False):
    metered = not free and not user_is_unlimited(user)
    if metered and total_credits(user) <= 0:
        raise HTTPException(status_code=402, detail="You're out of credits. Purchase a credit pack to keep building.")
    if metered and total_credits(user) < _min_cost(mode, fields):
        raise HTTPException(status_code=402,
                            detail=f"This operation needs at least {_min_cost(mode, fields)} credits. "
                                   "Top up a credit pack to continue.")
    if not is_owner(user):
        await check_rate_limit(f"gen:{user['user_id']}", GEN_MAX_PER_WINDOW, GEN_WINDOW_SECONDS)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    await db.gen_jobs.insert_one({
        "job_id": job_id, "user_id": user["user_id"], "status": "pending",
        "template_id": template_id, "error": None, "created_at": datetime.now(timezone.utc),
    })
    if not is_owner(user):
        # Atomic-enough concurrency cap: count AFTER inserting our own job (self included),
        # so two racing requests both see the overflow and both get rejected.
        recent = datetime.now(timezone.utc) - timedelta(minutes=10)
        active = await db.gen_jobs.count_documents(
            {"user_id": user["user_id"], "status": "pending", "created_at": {"$gt": recent}})
        if active > 2:
            await db.gen_jobs.delete_one({"job_id": job_id})
            raise HTTPException(status_code=429,
                                detail="You already have builds in progress. Please wait for them to finish.")
    asyncio.create_task(_run_generation(job_id, user["user_id"], fields, mode, template_id, free))
    return {"job_id": job_id, "status": "pending"}
