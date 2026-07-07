#!/usr/bin/env python3
"""
Backend test for SiteGenie pricing/billing endpoints.
Tests the rebuilt pricing/billing backend that matches Emergent's structure.
"""
import requests
import time
import sys

# Configuration
BASE_URL = "https://5727d3a6-6e24-4861-baf5-bbf19c80f1e5.preview.emergentagent.com/api"
ORIGIN_URL = "https://5727d3a6-6e24-4861-baf5-bbf19c80f1e5.preview.emergentagent.com"
EMAIL = "neobeyondlegacy2@gmail.com"
PASSWORD = "OwnerGenie2025!"

# Test results tracking
test_results = []


def log_test(test_name, passed, details=""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = f"{status} - {test_name}"
    if details:
        result += f"\n    {details}"
    print(result)
    test_results.append({"name": test_name, "passed": passed, "details": details})


def login():
    """Login and return session."""
    print("\n=== AUTHENTICATION ===")
    session = requests.Session()
    
    # Try login
    resp = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    
    # Handle rate limiting
    if resp.status_code == 429:
        print("⚠️  Rate limited (429). Waiting 60 seconds and retrying...")
        time.sleep(60)
        resp = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    
    if resp.status_code == 200:
        log_test("Login", True, f"Successfully authenticated as {EMAIL}")
        return session
    else:
        log_test("Login", False, f"Status: {resp.status_code}, Response: {resp.text[:200]}")
        return None


def test_get_plans(session):
    """Test GET /api/plans endpoint."""
    print("\n=== TEST 1: GET /api/plans ===")
    
    # No auth needed for this endpoint
    resp = requests.get(f"{BASE_URL}/plans")
    
    if resp.status_code != 200:
        log_test("GET /api/plans - Status Code", False, f"Expected 200, got {resp.status_code}")
        return
    
    log_test("GET /api/plans - Status Code", True, "Returns 200")
    
    try:
        data = resp.json()
    except Exception as e:
        log_test("GET /api/plans - JSON Parse", False, f"Failed to parse JSON: {e}")
        return
    
    # Verify structure
    if "subscriptions" not in data or "credit_packs" not in data:
        log_test("GET /api/plans - Structure", False, f"Missing keys. Got: {list(data.keys())}")
        return
    
    log_test("GET /api/plans - Structure", True, "Has 'subscriptions' and 'credit_packs' keys")
    
    # Verify subscription plans
    subs = data["subscriptions"]
    expected_plans = ["free", "standard", "pro", "team"]
    
    for plan_id in expected_plans:
        if plan_id not in subs:
            log_test(f"GET /api/plans - Plan '{plan_id}'", False, f"Plan '{plan_id}' not found")
            continue
        
        plan = subs[plan_id]
        
        # Verify free plan
        if plan_id == "free":
            checks = [
                (plan.get("amount") == 0, "amount = 0"),
                (plan.get("monthly_credits") == 15, "monthly_credits = 15"),
                (plan.get("purchasable") == False, "purchasable = false"),
            ]
            for check, desc in checks:
                if not check:
                    log_test(f"GET /api/plans - Free plan {desc}", False, f"Got: {plan}")
                    break
            else:
                log_test(f"GET /api/plans - Free plan", True, "All values correct")
        
        # Verify standard plan
        elif plan_id == "standard":
            checks = [
                (plan.get("amount") == 20, "amount = 20"),
                (plan.get("annual_amount") == 17, "annual_amount = 17"),
                (plan.get("monthly_credits") == 50, "monthly_credits = 50"),
                (plan.get("annual_available") == True, "annual_available = true"),
            ]
            for check, desc in checks:
                if not check:
                    log_test(f"GET /api/plans - Standard plan {desc}", False, f"Got: {plan}")
                    break
            else:
                log_test(f"GET /api/plans - Standard plan", True, "All values correct")
        
        # Verify pro plan
        elif plan_id == "pro":
            checks = [
                (plan.get("amount") == 200, "amount = 200"),
                (plan.get("annual_amount") == 167, "annual_amount = 167"),
                (plan.get("monthly_credits") == 120, "monthly_credits = 120"),
            ]
            for check, desc in checks:
                if not check:
                    log_test(f"GET /api/plans - Pro plan {desc}", False, f"Got: {plan}")
                    break
            else:
                log_test(f"GET /api/plans - Pro plan", True, "All values correct")
        
        # Verify team plan
        elif plan_id == "team":
            checks = [
                (plan.get("amount") == 300, "amount = 300"),
                (plan.get("annual_amount") == 250, "annual_amount = 250"),
                (plan.get("monthly_credits") == 750, "monthly_credits = 750"),
                (plan.get("team_members") == 5, "team_members = 5"),
            ]
            for check, desc in checks:
                if not check:
                    log_test(f"GET /api/plans - Team plan {desc}", False, f"Got: {plan}")
                    break
            else:
                log_test(f"GET /api/plans - Team plan", True, "All values correct")
    
    # Verify credit packs
    packs = data["credit_packs"]
    expected_packs = {
        "pack_5": {"credits": 5, "amount": 1},
        "pack_100": {"credits": 100, "amount": 20},
        "pack_250": {"credits": 250, "amount": 50},
        "pack_500": {"credits": 500, "amount": 100},
        "pack_3000": {"credits": 3000, "amount": 500},
        "pack_6000": {"credits": 6000, "amount": 1000},
    }
    
    for pack_id, expected in expected_packs.items():
        if pack_id not in packs:
            log_test(f"GET /api/plans - Pack '{pack_id}'", False, f"Pack '{pack_id}' not found")
            continue
        
        pack = packs[pack_id]
        if pack.get("credits") == expected["credits"] and pack.get("amount") == expected["amount"]:
            log_test(f"GET /api/plans - Pack '{pack_id}'", True, 
                    f"{expected['credits']} credits / ${expected['amount']}")
        else:
            log_test(f"GET /api/plans - Pack '{pack_id}'", False, 
                    f"Expected {expected}, got credits={pack.get('credits')}, amount={pack.get('amount')}")


def test_subscription_checkout_monthly(session):
    """Test POST /api/subscription/checkout (monthly)."""
    print("\n=== TEST 2: POST /api/subscription/checkout (monthly) ===")
    
    payload = {
        "plan_id": "standard",
        "billing": "monthly",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/subscription/checkout", json=payload)
    
    if resp.status_code == 400 and "Invalid origin" in resp.text:
        log_test("Subscription Checkout (monthly) - CORS Origin", False, 
                f"Origin rejected: {ORIGIN_URL}. Response: {resp.text}")
        return
    
    if resp.status_code >= 500:
        log_test("Subscription Checkout (monthly) - Server Error", False, 
                f"Status: {resp.status_code}, Response: {resp.text[:300]}")
        return
    
    if resp.status_code != 200:
        log_test("Subscription Checkout (monthly) - Status Code", False, 
                f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}")
        return
    
    log_test("Subscription Checkout (monthly) - Status Code", True, "Returns 200")
    
    try:
        data = resp.json()
    except Exception as e:
        log_test("Subscription Checkout (monthly) - JSON Parse", False, f"Failed to parse JSON: {e}")
        return
    
    if "url" not in data or "session_id" not in data:
        log_test("Subscription Checkout (monthly) - Response Keys", False, 
                f"Missing 'url' or 'session_id'. Got: {list(data.keys())}")
        return
    
    log_test("Subscription Checkout (monthly) - Response Keys", True, 
            "Has 'url' and 'session_id'")
    
    url = data.get("url", "")
    if url.startswith("https://checkout.stripe.com") or url.startswith("https://"):
        log_test("Subscription Checkout (monthly) - Stripe URL", True, 
                f"Valid Stripe checkout URL returned")
    else:
        log_test("Subscription Checkout (monthly) - Stripe URL", False, 
                f"URL doesn't look like Stripe checkout: {url[:100]}")


def test_subscription_checkout_annual(session):
    """Test POST /api/subscription/checkout (annual)."""
    print("\n=== TEST 3: POST /api/subscription/checkout (annual) ===")
    
    payload = {
        "plan_id": "pro",
        "billing": "annual",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/subscription/checkout", json=payload)
    
    if resp.status_code >= 500:
        log_test("Subscription Checkout (annual) - Server Error", False, 
                f"Status: {resp.status_code}, Response: {resp.text[:300]}")
        return
    
    if resp.status_code != 200:
        log_test("Subscription Checkout (annual) - Status Code", False, 
                f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}")
        return
    
    log_test("Subscription Checkout (annual) - Status Code", True, "Returns 200")
    
    try:
        data = resp.json()
    except Exception as e:
        log_test("Subscription Checkout (annual) - JSON Parse", False, f"Failed to parse JSON: {e}")
        return
    
    if "url" in data and "session_id" in data:
        log_test("Subscription Checkout (annual) - Response", True, 
                "Returns Stripe checkout URL for annual billing (167*12 charged yearly)")
    else:
        log_test("Subscription Checkout (annual) - Response", False, 
                f"Missing 'url' or 'session_id'. Got: {list(data.keys())}")


def test_invalid_plan_checkout(session):
    """Test POST /api/subscription/checkout with invalid plans."""
    print("\n=== TEST 4: POST /api/subscription/checkout (invalid plans) ===")
    
    # Test 1: Free plan (not purchasable)
    payload = {
        "plan_id": "free",
        "billing": "monthly",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/subscription/checkout", json=payload)
    
    if resp.status_code == 400:
        log_test("Invalid Plan - Free plan", True, "Returns 400 (free is not purchasable)")
    else:
        log_test("Invalid Plan - Free plan", False, 
                f"Expected 400, got {resp.status_code}. Response: {resp.text[:200]}")
    
    # Test 2: Bogus plan
    payload = {
        "plan_id": "bogus",
        "billing": "monthly",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/subscription/checkout", json=payload)
    
    if resp.status_code == 400:
        log_test("Invalid Plan - Bogus plan", True, "Returns 400 (invalid plan)")
    else:
        log_test("Invalid Plan - Bogus plan", False, 
                f"Expected 400, got {resp.status_code}. Response: {resp.text[:200]}")


def test_credit_pack_checkout(session):
    """Test POST /api/checkout/session for credit packs."""
    print("\n=== TEST 5: POST /api/checkout/session (credit packs) ===")
    
    # Test pack_500
    payload = {
        "kind": "credits",
        "plan_id": "pack_500",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/checkout/session", json=payload)
    
    if resp.status_code >= 500:
        log_test("Credit Pack Checkout (pack_500) - Server Error", False, 
                f"Status: {resp.status_code}, Response: {resp.text[:300]}")
    elif resp.status_code != 200:
        log_test("Credit Pack Checkout (pack_500) - Status Code", False, 
                f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}")
    else:
        log_test("Credit Pack Checkout (pack_500) - Status Code", True, "Returns 200")
        
        try:
            data = resp.json()
            if "url" in data and "session_id" in data:
                log_test("Credit Pack Checkout (pack_500) - Response", True, 
                        "Returns Stripe checkout URL for pack_500 (500 credits / $100)")
            else:
                log_test("Credit Pack Checkout (pack_500) - Response", False, 
                        f"Missing 'url' or 'session_id'. Got: {list(data.keys())}")
        except Exception as e:
            log_test("Credit Pack Checkout (pack_500) - JSON Parse", False, f"Failed to parse JSON: {e}")
    
    # Test pack_5
    payload = {
        "kind": "credits",
        "plan_id": "pack_5",
        "origin_url": ORIGIN_URL
    }
    
    resp = session.post(f"{BASE_URL}/checkout/session", json=payload)
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            if "url" in data and "session_id" in data:
                log_test("Credit Pack Checkout (pack_5) - Response", True, 
                        "Returns Stripe checkout URL for pack_5 (5 credits / $1)")
            else:
                log_test("Credit Pack Checkout (pack_5) - Response", False, 
                        f"Missing 'url' or 'session_id'. Got: {list(data.keys())}")
        except Exception as e:
            log_test("Credit Pack Checkout (pack_5) - JSON Parse", False, f"Failed to parse JSON: {e}")
    else:
        log_test("Credit Pack Checkout (pack_5) - Status Code", False, 
                f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}")


def test_get_subscription(session):
    """Test GET /api/subscription."""
    print("\n=== TEST 6: GET /api/subscription ===")
    
    resp = session.get(f"{BASE_URL}/subscription")
    
    if resp.status_code != 200:
        log_test("GET /api/subscription - Status Code", False, 
                f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}")
        return
    
    log_test("GET /api/subscription - Status Code", True, "Returns 200")
    
    try:
        data = resp.json()
    except Exception as e:
        log_test("GET /api/subscription - JSON Parse", False, f"Failed to parse JSON: {e}")
        return
    
    # Verify expected keys
    expected_keys = ["status", "plan_credits", "extra_credits", "invoices"]
    missing_keys = [k for k in expected_keys if k not in data]
    
    if missing_keys:
        log_test("GET /api/subscription - Response Keys", False, 
                f"Missing keys: {missing_keys}. Got: {list(data.keys())}")
    else:
        log_test("GET /api/subscription - Response Keys", True, 
                f"Has all expected keys: status, plan_credits, extra_credits, invoices")
    
    # Log current subscription state
    status = data.get("status", "unknown")
    plan = data.get("plan", "none")
    plan_credits = data.get("plan_credits", 0)
    extra_credits = data.get("extra_credits", 0)
    
    log_test("GET /api/subscription - Current State", True, 
            f"Status: {status}, Plan: {plan}, Plan Credits: {plan_credits}, Extra Credits: {extra_credits}")


def print_summary():
    """Print test summary."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in test_results if r["passed"])
    failed = sum(1 for r in test_results if not r["passed"])
    total = len(test_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    
    if failed > 0:
        print("\n--- FAILED TESTS ---")
        for r in test_results:
            if not r["passed"]:
                print(f"❌ {r['name']}")
                if r["details"]:
                    print(f"   {r['details']}")
    
    print("\n" + "="*60)
    
    return failed == 0


def main():
    """Run all tests."""
    print("="*60)
    print("SITEGENIE PRICING/BILLING BACKEND TEST")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Origin: {ORIGIN_URL}")
    print(f"Test User: {EMAIL}")
    
    # Login
    session = login()
    if not session:
        print("\n❌ CRITICAL: Login failed. Cannot proceed with tests.")
        sys.exit(1)
    
    # Run tests
    test_get_plans(session)
    test_subscription_checkout_monthly(session)
    test_subscription_checkout_annual(session)
    test_invalid_plan_checkout(session)
    test_credit_pack_checkout(session)
    test_get_subscription(session)
    
    # Print summary
    success = print_summary()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
