#!/usr/bin/env python3
"""
Backend test for SiteGenie Team multi-seat + top-up checkout functionality.
Tests all Team endpoints and credit pack checkout as specified in the review request.
"""
import requests
import uuid
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://5727d3a6-6e24-4861-baf5-bbf19c80f1e5.preview.emergentagent.com/api"
ORIGIN_URL = "https://5727d3a6-6e24-4861-baf5-bbf19c80f1e5.preview.emergentagent.com"

def log(msg):
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def generate_test_email():
    """Generate unique test email."""
    random_id = uuid.uuid4().hex[:8]
    return f"owner@t{random_id}.com", f"member@t{random_id}.com"

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
    
    def add_pass(self, test_name):
        self.passed.append(test_name)
        log(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name, reason):
        self.failed.append((test_name, reason))
        log(f"❌ FAIL: {test_name} - {reason}")
    
    def summary(self):
        log("\n" + "="*80)
        log("TEST SUMMARY")
        log("="*80)
        log(f"Total Passed: {len(self.passed)}")
        log(f"Total Failed: {len(self.failed)}")
        if self.failed:
            log("\nFailed Tests:")
            for test_name, reason in self.failed:
                log(f"  ❌ {test_name}: {reason}")
        log("="*80)

def test_1_register_users(results):
    """TEST 1: Register two fresh users via POST /api/auth/register"""
    log("\n--- TEST 1: Register Two Users ---")
    
    owner_email, member_email = generate_test_email()
    log(f"Generated emails: owner={owner_email}, member={member_email}")
    
    # Register userA (owner)
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test Owner",
            "email": owner_email,
            "password": "TestPass123!",
            "consent": True
        }, timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("Register userA", f"Status {resp.status_code}: {resp.text}")
            return None, None, None, None
        
        data = resp.json()
        if "user_id" not in data:
            results.add_fail("Register userA", f"Missing user_id in response: {data}")
            return None, None, None, None
        
        # Extract session cookie
        cookie_a = resp.cookies.get("session_token")
        if not cookie_a:
            results.add_fail("Register userA", "No session_token cookie returned")
            return None, None, None, None
        
        results.add_pass("Register userA")
        log(f"UserA registered: {data.get('email')}, user_id={data.get('user_id')}")
        
    except Exception as e:
        results.add_fail("Register userA", str(e))
        return None, None, None, None
    
    # Register userB (member)
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test Member",
            "email": member_email,
            "password": "TestPass123!",
            "consent": True
        }, timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("Register userB", f"Status {resp.status_code}: {resp.text}")
            return owner_email, cookie_a, None, None
        
        data = resp.json()
        if "user_id" not in data:
            results.add_fail("Register userB", f"Missing user_id in response: {data}")
            return owner_email, cookie_a, None, None
        
        # Extract session cookie
        cookie_b = resp.cookies.get("session_token")
        if not cookie_b:
            results.add_fail("Register userB", "No session_token cookie returned")
            return owner_email, cookie_a, None, None
        
        results.add_pass("Register userB")
        log(f"UserB registered: {data.get('email')}, user_id={data.get('user_id')}")
        
    except Exception as e:
        results.add_fail("Register userB", str(e))
        return owner_email, cookie_a, None, None
    
    return owner_email, cookie_a, member_email, cookie_b

