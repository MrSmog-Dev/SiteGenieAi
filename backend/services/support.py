"""Halo — customer-facing support AI.

Public (no-auth) support chat for real customers/visitors, plus:
- feedback detection that routes customer feedback into the OWNER's Team Pulse feed
- generation of the customer-facing FAQ / Refund Policy / Terms of Service pages
  (drafted by Halo, grounded in real SiteGenie facts) that are published on the website.
"""
import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import (EMERGENT_LLM_KEY, STRATEGY_MODEL, OWNER_EMAIL, logger,
                    SUBSCRIPTION_PLANS, CREDIT_PACKS)
from database import db
from services.activity import log_activity


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_facts() -> str:
    plans = "; ".join(
        f"{p['name']} ${p['amount']:.0f} ({'unlimited AI credits' if p['unlimited'] else str(p['monthly_credits']) + ' credits/mo'})"
        for p in SUBSCRIPTION_PLANS.values())
    packs = "; ".join(f"{p['name']} ${p['amount']:.0f} for {p['credits']} credits" for p in CREDIT_PACKS.values())
    return (
        "SiteGenie turns a short description of a business into a complete, responsive, professionally "
        "designed website in minutes using an agentic AI pipeline — no code, no designer.\n"
        f"SUBSCRIPTION PLANS: {plans}. New accounts get 15 free credits.\n"
        f"CREDIT PACKS (top-ups): {packs}. Credits are consumed per AI operation based on work done.\n"
        "TEMPLATE MARKET: premium, ready-made AI-built website templates for a $200-$500 one-time price. "
        "Buyers OWN the template forever and get FREE UNLIMITED AI edits on it, plus a ZIP export.\n"
        "PUBLISHING: sites publish to a free vanity URL, can map a custom domain, export as a ZIP, and "
        "include SEO meta tags, branded social share images, and per-site view analytics.\n"
        "SUPPORT: this chat is the fastest way to get help; for account-specific billing the customer "
        "should be logged in."
    )


SITE_FACTS = _plan_facts()


HALO_SUPPORT_SYSTEM = (
    "You are Halo, the friendly customer support AI for SiteGenie (sitegenie.dev). You are the first "
    "point of contact for visitors and customers on the website. Be warm, patient, concise and genuinely "
    "helpful. De-escalate first, solve second. Use short paragraphs or numbered steps a non-technical "
    "person can follow. Speak in first person as Halo.\n\n"
    "GROUND EVERYTHING IN THESE FACTS (never invent features, prices or promises beyond them):\n"
    f"{SITE_FACTS}\n\n"
    "POLICY: Be honest about limits. Do NOT promise specific refunds, discounts, timelines or custom "
    "work — instead point customers to the Refund Policy, FAQ or Pricing pages and offer to pass their "
    "request to the team. If someone shares a bug, complaint, feature request or feedback, thank them "
    "sincerely and tell them you're logging it for the team. If they want a real website, encourage them "
    "to try the generator on the homepage (15 free credits) or browse the Template Market. Keep replies "
    "under ~120 words unless they ask for detail."
)


async def halo_reply(history: list, message: str) -> str:
    convo = "\n".join(
        f"{'Customer' if m.get('role') == 'user' else 'Halo'}: {m.get('content', '')}" for m in history[-10:])
    prompt = (f"CONVERSATION SO FAR:\n{convo}\n\n" if convo else "") + f"Customer: {message}"
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"halo_support_{uuid.uuid4().hex[:8]}",
                   system_message=HALO_SUPPORT_SYSTEM).with_model("anthropic", STRATEGY_MODEL)
    return str(await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=60)).strip()


FEEDBACK_DETECT_SYSTEM = (
    "You analyze a customer's message to SiteGenie support and decide if it contains actionable signal "
    "worth routing to the business team: a feature request, a bug report, a complaint, a compliment/praise, "
    "or general product feedback. Casual questions, greetings and how-to requests are NOT feedback.\n"
    "Reply with ONLY a JSON object, no markdown:\n"
    '{"is_feedback": true|false, "kind": "feature"|"bug"|"complaint"|"praise"|"feedback", '
    '"summary": "<one concise sentence for the team, max 160 chars>", "sentiment": "positive"|"neutral"|"negative"}'
)


async def _owner_id() -> str | None:
    owner = await db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "user_id": 1})
    return owner["user_id"] if owner else None


