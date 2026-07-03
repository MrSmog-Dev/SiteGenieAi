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
SUBSCRIPTION_PLANS = {
    "monthly":   {"name": "Monthly",  "amount": 20.00,  "monthly_credits": 50,  "billing_days": 30,  "interval": "month",   "unlimited": False},
    "quarterly": {"name": "3-Month",  "amount": 49.00,  "monthly_credits": 120, "billing_days": 90,  "interval": "quarter", "unlimited": False},
    "annual":    {"name": "Annual",   "amount": 149.00, "monthly_credits": 300, "billing_days": 365, "interval": "year",    "unlimited": True},
}
CREDIT_RESET_DAYS = 30
CREDIT_PACKS = {
    "pack_25":  {"name": "Starter Pack", "amount": 9.00,  "credits": 25},
    "pack_60":  {"name": "Growth Pack",  "amount": 19.00, "credits": 60},
    "pack_150": {"name": "Pro Pack",     "amount": 39.00, "credits": 150},
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
