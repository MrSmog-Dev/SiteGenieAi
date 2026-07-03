# SiteGenie — PRD

## Original Problem Statement
An online store that creates website templates for businesses without a website. Subscription-based (Monthly, 3-Month, Annual). Template generator works via credits; subscribers can purchase extra credits after hitting plan limits. Later additions: native Stripe subscriptions, usage-based credit model, Owner bypass role, multi-step Agentic AI pipeline, publishing/hosting with vanity URLs, SEO meta tags, branded OG images, ZIP exports.

## Users
- Small business owners without a website (primary)
- Owner/admin account with unlimited credits (bypass role)

## Architecture
- Frontend: React + Tailwind + Shadcn (dark, brand blue #0055FF, sharp-edged design system)
- Backend: FastAPI modular (`routes/`, `services/`, `models.py`, `config.py`, `security.py`), MongoDB (Motor)
- Auth: JWT email/password + Emergent Google Auth
- Payments: Stripe LIVE mode (native subscriptions + credit packs, webhooks)
- AI: Emergent LLM Key — Claude Sonnet 4.6 (Quality, 2-pass) / Haiku 4.5 (Economy)
- Publishing: vanity slugs `/api/p/{slug}`, server-rendered SEO HTML, Pillow OG cards `/api/og/{slug}.png`, ZIP export

## Implemented (history)
- 2026-05/06: Full MVP — auth, plans, generator, credits, Stripe subscriptions & packs, Owner role
- 2026-06: Agentic 2-pass pipeline + Economy/Quality toggle; backend modularization; publish flow with vanity slugs; SEO meta payload; branded OG card generator; ZIP export; live iframe thumbnails; pytest regression suites (test_phase1, test_phase3, test_publish_flow)
- 2026-06 (prod): User deployed to production at https://sitegenie.dev
- 2026-07-03: **Emergent-style chat-first landing page redesign** — centered hero with glowing prompt box, typewriter cycling placeholder, 6 suggestion chips (coffee/barber/fitness/restaurant/law/florist), Enter-to-start, personalized greeting for logged-in users, pricing/features kept below fold. Fixed stale "3 free credits" → 15 on Register page.
- 2026-07-03: **Chat-style follow-up flow on landing** (approved enhancement) — after typing an idea or picking a chip, the agent asks 2 scripted follow-ups (business name → brand vibe with 6 quick-select vibe chips or free text) in a chat thread with typing indicator, Skip and Start-over controls. Full brief stored as JSON in `sessionStorage.sg_pending_brief` {description, industry, business_name, brand_keywords, style} and pre-fills 5 Generator fields. Brief carried through email login/register AND Google OAuth callback into Generator; Login/Register show "brief saved" banners and route to `/generate` when a brief exists. Tested by testing agent: 8/8 scenarios pass (iteration_8.json).

## Known Issues / Blockers
- **P0 BLOCKED**: Emergent LLM Key budget exceeded ($3.00 cap hit) — `/api/generate/start` returns 500 until user tops up (Profile → Universal Key → Add Balance)
- Stripe is LIVE mode — be careful with test purchases

- 2026-07-03: **P2 Analytics counter** — non-bot views counted on `/api/p/{slug}` and domain-served pages (`views_total` + `views_daily` per date, bot UAs filtered by regex); `GET /api/templates/{id}/stats` returns totals + 14-day daily series; UI: views badge on My Websites cards, views chip in TemplateView header, total + 14-bar sparkline in share dialog. Tested: iteration_9.json 100% pass.
- 2026-07-03: **P3 Custom domain mapping** — `PUT/DELETE /api/templates/{id}/domain` (normalize + validate + uniqueness w/ unique sparse index), `POST .../domain/verify` (DNS A-record IP comparison vs app host), `GET /api/public/domain/{host}` public payload, host-based serving in App.js → DomainSite.jsx (foreign hostname renders published site full-screen). Share dialog UI: connect input, Pending DNS/Verified badges, CNAME instructions, verify + remove. NOTE: for production, arbitrary domains must also be routed by the hosting ingress (user may need Emergent support to attach domains to the deployment). Tested: iteration_9.json 100% pass.

## Backlog — ALL CLEAR (as of 2026-07-03)
- (user action) Top up Emergent LLM key, redeploy to production, validate live.

## Key Endpoints
- `POST /api/templates/generate` → job; poll job for template
- `POST /api/templates/{id}/publish`, `GET /api/p/{slug}`, `GET /api/og/{slug}.png`, `GET /api/templates/{id}/export`

## Test Credentials
See `/app/memory/test_credentials.md` (Owner: neobeyondlegacy2@gmail.com)
