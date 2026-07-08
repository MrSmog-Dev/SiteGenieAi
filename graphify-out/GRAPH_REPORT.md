# Graph Report - .  (2026-07-08)

## Corpus Check
- Large corpus: 216 files · ~998,414 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1523 nodes · 2238 edges · 176 communities (125 shown, 51 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 289 edges (avg confidence: 0.8)
- Token cost: 596,410 input · 0 output

## Community Hubs (Navigation)
- Frontend Runtime Dependencies
- AI Team Agent Memory & Chat Routes
- Flagship Template Build Pipeline
- Backend Auth/Subscription Test Suite
- Frontend Dependency Resolutions
- Auth: Login/Session/Google OAuth
- Template Market Tests
- AI Team Agent Roster (PRD)
- UI Carousel Component
- Native Stripe Subscriptions
- Team Management & Invites
- Customer Support (Halo Chat)
- Template CRUD Routes
- Sample Generated Landing Page
- Backend Pydantic Models
- Ivy SEO/GEO Engine
- Rate-Limit & Credit-Pack Tests
- Rex Lead Hunting & Outreach
- Blog Engine Routes
- Automation Loop (Outreach/Alerts)
- Rate-Limiting Test Suite
- UI-UX-Pro-Max Design System Generator
- War Room Team Orchestration
- Legacy backend_test.py Suite
- AI Team Chat Tests
- Analytics & Custom Domain Tests
- Iteration-16 Regression Tests
- Design System Formatting/Persistence
- shadcn/ui Component Config
- Market Checkout & Payments
- UI Menubar Component
- Credit System Tests
- Team Pulse Activity Feed
- Market Price/Model Tests (Iter 13)
- graphify /add & --watch Docs
- Frontend Dev Dependencies
- Server Bootstrap & Plans/Milestones
- Build Session Orchestration
- Agent Reply & Business Context
- SEO Center Page
- Owner Data Reset & Market Delist
- package.json Metadata
- Genie Waking Loader & API Client
- Backend Dependency Manifest
- UIUX Skill Core Search (BM25)
- Reset-Business-Data Tests
- UI Command Palette Component
- UI Context Menu Component
- UI Dropdown Menu Component
- Landing Page
- Blog Stock-Image Sourcing
- Premium Upgrade Tests
- BM25 Ranking Algorithm
- UI Alert Dialog Component
- UI Table Component
- Template Generate/Edit Routes
- OG Social Preview Card Generator
- Design Intelligence Service
- Auth Verification Tests
- UI Breadcrumb Component
- UI Drawer Component
- UI Navigation Menu Component
- UI Pagination Component
- UI Select Component
- UI Sheet Component
- UI Toast Component
- Generator Page
- Auth & Test Credentials Docs
- Webpack Health-Check Plugin
- App Shell & Router
- UI Card Component
- UI Dialog Component
- Auth Test-ID Constants
- Market Page
- Publish/Slug Routes
- Ownership Certificate PDF Generator
- UIUX Skill Page-Override Generation
- graphify Query/Extraction Reference Docs
- jsconfig Path Aliases
- UI Input-OTP Component
- Health-Check Endpoints
- Feedback Inbox Component
- Build Canvas Page
- Pricing Page
- Team Pulse Component
- UI Alert Component
- Template Details Update Route
- LLM Provider & 2-Pass Generation Pipeline
- Pricing/Billing Feature Notes (PRD)
- Ivy SEO Autopilot Tests
- graphify Skill Concepts
- CRACO Webpack Config
- Frontend Public Branding Assets
- UI Accordion Component
- UI Avatar Component
- UI Tabs Component
- UI Toggle Group Component
- Visual Editor Component
- Auth Context Provider
- Atlas Agent Avatar & Directory
- Visual Builder HTML Save Route
- UIUX Skill Search Formatting
- graphify Extraction Spec Rules
- UI Sonner Toast Component
- Agent Memory Component
- Dashboard Layout Component
- Halo Widget Component
- Rex Lead Panel Component
- UI Badge Component
- UI Button Component
- UI Label Component
- UI Radio Group Component
- UI Scroll Area Component
- UI Toggle Component
- War Room Component
- Frontend Entry Point
- Billing Page
- Policy Page
- UI Checkbox Component
- UI Hover Card Component
- UI Input Component
- UI Popover Component
- UI Progress Component
- UI Separator Component
- UI Slider Component
- UI Switch Component
- UI Textarea Component
- UI Tooltip Component
- Passlib Dependency
- Unresolved Node
- Blaze Agent Avatar
- Forge Agent Avatar
- Halo Agent Avatar
- Ivy Agent Avatar
- Ledger Agent Avatar
- Mara Agent Avatar
- Nova Agent Avatar
- Quill Agent Avatar
- Rex Agent Avatar
- Titan Agent Avatar
- Zephyr Agent Avatar
- SiteGenie Full Logo (Raw)
- SiteGenie Full Logo (Wordmark)
- SiteGenie Logo Mark
- CRA Bootstrap Docs
- Emergent Placeholder Doc

## God Nodes (most connected - your core abstractions)
1. `resolutions` - 42 edges
2. `_require_owner()` - 30 edges
3. `_call_llm()` - 30 edges
4. `log_activity()` - 26 edges
5. `/graphify command` - 19 edges
6. `post_agent_message()` - 18 edges
7. `run_war_room_meeting()` - 16 edges
8. `_run_generation()` - 15 edges
9. `_tick()` - 14 edges
10. `run_lead_demo()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)` --conceptually_related_to--> `Opaque Session Token Auth (user_sessions + httpOnly cookie)`  [AMBIGUOUS]
  memory/PRD.md → auth_testing.md
- `fastapi==0.110.1 dependency` --shares_data_with--> `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)`  [INFERRED]
  backend/requirements.txt → memory/PRD.md
- `motor (async MongoDB driver) dependency` --shares_data_with--> `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)`  [INFERRED]
  backend/requirements.txt → memory/PRD.md
- `pymongo dependency` --shares_data_with--> `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)`  [INFERRED]
  backend/requirements.txt → memory/PRD.md
- `openai==1.99.9 dependency` --shares_data_with--> `2-Pass Agentic Generation Pipeline (Quality Sonnet / Economy Haiku)`  [AMBIGUOUS]
  backend/requirements.txt → memory/PRD.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **AI Team — 12-agent roster** — memory_prd_ai_team, memory_prd_agent_titan, memory_prd_agent_nova, memory_prd_agent_atlas, memory_prd_agent_ledger, memory_prd_agent_quill, memory_prd_agent_ivy, memory_prd_agent_blaze, memory_prd_agent_mara, memory_prd_agent_rex, memory_prd_agent_halo, memory_prd_agent_forge, memory_prd_agent_zephyr [EXTRACTED 1.00]
- **Autonomous Automation Ecosystem (tick-driven agent actions)** — memory_prd_automation_loop, memory_prd_rex_autopilot, memory_prd_ivy_geo_sweep, memory_prd_payment_recovery, memory_prd_team_pulse [INFERRED 0.85]
- **graphify AST+Semantic Extraction Pipeline** — claude_skills_graphify_skill_extraction_pipeline, claude_skills_graphify_references_extraction_spec_subagent_prompt, claude_skills_graphify_skill_graph_report [EXTRACTED 1.00]

## Communities (176 total, 51 thin omitted)

### Community 0 - "Frontend Runtime Dependencies"
Cohesion: 0.04
Nodes (54): dependencies, axios, class-variance-authority, clsx, cmdk, cra-template, date-fns, dayjs (+46 more)

### Community 1 - "AI Team Agent Memory & Chat Routes"
Cohesion: 0.08
Nodes (49): AgentMemoryInput, add_agent_memory(), add_team_memory(), agent_activity_feed(), agent_job_status(), agent_status_board(), clear_agent_chat(), clear_war_room() (+41 more)

### Community 2 - "Flagship Template Build Pipeline"
Cohesion: 0.09
Nodes (43): build_flagship(), _design_context(), _extract(), _inject(), main(), Builds SiteGenie's 3 flagship Market templates targeting the $500 Premium grade., _sonnet(), _upgrade() (+35 more)

### Community 3 - "Backend Auth/Subscription Test Suite"
Cohesion: 0.06
Nodes (11): new_user(), SiteGenie backend API tests - Iteration 2. Focus: subscription lifecycle, credit, _register(), TestAuth, TestCheckout, TestCreditGating, TestCreditReset, TestPlans (+3 more)

### Community 4 - "Frontend Dependency Resolutions"
Cohesion: 0.05
Nodes (42): resolutions, **/anymatch/picomatch, **/axios/form-data, @babel/plugin-transform-modules-systemjs, **/cosmiconfig/yaml, **/css-loader/postcss, **/css-minimizer-webpack-plugin/postcss, **/cssnano/yaml (+34 more)

### Community 5 - "Auth: Login/Session/Google OAuth"
Cohesion: 0.12
Nodes (30): google_session(), login(), logout(), me(), Request, Response, register(), generation_status() (+22 more)

### Community 6 - "Template Market Tests"
Cohesion: 0.06
Nodes (12): buyer_client(), Tests for the Template Market feature (listings, ownership, checkout, free edits, Verify a purchased template bypasses credit gate on /edit and can export ZIP., Directly insert a purchased template into DB via a helper endpoint if available,, Sanity: non-purchased template with 0 credits should return 402., Directly simulate fulfill_market_purchase to prove buyer gets a copy with purcha, Register a fresh buyer user., TestFulfillmentSimulation (+4 more)

### Community 7 - "AI Team Agent Roster (PRD)"
Cohesion: 0.08
Nodes (32): google-generativeai dependency, Atlas — data agent, Blaze — social distribution agent, Forge — template builder/curator agent, Halo — support agent, Ivy — SEO/GEO agent, Ledger — finance agent, Mara — email agent (+24 more)

### Community 8 - "UI Carousel Component"
Cohesion: 0.08
Nodes (26): react, Carousel, CarouselContent, CarouselContext, CarouselItem, CarouselNext, CarouselPrevious, useCarousel() (+18 more)

### Community 9 - "Native Stripe Subscriptions"
Cohesion: 0.12
Nodes (17): Force stripe_sdk to talk directly to Stripe (not the emergent proxy).     Emerge, use_native_stripe(), cancel_subscription(), get_subscription(), Request, reactivate_subscription(), stripe_native_webhook(), subscription_checkout() (+9 more)

### Community 10 - "Team Management & Invites"
Cohesion: 0.12
Nodes (25): my_invites(), Team state for the Billing page (owner or member)., Pending invites addressed to me (to accept after signing up)., _require_team_owner(), team_accept(), team_account(), team_invite(), team_leave() (+17 more)

### Community 11 - "Customer Support (Halo Chat)"
Cohesion: 0.12
Nodes (22): delete_feedback(), list_feedback(), _now(), Request, Public customer support chat with Halo — no auth required., Owner-only Customer Feedback inbox with filters + summary counts., _require_owner(), support_chat() (+14 more)

### Community 12 - "Template CRUD Routes"
Cohesion: 0.13
Nodes (15): DomainInput, _count_view(), _inject_social_meta(), _normalize_domain(), ownership_certificate(), _public_base(), public_page(), public_site_by_domain() (+7 more)

### Community 13 - "Sample Generated Landing Page"
Cohesion: 0.08
Nodes (24): reportlab==4.2.5 dependency, About section (brand story + stats), Contact form section, FAQ accordion section, Hero section (headline/subheadline/CTA), Services section (4 disciplines grid), Testimonials section, Verdant & Vine — sample generated garden-design landing page (+16 more)

### Community 14 - "Backend Pydantic Models"
Cohesion: 0.17
Nodes (22): AgentChatInput, BuildMessageInput, CheckoutInput, FeedbackStatusInput, ForgeBuildInput, GeoAuditInput, GoogleSessionInput, LeadHuntInput (+14 more)

### Community 15 - "Ivy SEO/GEO Engine"
Cohesion: 0.17
Nodes (21): build_content_calendar(), gap_to_calendar(), geo_audit(), geo_trend(), get_calendar(), internal_link_map(), mark_topic_published(), next_planned_topic() (+13 more)

### Community 16 - "Rate-Limit & Credit-Pack Tests"
Cohesion: 0.10
Nodes (8): admin_client(), Tests for native Stripe recurring subscription integration. Covers: - POST /api/, 5 wrong pw from a fresh IP+email -> 6th returns 429., Register fresh user (3 credits) -> exhaust w/ 3 generates? No, just check with a, TestCreditPacksOldFlow, TestRegression, TestSubscriptionCheckout, _unique_ip()

### Community 17 - "Rex Lead Hunting & Outreach"
Cohesion: 0.18
Nodes (19): delete_lead(), draft_outreach(), hunt(), hunt_status(), list_leads(), _require_owner(), scan(), update_lead() (+11 more)

### Community 18 - "Blog Engine Routes"
Cohesion: 0.19
Nodes (16): blog_index(), blog_post(), blog_sitemap(), _host(), Request, _blaze_social_draft(), _page(), _parse_article() (+8 more)

### Community 19 - "Automation Loop (Outreach/Alerts)"
Cohesion: 0.21
Nodes (18): post_agent_message(), auto_demo_hot_leads(), auto_outreach_leads(), automation_loop(), Post-hunt automation: draft pitches for fresh leads, auto-demo the hottest ones, Alert the owner when a lead's demo site gets viewed (first view is silently abso, Daily pipeline hygiene: nudge on stale HOT leads, archive dead ones., Rex -> Forge handoff: auto-build and publish a pitch demo site for a contacted l (+10 more)

### Community 20 - "Rate-Limiting Test Suite"
Cohesion: 0.17
Nodes (6): Iteration 4 - Rate Limiting tests Covers:   (A) Login brute-force IP+email locko, _register_user(), TestGenerateRateLimit, TestLoginBruteForce, TestRegressionCore, _unique_ip()

### Community 21 - "UI-UX-Pro-Max Design System Generator"
Cohesion: 0.14
Nodes (11): DesignSystemGenerator, Find matching reasoning rule for a category., Apply reasoning rules to search results., Select best matching result based on priority keywords., Extract results list from search result dict., Generate complete design system recommendation.          variance/motion/density, Bucket a 1-10 dial value into its tier config. Returns None if value is None., Generates design system recommendations from aggregated searches. (+3 more)

### Community 22 - "War Room Team Orchestration"
Cohesion: 0.31
Nodes (17): start_war_room(), _agent_mem(), create_memo(), _create_tasks(), detect_and_route_memos(), _exec_forge(), _exec_ivy(), _exec_rex() (+9 more)

### Community 23 - "Legacy backend_test.py Suite"
Cohesion: 0.21
Nodes (17): log_test(), login(), main(), print_summary(), Test POST /api/subscription/checkout (monthly)., Test POST /api/subscription/checkout (annual)., Test POST /api/subscription/checkout with invalid plans., Test POST /api/checkout/session for credit packs. (+9 more)

### Community 24 - "AI Team Chat Tests"
Cohesion: 0.11
Nodes (5): AI Team feature backend tests, TestChat, TestForge, TestOwnerGating, TestRegression

### Community 25 - "Analytics & Custom Domain Tests"
Cohesion: 0.11
Nodes (4): Backend tests for P2 analytics and P3 custom domain features., TestAnalytics, TestCustomDomain, TestRegression

### Community 26 - "Iteration-16 Regression Tests"
Cohesion: 0.18
Nodes (13): _login_owner(), Iteration 16 — verify code-review fixes: FIX 1: /api/checkout/session subscripti, _register_throwaway(), test_agent_chat_slice_caps_at_200(), test_checkout_credits_pack25_ok(), test_checkout_rejects_subscription_kind(), test_concurrency_cap_429_and_own_job_deleted(), test_economy_passes_1_credit_gate() (+5 more)

### Community 27 - "Design System Formatting/Persistence"
Cohesion: 0.16
Nodes (17): ansi_ljust(), format_ascii_box(), format_markdown(), format_master_md(), generate_design_system(), hex_to_ansi(), persist_design_system(), Convert hex color to ANSI True Color swatch (██) with fallback. (+9 more)

### Community 28 - "shadcn/ui Component Config"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, iconLibrary, rsc (+9 more)

### Community 29 - "Market Checkout & Payments"
Cohesion: 0.18
Nodes (16): market_checkout(), market_preview(), market_purchase_status(), Request, checkout_status(), create_checkout(), Request, stripe_webhook() (+8 more)

### Community 30 - "UI Menubar Component"
Cohesion: 0.12
Nodes (10): Menubar, MenubarCheckboxItem, MenubarContent, MenubarItem, MenubarLabel, MenubarRadioItem, MenubarSeparator, MenubarSubContent (+2 more)

### Community 31 - "Credit System Tests"
Cohesion: 0.23
Nodes (13): estimate_cost(), _login_admin(), _me(), Backend tests for reworked usage-based credit system (iteration 6)., _register(), test_402_gating_zero_credits(), test_admin_login_and_me(), test_annual_unlimited_bypass() (+5 more)

### Community 32 - "Team Pulse Activity Feed"
Cohesion: 0.22
Nodes (15): _eligible_pulse_agent(), get_activity_feed(), get_status_board(), log_activity(), maybe_proactive_pulse(), _now(), Team Pulse — makes the AI Team feel alive.  Two responsibilities: 1. ACTIVITY LO, Pick an agent that is idle and hasn't self-posted recently (rotates naturally). (+7 more)

### Community 33 - "Market Price/Model Tests (Iter 13)"
Cohesion: 0.14
Nodes (6): admin(), _login(), owner(), Iteration 13 tests — market price override + generator model/quality., Verify /templates/generate accepts model + quality=economy, completes., test_generate_haiku_economy()

### Community 34 - "graphify /add & --watch Docs"
Cohesion: 0.14
Nodes (16): Graphify Skill Directive (.claude/CLAUDE.md), /graphify add <url>, --watch folder auto-rebuild, FalkorDB export, graphify MCP stdio server, Neo4j Cypher export, GitHub Clone + Cross-Repo Merge Flow, Native CLAUDE.md Integration (graphify claude install) (+8 more)

### Community 35 - "Frontend Dev Dependencies"
Cohesion: 0.12
Nodes (16): devDependencies, autoprefixer, @babel/plugin-proposal-private-property-in-object, @craco/craco, dotenv, @emergentbase/visual-edits, eslint, @eslint/js (+8 more)

### Community 36 - "Server Bootstrap & Plans/Milestones"
Cohesion: 0.16
Nodes (7): get_milestones(), _initialize(), _run_db_init(), startup(), ensure_automation_state(), Periodically process active subscriptions for credit resets and renewals., subscription_worker()

### Community 37 - "Build Session Orchestration"
Cohesion: 0.24
Nodes (11): build_attach(), build_message(), build_session(), attach_template(), create_session(), get_session(), handle_message(), _now() (+3 more)

### Community 38 - "Agent Reply & Business Context"
Cohesion: 0.22
Nodes (12): agent_reply(), business_snapshot(), _system_prompt(), team_memory_context(), leads_summary(), _kind_label(), _mara_recovery_draft(), _now() (+4 more)

### Community 39 - "SEO Center Page"
Cohesion: 0.19
Nodes (5): Calendar(), Geo(), Overview(), scoreColor(), TABS

### Community 40 - "Owner Data Reset & Market Delist"
Cohesion: 0.27
Nodes (10): Owner-only: wipe test users/revenue/jobs/AI-chat history for a true fresh start., reset_business_data(), delist_market(), list_on_market(), market_listings(), market_mine(), override_market_price(), Owner override — bypass the AI pricing agent and set a manual USD price. (+2 more)

### Community 41 - "package.json Metadata"
Cohesion: 0.17
Nodes (11): browserslist, development, production, name, packageManager, private, scripts, build (+3 more)

### Community 42 - "Genie Waking Loader & API Client"
Cohesion: 0.20
Nodes (5): GenieWaking(), api, checkApiHealth(), listeners, reportApiError()

### Community 43 - "Backend Dependency Manifest"
Cohesion: 0.18
Nodes (11): emergentintegrations==0.2.0 dependency, fastapi==0.110.1 dependency, motor (async MongoDB driver) dependency, PyJWT==2.13.0 dependency, pymongo dependency, Publish View Analytics Counter (views_total/views_daily), SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM), Custom Domain Mapping (DNS verify + host-based serving) (+3 more)

### Community 44 - "UIUX Skill Core Search (BM25)"
Cohesion: 0.25
Nodes (10): detect_domain(), _load_csv(), Load CSV and return list of dicts, Core search function using BM25, Auto-detect the most relevant domain from query, Main search function with auto-domain detection, Search stack-specific guidelines, search() (+2 more)

### Community 45 - "Reset-Business-Data Tests"
Cohesion: 0.27
Nodes (6): _login(), owner_session(), Tests for POST /api/auth/admin/reset-business-data (owner-only fresh-start)., _register(), test_non_owner_403(), test_reset_flow()

### Community 46 - "UI Command Palette Component"
Cohesion: 0.20
Nodes (7): Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator

### Community 47 - "UI Context Menu Component"
Cohesion: 0.20
Nodes (8): ContextMenuCheckboxItem, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuRadioItem, ContextMenuSeparator, ContextMenuSubContent, ContextMenuSubTrigger

### Community 48 - "UI Dropdown Menu Component"
Cohesion: 0.20
Nodes (8): DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuSubContent, DropdownMenuSubTrigger

### Community 49 - "Landing Page"
Cohesion: 0.22
Nodes (9): CHIPS, EXAMPLES, features, Landing(), PLACEHOLDERS, plans, STEP_HINTS, useTypewriter() (+1 more)

### Community 50 - "Blog Stock-Image Sourcing"
Cohesion: 0.33
Nodes (8): _figure(), _generate_image(), _openverse_search(), Free-to-use stock photos (CC-licensed) via Openverse, no API key., AI-generated illustration via Gemini Nano Banana (Emergent LLM key)., Replaces [IMAGE: description] markers with stored images (free stock first, AI f, resolve_article_images(), _store_image()

### Community 52 - "BM25 Ranking Algorithm"
Cohesion: 0.28
Nodes (5): BM25, BM25 ranking algorithm for text search, Lowercase, split, remove punctuation, filter short words, Build BM25 index from documents, Score all documents against query

### Community 53 - "UI Alert Dialog Component"
Cohesion: 0.22
Nodes (6): AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogOverlay, AlertDialogTitle

### Community 54 - "UI Table Component"
Cohesion: 0.22
Nodes (8): Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow

### Community 55 - "Template Generate/Edit Routes"
Cohesion: 0.25
Nodes (8): EditInput, GenerateInput, edit_template(), generate_template(), regenerate_template(), upgrade_template(), _min_cost(), _start_job()

### Community 56 - "OG Social Preview Card Generator"
Cohesion: 0.39
Nodes (7): og_card(), Auto-generated branded 1200x630 social preview card for a published site., _darken(), _fit_name(), _hex_to_rgb(), _mix(), render_og_png()

### Community 57 - "Design Intelligence Service"
Cohesion: 0.32
Nodes (6): _cached_spec(), design_directive(), design_spec_for(), Design Intelligence — SiteGenie's port of the UI-UX-Pro-Max skill.  Runs the ven, Build a design-system query from the business fields and return the skill's mark, The full design-intelligence block to inject into the builder prompt.

### Community 59 - "UI Breadcrumb Component"
Cohesion: 0.25
Nodes (5): Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage

### Community 60 - "UI Drawer Component"
Cohesion: 0.25
Nodes (4): DrawerContent, DrawerDescription, DrawerOverlay, DrawerTitle

### Community 61 - "UI Navigation Menu Component"
Cohesion: 0.25
Nodes (7): NavigationMenu, NavigationMenuContent, NavigationMenuIndicator, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle, NavigationMenuViewport

### Community 63 - "UI Select Component"
Cohesion: 0.25
Nodes (7): SelectContent, SelectItem, SelectLabel, SelectScrollDownButton, SelectScrollUpButton, SelectSeparator, SelectTrigger

### Community 64 - "UI Sheet Component"
Cohesion: 0.25
Nodes (5): SheetContent, SheetDescription, SheetOverlay, SheetTitle, sheetVariants

### Community 65 - "UI Toast Component"
Cohesion: 0.25
Nodes (7): Toast, ToastAction, ToastClose, ToastDescription, ToastTitle, toastVariants, ToastViewport

### Community 66 - "Generator Page"
Cohesion: 0.25
Nodes (5): DEFAULT_FORM, MODELS, STYLES, TIERS, VIBES

### Community 67 - "Auth & Test Credentials Docs"
Cohesion: 0.29
Nodes (7): Admin Test Credentials (admin@sitegenie.com), Google OAuth Test Flow (Mongo-seeded session), Protected Endpoints List (/api/templates, /api/checkout/*), Opaque Session Token Auth (user_sessions + httpOnly cookie), bcrypt==4.1.3 dependency, Credit-based Usage Model, Functional Code Review Fixes (billing leak, indexes, capped arrays)

### Community 69 - "App Shell & Router"
Cohesion: 0.29
Nodes (3): APP_HOSTS, backendHost, isEmergentHost

### Community 70 - "UI Card Component"
Cohesion: 0.29
Nodes (6): Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle

### Community 71 - "UI Dialog Component"
Cohesion: 0.29
Nodes (4): DialogContent, DialogDescription, DialogOverlay, DialogTitle

### Community 72 - "Auth Test-ID Constants"
Cohesion: 0.29
Nodes (4): LOGIN, LOGOUT, REGISTER, HOME

### Community 74 - "Publish/Slug Routes"
Cohesion: 0.33
Nodes (6): SlugInput, download_zip(), publish_template(), set_slug(), slugify(), unique_slug()

### Community 75 - "Ownership Certificate PDF Generator"
Cohesion: 0.40
Nodes (5): ownership_certificate_pdf(), build_certificate_pdf(), _center(), Ownership Certificate PDF generator (reportlab).  Produces a clean, branded 'Cer, cert: {title, owner_name, owner_email, price_usd, transferred_at (iso), cert_id}

### Community 76 - "UIUX Skill Page-Override Generation"
Cohesion: 0.33
Nodes (6): _detect_page_type(), format_page_override_md(), _generate_intelligent_overrides(), Format a page-specific override file with intelligent AI-generated content., Generate intelligent overrides based on page type using layered search., Detect page type from context and search results.

### Community 77 - "graphify Query/Extraction Reference Docs"
Cohesion: 0.33
Nodes (6): SiteGenie Project graphify Integration (top-level CLAUDE.md), BFS/DFS Traversal Modes, save-result Feedback Loop (work memory), Constrained Query Expansion Against Graph Vocabulary, SiteGenie Product (website-template generator), Testing Protocol (main/testing-agent communication format)

### Community 78 - "jsconfig Path Aliases"
Cohesion: 0.33
Nodes (5): compilerOptions, baseUrl, paths, include, @/*

### Community 79 - "UI Input-OTP Component"
Cohesion: 0.33
Nodes (5): input-otp, InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot

### Community 80 - "Health-Check Endpoints"
Cohesion: 0.47
Nodes (5): formatBytes(), formatDuration(), os, SERVER_START_TIME, setupHealthEndpoints()

### Community 81 - "Feedback Inbox Component"
Cohesion: 0.40
Nodes (5): ago(), FeedbackInbox(), KIND, SENTIMENT_DOT, STATUS_TABS

### Community 82 - "Build Canvas Page"
Cohesion: 0.33
Nodes (4): MODELS, STAGE_LABEL, STARTERS, TIERS

### Community 83 - "Pricing Page"
Cohesion: 0.33
Nodes (3): COMPARISON, PLAN_FEATURES, PLAN_ORDER

### Community 84 - "Team Pulse Component"
Cohesion: 0.50
Nodes (3): ActivityRow(), ago(), KIND_META

### Community 85 - "UI Alert Component"
Cohesion: 0.40
Nodes (4): Alert, AlertDescription, AlertTitle, alertVariants

### Community 86 - "Template Details Update Route"
Cohesion: 0.50
Nodes (4): Owner/buyer edits to a purchased or generated site's core details ("Make it your, TemplateDetailsInput, Make it yours' — update core business details on a site and reflect the safe one, update_template_details()

### Community 87 - "LLM Provider & 2-Pass Generation Pipeline"
Cohesion: 0.50
Nodes (4): litellm dependency, openai==1.99.9 dependency, 2-Pass Agentic Generation Pipeline (Quality Sonnet / Economy Haiku), LLM Call Timeout + Quality-to-Economy Fallback

### Community 88 - "Pricing/Billing Feature Notes (PRD)"
Cohesion: 0.50
Nodes (4): stripe==14.4.1 dependency, Pricing Rebuilt to Match Emergent (plans + top-ups), Team Multi-seat (shared credit pool), In-app Top-Up Modal

### Community 89 - "Ivy SEO Autopilot Tests"
Cohesion: 0.50
Nodes (3): Test Ivy SEO Autopilot backend endpoints. All endpoints are OWNER-GATED and requ, Test all Ivy SEO Autopilot endpoints with owner authentication., test_ivy_seo_endpoints()

### Community 90 - "graphify Skill Concepts"
Cohesion: 0.50
Nodes (4): Community Detection, AST + Semantic Extraction Pipeline, God Nodes, GRAPH_REPORT.md audit report

### Community 92 - "Frontend Public Branding Assets"
Cohesion: 0.50
Nodes (4): "Made with Emergent" badge, PostHog analytics integration, SiteGenie React app entry (index.html), Official SiteGenie Logo Branding

### Community 93 - "UI Accordion Component"
Cohesion: 0.50
Nodes (3): AccordionContent, AccordionItem, AccordionTrigger

### Community 94 - "UI Avatar Component"
Cohesion: 0.50
Nodes (3): Avatar, AvatarFallback, AvatarImage

### Community 95 - "UI Tabs Component"
Cohesion: 0.50
Nodes (3): TabsContent, TabsList, TabsTrigger

### Community 96 - "UI Toggle Group Component"
Cohesion: 0.50
Nodes (3): ToggleGroup, ToggleGroupContext, ToggleGroupItem

### Community 97 - "Visual Editor Component"
Cohesion: 0.67
Nodes (3): ADD_BLOCKS, injectRuntime(), VisualEditor()

### Community 99 - "Atlas Agent Avatar & Directory"
Cohesion: 1.00
Nodes (3): Atlas (AI Agent Persona), Atlas Agent Avatar, frontend/public/agents Directory

### Community 100 - "Visual Builder HTML Save Route"
Cohesion: 0.67
Nodes (3): HtmlSaveInput, Save edits from the visual (click-to-edit) builder. Owner of the template (incl., save_template_html()

### Community 102 - "graphify Extraction Spec Rules"
Cohesion: 0.67
Nodes (3): Discrete Confidence-Score Rubric (avoids 0.5 collapse), Deterministic Node ID Format Rule (full-path stem + entity), Extraction Subagent Prompt Spec

## Ambiguous Edges - Review These
- `Opaque Session Token Auth (user_sessions + httpOnly cookie)` → `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)`  [AMBIGUOUS]
  auth_testing.md · relation: conceptually_related_to
- `openai==1.99.9 dependency` → `2-Pass Agentic Generation Pipeline (Quality Sonnet / Economy Haiku)`  [AMBIGUOUS]
  backend/requirements.txt · relation: shares_data_with

## Knowledge Gaps
- **409 isolated node(s):** `$schema`, `style`, `rsc`, `tsx`, `config` (+404 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Opaque Session Token Auth (user_sessions + httpOnly cookie)` and `SiteGenie Architecture (React/Tailwind/Shadcn, FastAPI, MongoDB/Motor, Stripe, Emergent LLM)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `openai==1.99.9 dependency` and `2-Pass Agentic Generation Pipeline (Quality Sonnet / Economy Haiku)`?**
  _Edge tagged AMBIGUOUS (relation: shares_data_with) - confidence is low._
- **Why does `estimate_cost()` connect `Credit System Tests` to `Flagship Template Build Pipeline`, `Auth: Login/Session/Google OAuth`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Why does `dependencies` connect `Frontend Runtime Dependencies` to `UI Carousel Component`, `package.json Metadata`, `UI Sonner Toast Component`, `UI Input-OTP Component`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `_call_llm()` (e.g. with `build_flagship()` and `_sonnet()`) actually correct?**
  _`_call_llm()` has 25 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Builds SiteGenie's 3 flagship Market templates targeting the $500 Premium grade.`, `Force stripe_sdk to talk directly to Stripe (not the emergent proxy).     Emerge`, `One depth pass on listed flagships + reprice. Run: python deepen_flagships.py` to the rest of the system?**
  _549 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend Runtime Dependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.037037037037037035 - nodes in this community are weakly interconnected._