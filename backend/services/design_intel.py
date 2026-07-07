"""Design Intelligence — SiteGenie's port of the UI-UX-Pro-Max skill.

Runs the vendored skill's design-system engine (uiux_skill/) server-side to produce a
tailored design spec (pattern, style, exact palette, font pairing, effects, anti-patterns)
for a business, then exposes it + the skill's pro-UI quality rules for injection into the
website builder prompt. Pure stdlib + CSV — no external deps, ~1s, cached in-process.
"""
import os
import sys
import functools

from config import logger

_SKILL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uiux_skill")
if _SKILL_DIR not in sys.path:
    sys.path.insert(0, _SKILL_DIR)

try:
    from design_system import generate_design_system as _gen_ds  # type: ignore
    _AVAILABLE = True
except Exception:
    logger.exception("UI-UX-Pro-Max skill engine not available")
    _AVAILABLE = False


# The skill's non-negotiable quality rules, distilled for a single-file marketing site build.
PRO_UI_RULES = (
    "PROFESSIONAL UI RULES (from the UI-UX-Pro-Max design system — follow strictly):\n"
    "• Accessibility: text contrast >= 4.5:1; visible focus states; descriptive alt text; semantic headings h1->h2->h3 (no skips); never convey meaning by color alone.\n"
    "• Icons: use inline SVG icons (Lucide/Heroicons style), NEVER emojis as UI/section icons. One consistent icon style + stroke width.\n"
    "• Touch/interaction: clickable elements >= 44px, cursor:pointer, clear hover AND active states; each section has ONE primary CTA, secondary actions visually subordinate.\n"
    "• Typography: base body 16px+, line-height 1.5-1.75, 60-75 chars per line; a clear type scale; bold headings (600-700), regular body (400).\n"
    "• Color: use the provided palette as CSS variables (semantic tokens), not scattered raw hex; anchor everything to the primary + accent.\n"
    "• Spacing: 4/8px rhythm; generous whitespace; consistent max-width container; strong visual hierarchy via size/space/contrast.\n"
    "• Motion: entrance + hover micro-interactions 150-300ms, ease-out; animate transform/opacity only; respect prefers-reduced-motion; animate 1-2 key elements per section (not everything).\n"
    "• Forms: visible labels (not placeholder-only), correct input types (email/tel), inline validation on blur, clear success state.\n"
    "• Responsive: mobile-first; breakpoints ~375/768/1024/1440; no horizontal scroll; working mobile menu.\n"
    "• Images: real relevant Unsplash source URLs or refined CSS gradients; declare sizes to avoid layout shift; never broken images."
)


@functools.lru_cache(maxsize=256)
def _cached_spec(query: str) -> str:
    if not _AVAILABLE:
        return ""
    try:
        return _gen_ds(query, "SiteGenie Build", output_format="markdown") or ""
    except Exception:
        logger.exception("design system generation failed for %r", query)
        return ""


def design_spec_for(fields: dict) -> str:
    """Build a design-system query from the business fields and return the skill's markdown spec."""
    parts = [fields.get("industry", ""), fields.get("business_name", ""),
             fields.get("brand_keywords", ""), fields.get("style", "")]
    query = " ".join(p for p in parts if p).strip() or (fields.get("description", "") or "website")[:120]
    return _cached_spec(query[:160])


def design_directive(fields: dict) -> str:
    """The full design-intelligence block to inject into the builder prompt."""
    spec = design_spec_for(fields)
    if not spec:
        return PRO_UI_RULES
    return (
        "DESIGN SYSTEM (authoritative — derived by the UI-UX-Pro-Max engine for THIS business; "
        "use its exact palette, font pairing, effects and layout pattern, and honor its anti-patterns):\n"
        f"{spec}\n\n{PRO_UI_RULES}\n\n"
        "Apply the palette as :root CSS variables, load the specified Google Fonts, follow the layout "
        "pattern, and make the result feel like a bespoke, high-converting, premium site — never templated."
    )


def available() -> bool:
    return _AVAILABLE
