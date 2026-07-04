import json
import re
import uuid
import asyncio

from emergentintegrations.llm.chat import LlmChat, UserMessage

from config import EMERGENT_LLM_KEY, STRATEGY_MODEL, logger

PRICE_MIN, PRICE_MAX = 200, 500

PRICING_SYSTEM = (
    "You are the pricing analyst agent for a premium website template marketplace. You are given "
    "objective code metrics and a content outline for a professionally built single-page website "
    "template. Price it between $200 and $500 using these calibration bands strictly:\n"
    "- $200-275: solid but simple — 5-7 sections, light interactivity, few animations.\n"
    "- $280-360: rich single-pager — 7-9 sections, moderate JS, several animations, good copy depth.\n"
    "- $370-460: deep professional site — 10+ sections, multiple interactive components, strong "
    "animation suite, 90KB+.\n"
    "- $470-500: FLAGSHIP — awards the top of the range and $500 is expected when a template has 10+ "
    "sections AND ships working advanced components (gallery with lightbox, slider/carousel, multi-step "
    "validated form, accordion, scroll-spy nav, animated counters), 10+ keyframe animations, 25+ JS "
    "listeners and 140KB+ of polished code. Do NOT withhold $500 from templates that meet this bar.\n"
    "Weigh: depth of sections, interactivity (JS behaviours), animations, responsive breakpoints, copy "
    "volume and overall craftsmanship. Respond with ONLY a JSON object, no markdown fences:\n"
    '{"price": <integer 200-500>, "tier": "Standard"|"Professional"|"Premium", '
    '"summary": "<one persuasive sentence describing this template to buyers>", '
    '"highlights": ["<3-5 short selling points>"], '
    '"rationale": "<one sentence explaining the price>"}'
)


def compute_metrics(html: str) -> dict:
    low = html.lower()
    return {
        "html_kb": round(len(html) / 1024, 1),
        "sections": low.count("<section"),
        "media_queries": low.count("@media"),
        "keyframe_animations": low.count("@keyframes"),
        "js_listeners": low.count("addeventlistener"),
        "forms": low.count("<form"),
        "images": low.count("<img") + low.count("background-image"),
        "buttons_links": low.count("<a ") + low.count("<button"),
        "headings": sum(low.count(f"<h{i}") for i in range(1, 4)),
        "google_fonts": low.count("fonts.googleapis"),
    }


def _clamp(p) -> int:
    return int(max(PRICE_MIN, min(PRICE_MAX, round(float(p) / 5) * 5)))


def _tier(price: int) -> str:
    if price >= 400:
        return "Premium"
    if price >= 300:
        return "Professional"
    return "Standard"


def _heuristic_price(m: dict) -> int:
    score = (
        min(m["html_kb"] / 60.0, 1) * 90
        + min(m["sections"] / 8.0, 1) * 60
        + min(m["keyframe_animations"] / 6.0, 1) * 50
        + min(m["js_listeners"] / 8.0, 1) * 45
        + min(m["media_queries"] / 4.0, 1) * 30
        + min(m["images"] / 10.0, 1) * 25
    )
    return _clamp(PRICE_MIN + score)


def _outline(html: str) -> str:
    text = re.sub(r"<style[\s\S]*?</style>|<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    headings = re.findall(r"<h[1-3][^>]*>([\s\S]*?)</h[1-3]>", text, flags=re.IGNORECASE)
    clean = [re.sub(r"<[^>]+>|\s+", " ", h).strip() for h in headings]
    return " | ".join(h for h in clean if h)[:1200]


async def price_template(tpl: dict) -> dict:
    """AI Pricing Agent: analyzes template depth and returns a $200-500 price + listing copy."""
    html = tpl.get("html", "")
    metrics = compute_metrics(html)
    prompt = (
        f"Template: {tpl.get('business_name', '')} — {tpl.get('industry', '')}\n"
        f"Description: {tpl.get('description', '')}\n"
        f"Build quality mode: {tpl.get('quality', 'quality')}\n"
        f"CODE METRICS: {json.dumps(metrics)}\n"
        f"CONTENT OUTLINE (headings): {_outline(html)}\n\n"
        "Analyze the depth and output the pricing JSON now."
    )
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"price_{uuid.uuid4().hex}",
                       system_message=PRICING_SYSTEM).with_model("anthropic", STRATEGY_MODEL)
        raw = str(await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=90)).strip()
        data = json.loads(re.search(r"\{[\s\S]*\}", raw).group(0))
        price = _clamp(data.get("price", 0))
        return {
            "price_usd": price,
            "tier": data.get("tier") if data.get("tier") in ("Standard", "Professional", "Premium") else _tier(price),
            "summary": str(data.get("summary") or "")[:300],
            "highlights": [str(h)[:90] for h in (data.get("highlights") or [])][:5],
            "rationale": str(data.get("rationale") or "")[:300],
            "metrics": metrics,
            "priced_by": "ai",
        }
    except Exception:
        logger.exception("pricing agent failed; falling back to heuristic pricing")
        price = _heuristic_price(metrics)
        return {
            "price_usd": price,
            "tier": _tier(price),
            "summary": f"A polished, conversion-ready {tpl.get('industry', 'business')} website template.",
            "highlights": ["Fully responsive design", "Complete ready-to-edit copy",
                           "Modern animations & interactions"],
            "rationale": "Priced from objective code-depth metrics.",
            "metrics": metrics,
            "priced_by": "heuristic",
        }
