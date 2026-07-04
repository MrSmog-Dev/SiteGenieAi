import re
import uuid
from datetime import datetime, timezone

from config import STRATEGY_MODEL, logger
from database import db
from services.agents import BASE_CONTEXT, post_agent_message
from services.llm import _call_llm

IVY_WRITER_SYSTEM = (
    "You are Ivy, SiteGenie's SEO specialist. You write ONE large, genuinely useful SEO article per day "
    f"for SiteGenie's blog.\n{BASE_CONTEXT}\n"
    "Audience: small-business owners searching Google for help with websites, online presence, templates "
    "and local marketing. Pick a FRESH topic with real search demand that is NOT in the existing list.\n"
    "Requirements: 1200-1800 words; structured with <h2> and <h3>; short paragraphs; bullet lists; a "
    "3-question FAQ section at the end; concrete, non-generic advice. Weave in 4-6 natural internal links "
    "with descriptive keyword-rich anchor text: <a href=\"/\">AI website builder</a>-style links to '/' "
    "(the SiteGenie builder), '/market' (premium website templates, $200-500, free unlimited edits), and "
    "'/pricing' (subscription plans). If related articles are provided, naturally link 1-2 of them via "
    "their /api/blog/<slug> path. Insert EXACTLY 3 image placeholders at natural break points, each on "
    "its own line in this exact format: [IMAGE: short vivid description of an ideal photo for that "
    "section] — the first one goes right after the opening paragraph. End the body with a short "
    "call-to-action paragraph inviting readers to build their site with SiteGenie.\n"
    "Output EXACTLY this format, nothing else:\n"
    "TITLE: <SEO title, max 60 chars>\n"
    "SLUG: <kebab-case-slug>\n"
    "DESCRIPTION: <meta description, max 155 chars>\n"
    "KEYWORDS: <5 comma-separated keywords>\n"
    "BODY:\n"
    "<article body HTML using only h2, h3, p, ul, ol, li, a, strong, em>"
)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:80] or f"post-{uuid.uuid4().hex[:6]}"


def _parse_article(raw: str) -> dict:
    def grab(field):
        m = re.search(rf"^{field}:\s*(.+)$", raw, re.M)
        return m.group(1).strip() if m else ""
    body = raw.split("BODY:", 1)[1].strip() if "BODY:" in raw else ""
    body = re.sub(r"^```(?:html)?|```$", "", body.strip(), flags=re.M).strip()
    body = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.I)
    if not body or len(body) < 500:
        raise ValueError("article body too short")
    return {"title": grab("TITLE")[:90] or "SiteGenie Blog",
            "slug": _slugify(grab("SLUG") or grab("TITLE")),
            "meta_description": grab("DESCRIPTION")[:160],
            "keywords": [k.strip() for k in grab("KEYWORDS").split(",") if k.strip()][:6],
            "body": body}


async def write_blog_post(owner_id: str | None = None) -> dict:
    existing = await db.blog_posts.find({}, {"_id": 0, "title": 1, "slug": 1}).sort(
        "created_at", -1).to_list(40)
    prompt = (
        f"Existing articles (do NOT repeat or overlap these topics): {[p['title'] for p in existing]}\n"
        f"Related articles you may interlink (title, slug): {[(p['title'], p['slug']) for p in existing[:6]]}\n"
        "Write today's article now in the exact output format."
    )
    raw = str(await _call_llm(prompt, IVY_WRITER_SYSTEM, STRATEGY_MODEL))
    art = _parse_article(raw)
    from services.blog_images import resolve_article_images
    art["body"] = await resolve_article_images(art["body"])
    slug = art["slug"]
    if await db.blog_posts.find_one({"slug": slug}, {"_id": 1}):
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    now = datetime.now(timezone.utc)
    post = {"post_id": f"post_{uuid.uuid4().hex[:12]}", "slug": slug, "title": art["title"],
            "meta_description": art["meta_description"], "keywords": art["keywords"],
            "body": art["body"], "author": "ivy", "created_at": now}
    await db.blog_posts.insert_one(dict(post))
    internal_links = art["body"].count("<a ")
    images_used = art["body"].count("<figure")
    if owner_id:
        await post_agent_message(owner_id, "ivy",
            f'Today\'s article is live: "{art["title"]}" — read it at /api/blog/{slug}. '
            f'Target keywords: {", ".join(art["keywords"][:3])}. {images_used} images embedded, '
            f"{internal_links} links pointing readers back to SiteGenie. Compounding content, one day at a time.")
        await _blaze_social_draft(owner_id, art["title"], slug, art["keywords"])
    logger.info("ivy published blog post '%s'", slug)
    return post


async def _blaze_social_draft(owner_id: str, title: str, slug: str, keywords: list):
    try:
        raw = await _call_llm(
            f'New SiteGenie blog article just published: "{title}" (path /api/blog/{slug}; keywords: '
            f'{", ".join(keywords)}). Write 2 ready-to-post promos: one X/Twitter post (<280 chars, strong '
            "hook) and one LinkedIn post (3-5 sentences, ends with the link path). Label them exactly "
            "'X:' and 'LINKEDIN:'. Max 2 hashtags total.",
            "You are Blaze, SiteGenie's high-energy social media manager. Punchy hooks, zero fluff.",
            STRATEGY_MODEL)
        await post_agent_message(owner_id, "blaze",
            f"Ivy just dropped a new article — today's distribution kit, ready to post:\n\n{str(raw).strip()}")
    except Exception:
        logger.exception("blaze social draft failed")


async def run_ivy_blog(owner_id: str):
    try:
        await write_blog_post(owner_id)
    except Exception:
        logger.exception("ivy blog automation failed")
        await post_agent_message(owner_id, "ivy",
            "I hit a problem publishing today's article. I'll retry tomorrow — or press "
            "'Write article now' to retry immediately.")


