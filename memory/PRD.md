# SiteGenie — Product Requirements Document

## Original Problem Statement
An online store that creates website templates for businesses that don't have a website. Subscription-based with Monthly, 3-Month, and Annual plans. The template generator works via Credits. Subscribers can purchase extra credits after hitting their plan limit.

## User Choices
- Generation: AI-powered (Claude Sonnet 4.6 via Emergent LLM key)
- Payments: Stripe (test key), subscriptions + credit packs
- Auth: BOTH email/password (bcrypt + session tokens) AND Emergent-managed Google login
- Credit limits: Monthly=20, 3-Month=75, Annual=160
- Business types: General

## Architecture
- Backend: FastAPI + MongoDB (motor). Emergent integrations for LLM & Stripe.
- Frontend: React 19 + Tailwind + framer-motion + shadcn. Dark Swiss/high-contrast theme.
- Auth: opaque session tokens in `user_sessions`, httpOnly `session_token` cookie (also Bearer).
- Generation: ASYNC JOB pattern (POST /generate returns job_id instantly; background task runs LLM; frontend polls /templates/job/{id}). This avoids ingress request timeouts since full-site generation takes ~60-120s.

## User Personas
- Small business owner with no website who wants a professional site fast.
- Freelancer/agency generating client sites quickly.

## Core Requirements (static)
- Subscription tiers granting monthly credits.
- 1 credit = 1 generated website.
- Buy extra credit packs anytime.
- AI generates full responsive branded HTML sites from a business description.
- Preview, view code, download HTML.

## Implemented (2026-07-02)
- Landing page (hero, features bento, how-it-works, pricing).
- Auth: register (3 free credits), login, logout, /me, Google OAuth callback flow.
- Dashboard: credits/plan/count stats, recent websites.
- AI Generator: business form -> async job -> live iframe preview; download/open.
- My Templates: list, view (desktop/mobile), code view, copy, download, delete.
- Pricing: 3 subscriptions + 3 credit packs, Stripe checkout redirect.
- Payment return: polls checkout status, grants credits/plan once.
- Stripe: /checkout/session, /checkout/status/{id}, /webhook/stripe, payment_transactions.
- Admin seed: admin@sitegenie.com / admin123.

## Implemented — P1 (2026-07-02, iter 2)
- Template Regenerate (fresh design, same details) + Edit-with-AI (natural-language change instructions). Each costs 1 credit. Async job pattern reused.
- Two-bucket credit model: plan_credits (resets to plan allowance every 30 days) + extra_credits (packs, never reset). Deduction: plan first, then extra.
- Subscription lifecycle: active/cancelled status, auto-renew (simulated), 30-day credit reset, cancel + reactivate. Lazy processing in get_current_user + hourly background worker.
- Billing page (/billing): plan status, dates, credit breakdown, cancel/reactivate, payment history.
- Plans updated to per-30-day allowances: Monthly 20/30d, 3-Month 25/30d, Annual 30/30d.

## Implemented — Iter 3-6 (2026-07-02)
- Rate limiting: login brute-force (5/15min per IP+email) + generation (15/5min per user).
- Native Stripe recurring subscriptions (mode=subscription, own test key): auto-create prices, checkout, cancel/reactivate via Stripe API, webhook /api/webhook/stripe-native for renewals (webhook secret pending registration).
- Security audit fixes: CORS allowlist, SameSite=Lax cookie, strong admin password, payment idempotency, iframe sandbox, credit floor.
- REWORKED credit system (usage-based currency): cost per AI op = max(1, round((prompt+output chars/4)/3000)). Plans: Monthly $20/50cr, 3-Month $49/120cr, Annual $149/UNLIMITED. plan_credits (30d reset) + extra_credits (packs). 402 block at 0 credits (non-unlimited); packs pack_25/60/150. New users get 15 free credits.

## Implemented — Publish / Hosting (2026-07-03)
- Publish templates to a shareable public URL. Backend: POST /api/templates/{id}/publish, /unpublish; templates gain `published`, `slug` (unique sparse index), `published_at`. MyTemplates "Live" badge; TemplateView Publish/Share dialog. Edits/regenerations update the live site automatically.

## Implemented — Backlog batch (2026-07-03)
- **ZIP export**: GET /api/templates/{id}/download-zip → zip of index.html + README.txt. TemplateView "Download" is now a menu (HTML file / ZIP).
- **Thumbnails**: MyTemplates cards show a LIVE scaled iframe preview (`SiteThumb`, lazy IntersectionObserver fetch of /templates/{id}).
- **Economy/Quality toggle**: GenerateInput `quality` ("quality"=2-pass Haiku→Sonnet default, "economy"=fast single-pass Haiku, fewer credits). Generator mode selector; regenerate reuses stored quality.
- **Backend refactor**: server.py (1150+ lines) split into config.py, database.py, models.py, security.py, services/{llm,billing}.py, routes/{auth,plans,templates,payments,subscriptions}.py. server.py now a thin orchestrator. All APIs unchanged. `_use_native_stripe`→`use_native_stripe`.
- **Vanity slug**: PUT /api/templates/{id}/slug (slugified, min 3 chars, 409 on clash, ownership-guarded). Editor in the Share dialog.
- **SEO / social meta (canonical public page)**: GET /api/p/{slug} serves the published site as REAL server-rendered HTML with injected og:title/description/image (auto-extracted from first Unsplash URL) + twitter card + CSP `connect-src 'none'`. This is the shareable URL (works with link-preview crawlers). `/s/{slug}` now redirects to `/api/p/{slug}`. JSON GET /api/public/site/{slug} retained.
- Verified: test_publish_flow.py, test_phase1.py, test_phase3.py, test_credit_system.py 16/16 + rate-limit regression; frontend agent iteration_7.json = 8/8 PASS.

## Backlog / Remaining
- P1: Regenerate/edit an existing template; custom section prompts. ✅ DONE (regenerate/edit).
- P1: Real recurring Stripe subscriptions. ✅ DONE (native Stripe, live mode).
- P2: Auto-expire plan + monthly credit reset job. ✅ DONE (lazy + hourly worker).
- P2: Publish/hosting. ✅ DONE. Remaining: **custom domain mapping** (needs DNS + per-domain TLS/ingress — not feasible in this env; delivered vanity slugs as the practical equivalent).
- P2: More export formats. ✅ ZIP done. (image/asset bundling N/A — sites use hosted assets.)
- P2: Cheaper/faster model toggle. ✅ DONE (Economy mode).
- P3 (new idea): auto-generated branded OG card image per published site (currently reuses the site's hero image).

## Notes
- LLM budget: each generation costs ~$0.12. Ensure Universal Key has adequate balance
  (Profile -> Universal Key -> Add Balance / auto top-up).
