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
- ~~P0 BLOCKED: Emergent LLM Key budget exceeded~~ **RESOLVED 2026-07-03** — user topped up; verified end-to-end with owner login + `POST /api/templates/generate` returning 65KB HTML.
- Stripe is LIVE mode — be careful with test purchases
- Sonnet 4.6 (Quality mode) is flaky right now — sometimes returns in ~90s, sometimes stalls >4min. Mitigated 2026-07-03 with a 240s per-call timeout in `services/llm.py::_call_llm` that fails the job cleanly instead of hanging; Economy mode (single-pass Haiku) reliably completes in ~30-60s.

- 2026-07-03: **P2 Analytics counter** — non-bot views counted on `/api/p/{slug}` and domain-served pages (`views_total` + `views_daily` per date, bot UAs filtered by regex); `GET /api/templates/{id}/stats` returns totals + 14-day daily series; UI: views badge on My Websites cards, views chip in TemplateView header, total + 14-bar sparkline in share dialog. Tested: iteration_9.json 100% pass.
- 2026-07-03: **P3 Custom domain mapping** — `PUT/DELETE /api/templates/{id}/domain` (normalize + validate + uniqueness w/ unique sparse index), `POST .../domain/verify` (DNS A-record IP comparison vs app host), `GET /api/public/domain/{host}` public payload, host-based serving in App.js → DomainSite.jsx (foreign hostname renders published site full-screen). Share dialog UI: connect input, Pending DNS/Verified badges, CNAME instructions, verify + remove. NOTE: for production, arbitrary domains must also be routed by the hosting ingress (user may need Emergent support to attach domains to the deployment). Tested: iteration_9.json 100% pass.
- 2026-07-03: **LLM call timeout + graceful error surfacing** — added 240s `asyncio.wait_for` around every `_call_llm` in `services/llm.py` and taught `_fail_job` to recognize `asyncio.TimeoutError` and write a user-friendly "AI took too long, try again — Economy mode is faster" message to the job. Prevents jobs from hanging forever on Sonnet 4.6 stalls (E2E validated by main agent).
- 2026-06 (rendered 07-03): **Template Market** — public `/market` page selling pre-made templates at $200–$500, priced automatically by an **AI Pricing Agent** (`services/pricing_agent.py`: code-depth metrics + Haiku analysis → price/tier/summary/highlights; heuristic fallback if LLM unavailable). Owner-only listing (`POST /api/market/list`, sell/delist buttons in TemplateView + market page), one-time Stripe Checkout per template (`POST /api/market/{id}/checkout`, kind=market_purchase in payment_transactions, fulfilled via `apply_payment` → `services/market.py::fulfill_market_purchase`), buyer gets an editable copy with `purchased=true` → **FREE unlimited AI edits (credit check bypassed)** + ZIP export; "Most Popular" badge from views/purchases score; listing previews served at `GET /api/market/{id}/preview` (view-counted with `?count=1`, bot-filtered). Frontend: Market.jsx grid with live iframe thumbs, MarketSuccess.jsx post-checkout page, Owned badges in MyTemplates/TemplateView, Market nav in dashboard sidebar + landing. Tested: iteration_11.json 100% (17/17 backend, 7/7 frontend); pytest suite at backend/tests/test_market.py.

## Backlog
- **P0 (user action): Top up Emergent LLM key** — budget exhausted again mid-seeding (cost 5.25/5.0). Only 1 of 8 Market seed templates generated (Lumen Studio, $280). Re-run `cd /app/backend && python seed_market.py` after top-up to seed the remaining 7 (script is idempotent).
- (user action) Redeploy to production to ship the Template Market.
- P3: Weekly analytics email digest (Resend), Quality→Economy auto-fallback on timeout.

## Key Endpoints
- `POST /api/templates/generate` → job; poll job for template
- `POST /api/templates/{id}/publish`, `GET /api/p/{slug}`, `GET /api/og/{slug}.png`, `GET /api/templates/{id}/export`

## Test Credentials
See `/app/memory/test_credentials.md` (Owner: neobeyondlegacy2@gmail.com)