def test_2_non_team_state(results, cookie_a):
    """TEST 2: GET /api/team-account should return is_team=false for non-team user"""
    log("\n--- TEST 2: Non-Team State ---")
    
    if not cookie_a:
        results.add_fail("Non-team state", "No cookie_a available")
        return
    
    try:
        resp = requests.get(f"{BASE_URL}/team-account", 
                           cookies={"session_token": cookie_a}, 
                           timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("GET /api/team-account", f"Status {resp.status_code}: {resp.text}")
            return
        
        data = resp.json()
        if data.get("is_team") != False:
            results.add_fail("GET /api/team-account", f"Expected is_team=false, got {data}")
            return
        
        results.add_pass("GET /api/team-account (non-team)")
        log(f"Response: {json.dumps(data, indent=2)}")
        
    except Exception as e:
        results.add_fail("GET /api/team-account", str(e))
    
    # Also test GET /api/team-account/invites
    try:
        resp = requests.get(f"{BASE_URL}/team-account/invites", 
                           cookies={"session_token": cookie_a}, 
                           timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("GET /api/team-account/invites", f"Status {resp.status_code}: {resp.text}")
            return
        
        data = resp.json()
        if "invites" not in data or data["invites"] != []:
            results.add_fail("GET /api/team-account/invites", f"Expected empty invites, got {data}")
            return
        
        results.add_pass("GET /api/team-account/invites (empty)")
        log(f"Response: {json.dumps(data, indent=2)}")
        
    except Exception as e:
        results.add_fail("GET /api/team-account/invites", str(e))

def test_3_owner_guard(results, cookie_a):
    """TEST 3: POST /api/team-account/invite should return 403 for non-team owner"""
    log("\n--- TEST 3: Owner Guard (403 for non-team owner) ---")
    
    if not cookie_a:
        results.add_fail("Owner guard", "No cookie_a available")
        return
    
    try:
        resp = requests.post(f"{BASE_URL}/team-account/invite", 
                            json={"email": "x@y.com"},
                            cookies={"session_token": cookie_a}, 
                            timeout=10)
        
        if resp.status_code != 403:
            results.add_fail("POST /api/team-account/invite (non-owner)", 
                           f"Expected 403, got {resp.status_code}: {resp.text}")
            return
        
        results.add_pass("POST /api/team-account/invite (403 for non-owner)")
        log(f"Response: {resp.status_code} - {resp.json()}")
        
    except Exception as e:
        results.add_fail("POST /api/team-account/invite", str(e))

def test_4_top_up_checkout(results, cookie_a):
    """TEST 4: POST /api/checkout/session for credit packs"""
    log("\n--- TEST 4: Top-Up Checkout ---")
    
    if not cookie_a:
        results.add_fail("Top-up checkout", "No cookie_a available")
        return
    
    # Test pack_500
    try:
        resp = requests.post(f"{BASE_URL}/checkout/session", 
                            json={
                                "kind": "credits",
                                "plan_id": "pack_500",
                                "origin_url": ORIGIN_URL
                            },
                            cookies={"session_token": cookie_a}, 
                            timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("POST /api/checkout/session (pack_500)", 
                           f"Status {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            if "url" not in data or "session_id" not in data:
                results.add_fail("POST /api/checkout/session (pack_500)", 
                               f"Missing url or session_id: {data}")
            else:
                results.add_pass("POST /api/checkout/session (pack_500)")
                log(f"Response: url={data['url'][:50]}..., session_id={data['session_id']}")
        
    except Exception as e:
        results.add_fail("POST /api/checkout/session (pack_500)", str(e))
    
    # Test pack_5
    try:
        resp = requests.post(f"{BASE_URL}/checkout/session", 
                            json={
                                "kind": "credits",
                                "plan_id": "pack_5",
                                "origin_url": ORIGIN_URL
                            },
                            cookies={"session_token": cookie_a}, 
                            timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("POST /api/checkout/session (pack_5)", 
                           f"Status {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            if "url" not in data or "session_id" not in data:
                results.add_fail("POST /api/checkout/session (pack_5)", 
                               f"Missing url or session_id: {data}")
            else:
                results.add_pass("POST /api/checkout/session (pack_5)")
                log(f"Response: url={data['url'][:50]}..., session_id={data['session_id']}")
        
    except Exception as e:
        results.add_fail("POST /api/checkout/session (pack_5)", str(e))
    
    # Test invalid plan_id
    try:
        resp = requests.post(f"{BASE_URL}/checkout/session", 
                            json={
                                "kind": "credits",
                                "plan_id": "pack_bogus",
                                "origin_url": ORIGIN_URL
                            },
                            cookies={"session_token": cookie_a}, 
                            timeout=10)
        
        if resp.status_code != 400:
            results.add_fail("POST /api/checkout/session (invalid plan)", 
                           f"Expected 400, got {resp.status_code}: {resp.text}")
        else:
            results.add_pass("POST /api/checkout/session (invalid plan returns 400)")
            log(f"Response: {resp.status_code} - {resp.json()}")
        
    except Exception as e:
        results.add_fail("POST /api/checkout/session (invalid plan)", str(e))

def test_5_plans(results):
    """TEST 5: GET /api/plans should return credit_packs and subscriptions"""
    log("\n--- TEST 5: Plans Endpoint ---")
    
    try:
        resp = requests.get(f"{BASE_URL}/plans", timeout=10)
        
        if resp.status_code != 200:
            results.add_fail("GET /api/plans", f"Status {resp.status_code}: {resp.text}")
            return
        
        data = resp.json()
        
        # Check credit_packs
        if "credit_packs" not in data:
            results.add_fail("GET /api/plans", "Missing credit_packs key")
            return
        
        credit_packs = data["credit_packs"]
        expected_packs = ["pack_5", "pack_100", "pack_250", "pack_500", "pack_3000", "pack_6000"]
        
        for pack_id in expected_packs:
            if pack_id not in credit_packs:
                results.add_fail("GET /api/plans", f"Missing credit pack: {pack_id}")
                return
        
        results.add_pass("GET /api/plans (credit_packs has 6 tiers)")
        log(f"Credit packs: {list(credit_packs.keys())}")
        
        # Check subscriptions
        if "subscriptions" not in data:
            results.add_fail("GET /api/plans", "Missing subscriptions key")
            return
        
        subscriptions = data["subscriptions"]
        
        # Find team plan
        if "team" not in subscriptions:
            results.add_fail("GET /api/plans", "Team plan not found in subscriptions")
            return
        
        team_plan = subscriptions["team"]
        
        # Verify team plan details
        if team_plan.get("amount") != 300:
            results.add_fail("GET /api/plans", f"Team plan amount should be 300, got {team_plan.get('amount')}")
            return
        
        if team_plan.get("monthly_credits") != 750:
            results.add_fail("GET /api/plans", f"Team plan monthly_credits should be 750, got {team_plan.get('monthly_credits')}")
            return
        
        if team_plan.get("team_members") != 5:
            results.add_fail("GET /api/plans", f"Team plan team_members should be 5, got {team_plan.get('team_members')}")
            return
        
        results.add_pass("GET /api/plans (team plan verified)")
        log(f"Team plan: amount={team_plan.get('amount')}, monthly_credits={team_plan.get('monthly_credits')}, team_members={team_plan.get('team_members')}")
        
    except Exception as e:
        results.add_fail("GET /api/plans", str(e))

def test_6_invalid_accept(results, cookie_b):
    """TEST 6: POST /api/team-account/accept/inv_nonexistent should return 400"""
    log("\n--- TEST 6: Invalid Accept ---")
    
    if not cookie_b:
        results.add_fail("Invalid accept", "No cookie_b available")
        return
    
    try:
        resp = requests.post(f"{BASE_URL}/team-account/accept/inv_nonexistent", 
                            cookies={"session_token": cookie_b}, 
                            timeout=10)
        
        if resp.status_code != 400:
            results.add_fail("POST /api/team-account/accept/inv_nonexistent", 
                           f"Expected 400, got {resp.status_code}: {resp.text}")
            return
        
        results.add_pass("POST /api/team-account/accept/inv_nonexistent (400)")
        log(f"Response: {resp.status_code} - {resp.json()}")
        
    except Exception as e:
        results.add_fail("POST /api/team-account/accept/inv_nonexistent", str(e))

def main():
    log("="*80)
    log("SITEGENIE TEAM MULTI-SEAT + TOP-UP CHECKOUT BACKEND TEST")
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"Origin URL: {ORIGIN_URL}")
    
    results = TestResults()
    
    # Test 1: Register users
    owner_email, cookie_a, member_email, cookie_b = test_1_register_users(results)
    
    # Test 2: Non-team state
    test_2_non_team_state(results, cookie_a)
    
    # Test 3: Owner guard
    test_3_owner_guard(results, cookie_a)
    
    # Test 4: Top-up checkout
    test_4_top_up_checkout(results, cookie_a)
    
    # Test 5: Plans
    test_5_plans(results)
    
    # Test 6: Invalid accept
    test_6_invalid_accept(results, cookie_b)
    
    # Print summary
    results.summary()
    
    return len(results.failed) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
