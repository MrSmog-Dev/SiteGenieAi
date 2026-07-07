from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

import os
import logging
import stripe as stripe_sdk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sitegenie")

# ---------------- Secrets / env ----------------
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
STRIPE_API_KEY = os.environ['STRIPE_API_KEY']
OWNER_EMAIL = os.environ.get('OWNER_EMAIL', '').lower().strip()
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_IDS = {
    "monthly": os.environ.get('STRIPE_PRICE_MONTHLY', ''),
    "quarterly": os.environ.get('STRIPE_PRICE_QUARTERLY', ''),
    "annual": os.environ.get('STRIPE_PRICE_ANNUAL', ''),
}
if STRIPE_SECRET_KEY:
    stripe_sdk.api_key = STRIPE_SECRET_KEY

STRIPE_NATIVE_API_BASE = "https://api.stripe.com"

def use_native_stripe():
    """Force stripe_sdk to talk directly to Stripe (not the emergent proxy).
    Emergent's StripeCheckout mutates the global stripe.api_base when
    STRIPE_API_KEY contains 'sk_test_emergent', which would otherwise break
    native subscription/customer calls that rely on the user's own Stripe key."""
    stripe_sdk.api_base = STRIPE_NATIVE_API_BASE
    if STRIPE_SECRET_KEY:
        stripe_sdk.api_key = STRIPE_SECRET_KEY

# ---------------- Business config ----------------
# Emergent-style plans: Free / Standard / Pro / Team, with monthly + annual (~15% off) pricing.
# amount = monthly price; annual_amount = per-MONTH price when billed annually (charged x12).
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free", "amount": 0.00, "annual_amount": 0.00,
        "monthly_credits": 15, "billing_days": 30, "interval": "month",
        "unlimited": False, "team_members": 1, "purchasable": False, "annual_available": False,
        "tagline": "Try SiteGenie and generate your first site.",
    },
    "standard": {
        "name": "Standard", "amount": 20.00, "annual_amount": 17.00,
        "monthly_credits": 50, "billing_days": 30, "interval": "month",
        "unlimited": False, "team_members": 1, "purchasable": True, "annual_available": True,
        "tagline": "For solo founders shipping a real website.",
    },
    "pro": {
        "name": "Pro", "amount": 200.00, "annual_amount": 167.00,
        "monthly_credits": 120, "billing_days": 30, "interval": "month",
        "unlimited": False, "team_members": 1, "purchasable": True, "annual_available": True,
        "tagline": "For power users building & selling many sites.",
    },
    "team": {
        "name": "Team", "amount": 300.00, "annual_amount": 250.00,
        "monthly_credits": 750, "billing_days": 30, "interval": "month",
        "unlimited": False, "team_members": 5, "purchasable": True, "annual_available": True,
        "tagline": "Shared credits for a whole team (up to 5).",
    },
}
# New signups get 15 credits once (kept). Plan monthly_credits reset every billing cycle.
CREDIT_RESET_DAYS = 30
# Top-up packs (one-time, never expire) — mirrors Emergent's tiers.
CREDIT_PACKS = {
    "pack_5":    {"name": "Starter",   "amount": 1.00,    "credits": 5,    "note": "Intro offer"},
    "pack_100":  {"name": "Standard",  "amount": 20.00,   "credits": 100,  "note": ""},
    "pack_250":  {"name": "Builder",   "amount": 50.00,   "credits": 250,  "note": ""},
    "pack_500":  {"name": "Popular",   "amount": 100.00,  "credits": 500,  "note": "Most popular"},
    "pack_3000": {"name": "Best value","amount": 500.00,  "credits": 3000, "note": "20% bonus"},
    "pack_6000": {"name": "Enterprise","amount": 1000.00, "credits": 6000, "note": "20% off"},
}
# Usage-based metering: credits are a currency consumed per AI operation based on
# the amount of work (tokens processed), similar to Emergent's own credit system.
TOKENS_PER_CREDIT = 3000
MIN_OPERATION_COST = 1

# ---------------- Rate limiting ----------------
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
GEN_MAX_PER_WINDOW = 15
GEN_WINDOW_SECONDS = 5 * 60

# ---------------- Generation models (Claude agent: strategist -> builder) ----------------
STRATEGY_MODEL = "claude-haiku-4-5"
BUILD_MODEL = "claude-sonnet-4-6"
