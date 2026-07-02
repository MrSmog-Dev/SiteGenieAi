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

## Backlog / Remaining
- P1: Regenerate/edit an existing template; custom section prompts.
- P1: Real recurring Stripe subscriptions (currently one-time checkouts that grant plan+credits with expiry).
- P2: Auto-expire plan + monthly credit reset job.
- P2: Custom domain / hosting/publish option.
- P2: More export formats (zip with assets), template thumbnails via screenshot.
- P2: Cheaper/faster model option (gemini-3-flash / claude-haiku) toggle to stretch credits.

## Notes
- LLM budget: each generation costs ~$0.12. Ensure Universal Key has adequate balance
  (Profile -> Universal Key -> Add Balance / auto top-up).