# ---------------- server-rendered blog pages ----------------

_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0B0E14;color:#E7EAF0;font-family:Georgia,'Times New Roman',serif;line-height:1.75}
.wrap{max-width:760px;margin:0 auto;padding:0 24px 80px}
header.site{border-bottom:1px solid rgba(255,255,255,.1);padding:18px 24px;display:flex;align-items:center;justify-content:space-between;font-family:Arial,Helvetica,sans-serif}
header.site .logo{color:#fff;text-decoration:none;font-weight:bold;font-size:18px;letter-spacing:-.5px}
header.site nav a{color:rgba(255,255,255,.65);text-decoration:none;font-size:14px;margin-left:22px}
header.site nav a:hover{color:#fff}
h1{font-size:38px;line-height:1.2;margin:48px 0 12px;letter-spacing:-.5px}
.meta{color:rgba(255,255,255,.45);font-size:14px;font-family:Arial,sans-serif;margin-bottom:36px}
article h2{font-size:26px;margin:40px 0 14px;letter-spacing:-.3px}
article h3{font-size:20px;margin:28px 0 10px}
article p{margin:0 0 18px;color:rgba(231,234,240,.88)}
article ul,article ol{margin:0 0 18px 24px}
article li{margin-bottom:8px;color:rgba(231,234,240,.88)}
article a{color:#7EA6FF}
.cta{margin:52px 0 0;border:1px solid rgba(126,166,255,.35);background:rgba(126,166,255,.07);padding:24px;font-family:Arial,sans-serif}
.cta a{display:inline-block;margin-top:12px;background:#3B6CFF;color:#fff;text-decoration:none;padding:12px 22px;font-size:14px}
.list-item{border-bottom:1px solid rgba(255,255,255,.08);padding:26px 0}
.list-item a.t{color:#fff;text-decoration:none;font-size:24px;letter-spacing:-.3px}
.list-item a.t:hover{color:#7EA6FF}
.list-item p{color:rgba(255,255,255,.55);margin-top:8px;font-size:15px}
.related{margin-top:56px;border-top:1px solid rgba(255,255,255,.1);padding-top:24px;font-family:Arial,sans-serif}
.related a{display:block;color:#7EA6FF;text-decoration:none;margin-bottom:10px;font-size:15px}
"""


def _page(title: str, description: str, canonical: str, body: str, extra_head: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{description}">
<meta property="og:type" content="article"><meta property="og:url" content="{canonical}">
{extra_head}
<style>{_CSS}</style>
</head>
<body>
<header class="site">
  <a class="logo" href="/">⚡ SiteGenie</a>
  <nav><a href="/api/blog">Blog</a><a href="/market">Template Market</a><a href="/pricing">Pricing</a><a href="/">Build a site</a></nav>
</header>
<div class="wrap">{body}</div>
</body>
</html>"""


def render_index(posts: list, host: str) -> str:
    items = "".join(
        f'<div class="list-item"><a class="t" href="/api/blog/{p["slug"]}">{p["title"]}</a>'
        f'<div class="meta" style="margin:6px 0 0">{p["created_at"].strftime("%B %d, %Y") if hasattr(p["created_at"], "strftime") else str(p["created_at"])[:10]}</div>'
        f'<p>{p.get("meta_description", "")}</p></div>'
        for p in posts) or '<p class="meta" style="margin-top:40px">First article drops soon — Ivy publishes daily.</p>'
    body = f"<h1>The SiteGenie Blog</h1><div class=\"meta\">Practical advice on websites, templates and getting found online — a new article every day.</div>{items}"
    return _page("The SiteGenie Blog — Websites, Templates & SEO for Small Business",
                 "Daily practical guides on AI website building, premium templates and small-business SEO from the SiteGenie team.",
                 f"https://{host}/api/blog", body)


def render_post(post: dict, related: list, host: str) -> str:
    date_str = post["created_at"].strftime("%B %d, %Y") if hasattr(post["created_at"], "strftime") else str(post["created_at"])[:10]
    related_html = ""
    if related:
        links = "".join(f'<a href="/api/blog/{r["slug"]}">→ {r["title"]}</a>' for r in related)
        related_html = f'<div class="related"><strong style="color:#fff">Keep reading</strong><div style="margin-top:12px">{links}</div></div>'
    cta = ('<div class="cta"><strong>Ready to get found online?</strong><br>'
           'Generate a complete website with the <a style="color:#7EA6FF" href="/">SiteGenie AI website builder</a> '
           'or own a <a style="color:#7EA6FF" href="/market">premium template</a> today.'
           '<br><a href="/">Build my website →</a></div>')
    schema = (f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article",'
              f'"headline":"{post["title"]}","datePublished":"{str(post["created_at"])[:10]}",'
              f'"author":{{"@type":"Organization","name":"SiteGenie"}}}}</script>')
    body = (f'<h1>{post["title"]}</h1><div class="meta">{date_str} · SiteGenie Team · '
            f'{", ".join(post.get("keywords", [])[:3])}</div><article>{post["body"]}</article>{cta}{related_html}')
    return _page(post["title"], post.get("meta_description", ""), f"https://{host}/api/blog/{post['slug']}",
                 body, extra_head=schema)


def render_sitemap(posts: list, host: str) -> str:
    urls = "".join(
        f"<url><loc>https://{host}/api/blog/{p['slug']}</loc><lastmod>{str(p['created_at'])[:10]}</lastmod></url>"
        for p in posts)
    return (f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>https://{host}/api/blog</loc></url>{urls}</urlset>')