async def detect_customer_feedback(session_id: str, message: str, reply: str,
                                   contact: dict | None = None):
    """If the customer's message is real feedback, log it to the owner's Team Pulse and store it."""
    try:
        raw = await _call_feedback(message)
        data = json.loads(re.search(r"\{[\s\S]*\}", str(raw)).group(0))
        if not data.get("is_feedback"):
            return
        owner_id = await _owner_id()
        if not owner_id:
            return
        kind = data.get("kind", "feedback")
        summary = str(data.get("summary", "")).strip()[:200] or message[:160]
        label = {"feature": "Feature request", "bug": "Bug report", "complaint": "Complaint",
                 "praise": "Praise", "feedback": "Feedback"}.get(kind, "Feedback")
        fb = {"feedback_id": f"fb_{uuid.uuid4().hex[:10]}", "session_id": session_id,
              "kind": kind, "summary": summary, "sentiment": data.get("sentiment", "neutral"),
              "message": message[:1000], "contact": contact or {}, "status": "new",
              "created_at": _now()}
        await db.customer_feedback.insert_one(dict(fb))
        await log_activity(
            owner_id, "halo", "feedback",
            f"{label} from a customer: {summary}",
            detail=f'They said: "{message[:280]}"', link="/team?agent=halo")
        logger.info("halo: routed customer %s to team pulse", kind)
    except Exception:
        logger.exception("customer feedback detection failed")


async def _call_feedback(message: str) -> str:
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"fb_{uuid.uuid4().hex[:8]}",
                   system_message=FEEDBACK_DETECT_SYSTEM).with_model("anthropic", STRATEGY_MODEL)
    return str(await asyncio.wait_for(
        chat.send_message(UserMessage(text=f"Customer message:\n{message[:1200]}")), timeout=45)).strip()


# ---------------- Website policy pages (drafted by Halo) ----------------

PAGE_SPECS = {
    "faq": ("Frequently Asked Questions",
            "Write a comprehensive customer FAQ for SiteGenie covering: what SiteGenie is and how it works, "
            "getting started + the 15 free credits, how credits work, the subscription plans, the Template "
            "Market (ownership, free unlimited edits, ZIP export), publishing + custom domains + analytics, "
            "editing a generated site, and how to get help. Group into 8-12 Q&A pairs."),
    "refund": ("Refund Policy",
               "Write a fair, clear Refund Policy for SiteGenie. Cover: subscription refunds (pro-rated / "
               "case-by-case within a reasonable window since it's a usage/credit product), one-time "
               "Template Market purchases (digital goods you own forever — generally non-refundable once "
               "downloaded/edited, but the team reviews genuine issues), credit packs, how to request a "
               "refund (contact support with order details), and typical response time. Keep it honest and "
               "customer-friendly, not legalistic. Do NOT invent a specific guaranteed money-back number of "
               "days — frame it as reviewed case-by-case."),
    "terms": ("Terms of Service",
              "Write plain-language Terms of Service for SiteGenie. Cover: acceptance of terms, account "
              "responsibilities, acceptable use, credits & billing, ownership of generated sites and "
              "purchased templates, AI-generated content disclaimer (review before publishing), "
              "intellectual property, service availability, limitation of liability, changes to the "
              "service/terms, and how to contact us. Readable, section headings, not scary boilerplate."),
}

PAGE_WRITER_SYSTEM = (
    "You are Halo, SiteGenie's customer support lead, drafting an official page for the SiteGenie website. "
    "Write in clear, warm, plain language a customer can actually understand — helpful, not intimidating "
    "legalese. Ground every claim in these facts (do not contradict or invent beyond them):\n"
    f"{SITE_FACTS}\n\n"
    "Output ONLY clean semantic HTML for the page BODY (no <html>/<head>/<body> wrapper, no markdown "
    "fences). Use <h2> for section titles, <h3> for sub-points/questions, <p>, <ul>/<li>. Start with a "
    "short 1-2 sentence intro paragraph. Do NOT include the page's main title (it is rendered separately). "
    "End with a short line inviting them to chat with Halo or email support for anything else."
)


async def generate_page(kind: str) -> dict:
    from services.llm import _call_llm
    title, brief = PAGE_SPECS[kind]
    html = str(await _call_llm(brief + "\n\nWrite the page now.", PAGE_WRITER_SYSTEM, STRATEGY_MODEL))
    html = re.sub(r"^```[a-z]*\n?|```$", "", html.strip()).strip()
    doc = {"kind": kind, "title": title, "html": html, "updated_at": _now(), "author": "halo"}
    await db.site_pages.update_one({"kind": kind}, {"$set": doc}, upsert=True)
    logger.info("halo: generated site page '%s'", kind)
    return doc


async def get_page(kind: str) -> dict | None:
    if kind not in PAGE_SPECS:
        return None
    page = await db.site_pages.find_one({"kind": kind}, {"_id": 0})
    if not page:
        # auto-seed on first access so the pages are always live
        page = await generate_page(kind)
    return page


async def ensure_pages():
    """Generate any missing policy pages (called at startup)."""
    for kind in PAGE_SPECS:
        existing = await db.site_pages.find_one({"kind": kind}, {"_id": 1})
        if not existing:
            try:
                await generate_page(kind)
            except Exception:
                logger.exception("ensure_pages failed for %s", kind)
