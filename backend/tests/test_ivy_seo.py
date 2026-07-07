"""
Test Ivy SEO Autopilot backend endpoints.
All endpoints are OWNER-GATED and require authentication.
"""
import os
import time
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://genie-deploy-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "neobeyondlegacy2@gmail.com"
OWNER_PASSWORD = "OwnerGenie2025!"


def test_ivy_seo_endpoints():
    """Test all Ivy SEO Autopilot endpoints with owner authentication."""
    
    # ============ 1. LOGIN TO GET SESSION COOKIE ============
    print("\n=== 1. Testing Login ===")
    session = requests.Session()
    login_payload = {"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    
    # Try login, handle rate limiting
    login_resp = session.post(f"{API}/auth/login", json=login_payload, timeout=30)
    if login_resp.status_code == 429:
        print("⚠️  Rate limited (429), waiting 60s and retrying...")
        time.sleep(60)
        login_resp = session.post(f"{API}/auth/login", json=login_payload, timeout=30)
    
    assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code} {login_resp.text}"
    print(f"✅ Login successful: {login_resp.status_code}")
    
    # Verify session cookie is set
    assert "session_token" in session.cookies, "Session cookie not set after login"
    print(f"✅ Session cookie captured: {session.cookies.get('session_token')[:20]}...")
    
    
    # ============ 2. GET /api/agents/ivy/seo/overview ============
    print("\n=== 2. Testing GET /api/agents/ivy/seo/overview ===")
    overview_resp = session.get(f"{API}/agents/ivy/seo/overview", timeout=30)
    assert overview_resp.status_code == 200, f"Overview failed: {overview_resp.status_code} {overview_resp.text}"
    
    overview_data = overview_resp.json()
    required_keys = ["calendar_total", "calendar_planned", "articles_published", "avg_article_score", "last_geo_visibility"]
    for key in required_keys:
        assert key in overview_data, f"Missing key '{key}' in overview response"
    
    print(f"✅ Overview endpoint passed")
    print(f"   - calendar_total: {overview_data.get('calendar_total')}")
    print(f"   - calendar_planned: {overview_data.get('calendar_planned')}")
    print(f"   - articles_published: {overview_data.get('articles_published')}")
    print(f"   - avg_article_score: {overview_data.get('avg_article_score')}")
    print(f"   - last_geo_visibility: {overview_data.get('last_geo_visibility')}")
    
    
    # ============ 3. GET /api/agents/ivy/seo/calendar ============
    print("\n=== 3. Testing GET /api/agents/ivy/seo/calendar ===")
    calendar_resp = session.get(f"{API}/agents/ivy/seo/calendar", timeout=30)
    assert calendar_resp.status_code == 200, f"Calendar failed: {calendar_resp.status_code} {calendar_resp.text}"
    
    calendar_data = calendar_resp.json()
    assert "calendar" in calendar_data, "Missing 'calendar' key in response"
    assert isinstance(calendar_data["calendar"], list), "Calendar should be a list"
    
    print(f"✅ Calendar endpoint passed")
    print(f"   - Total calendar items: {len(calendar_data['calendar'])}")
    
    # Verify seeded topics exist (~12 planned topics)
    if len(calendar_data["calendar"]) > 0:
        sample = calendar_data["calendar"][0]
        required_item_keys = ["title", "target_keyword", "intent", "scheduled_for", "status"]
        for key in required_item_keys:
            assert key in sample, f"Missing key '{key}' in calendar item"
        print(f"   - Sample item: {sample.get('title')[:50]}...")
        print(f"   - Target keyword: {sample.get('target_keyword')}")
        print(f"   - Status: {sample.get('status')}")
    
    
    # ============ 4. POST /api/agents/ivy/seo/geo-audit ============
    print("\n=== 4. Testing POST /api/agents/ivy/seo/geo-audit ===")
    geo_payload = {"query": "best AI website builder for a small bakery"}
    geo_resp = session.post(f"{API}/agents/ivy/seo/geo-audit", json=geo_payload, timeout=40)
    assert geo_resp.status_code == 200, f"Geo audit failed: {geo_resp.status_code} {geo_resp.text}"
    
    geo_data = geo_resp.json()
    required_geo_keys = ["query", "answer", "sitegenie_cited", "visibility", "content_gap"]
    for key in required_geo_keys:
        assert key in geo_data, f"Missing key '{key}' in geo audit response"
    
    assert geo_data["query"] == "best AI website builder for a small bakery", "Query mismatch"
    assert isinstance(geo_data["answer"], str) and len(geo_data["answer"]) > 0, "Answer should be non-empty string"
    assert isinstance(geo_data["sitegenie_cited"], bool), "sitegenie_cited should be boolean"
    assert isinstance(geo_data["visibility"], int) and 0 <= geo_data["visibility"] <= 100, "Visibility should be 0-100"
    assert isinstance(geo_data["content_gap"], str) and len(geo_data["content_gap"]) > 0, "Content gap should be non-empty"
    
    print(f"✅ Geo audit endpoint passed")
    print(f"   - Query: {geo_data['query']}")
    print(f"   - Answer: {geo_data['answer'][:100]}...")
    print(f"   - SiteGenie cited: {geo_data['sitegenie_cited']}")
    print(f"   - Visibility: {geo_data['visibility']}/100")
    print(f"   - Content gap: {geo_data['content_gap'][:80]}...")
    
    
    # ============ 5. POST /api/agents/ivy/seo/tech-audit ============
    print("\n=== 5. Testing POST /api/agents/ivy/seo/tech-audit ===")
    tech_payload = {"url": "https://example.com"}
    tech_resp = session.post(f"{API}/agents/ivy/seo/tech-audit", json=tech_payload, timeout=50)
    assert tech_resp.status_code == 200, f"Tech audit failed: {tech_resp.status_code} {tech_resp.text}"
    
    tech_data = tech_resp.json()
    required_tech_keys = ["url", "signals", "summary", "fixes"]
    for key in required_tech_keys:
        assert key in tech_data, f"Missing key '{key}' in tech audit response"
    
    assert isinstance(tech_data["signals"], dict), "Signals should be an object"
    assert isinstance(tech_data["summary"], str) and len(tech_data["summary"]) > 0, "Summary should be non-empty"
    assert isinstance(tech_data["fixes"], list), "Fixes should be an array"
    
    # Verify signals structure
    signal_keys = ["title", "has_meta_description", "h1_count"]
    for key in signal_keys:
        assert key in tech_data["signals"], f"Missing signal '{key}'"
    
    print(f"✅ Tech audit endpoint passed")
    print(f"   - URL: {tech_data['url']}")
    print(f"   - Title: {tech_data['signals'].get('title', 'N/A')[:50]}")
    print(f"   - H1 count: {tech_data['signals'].get('h1_count')}")
    print(f"   - Summary: {tech_data['summary'][:80]}...")
    print(f"   - Fixes count: {len(tech_data['fixes'])}")
    
    
    # ============ 6. GET /api/agents/ivy/seo/audits ============
    print("\n=== 6. Testing GET /api/agents/ivy/seo/audits ===")
    audits_resp = session.get(f"{API}/agents/ivy/seo/audits", timeout=30)
    assert audits_resp.status_code == 200, f"Audits list failed: {audits_resp.status_code} {audits_resp.text}"
    
    audits_data = audits_resp.json()
    assert "audits" in audits_data, "Missing 'audits' key in response"
    assert isinstance(audits_data["audits"], list), "Audits should be a list"
    
    print(f"✅ Audits list endpoint passed")
    print(f"   - Total audits: {len(audits_data['audits'])}")
    
    # Verify the geo and tech audits we just created are in the list
    if len(audits_data["audits"]) >= 2:
        geo_found = any(a.get("kind") == "geo" and a.get("query") == "best AI website builder for a small bakery" 
                       for a in audits_data["audits"])
        tech_found = any(a.get("kind") == "technical" for a in audits_data["audits"])
        assert geo_found, "Geo audit not found in audits list"
        assert tech_found, "Tech audit not found in audits list"
        print(f"   - ✅ Geo audit found in list")
        print(f"   - ✅ Tech audit found in list")
    
    
    # ============ 7. POST /api/agents/ivy/seo/reddit ============
    print("\n=== 7. Testing POST /api/agents/ivy/seo/reddit ===")
    reddit_resp = session.post(f"{API}/agents/ivy/seo/reddit", timeout=40)
    assert reddit_resp.status_code == 200, f"Reddit opportunities failed: {reddit_resp.status_code} {reddit_resp.text}"
    
    reddit_data = reddit_resp.json()
    assert "opportunities" in reddit_data, "Missing 'opportunities' key in response"
    assert isinstance(reddit_data["opportunities"], list), "Opportunities should be a list"
    
    print(f"✅ Reddit opportunities endpoint passed")
    print(f"   - Total opportunities: {len(reddit_data['opportunities'])}")
    
    if len(reddit_data["opportunities"]) > 0:
        sample_opp = reddit_data["opportunities"][0]
        required_opp_keys = ["subreddit", "angle", "reply_draft"]
        for key in required_opp_keys:
            assert key in sample_opp, f"Missing key '{key}' in opportunity item"
        print(f"   - Sample subreddit: {sample_opp.get('subreddit')}")
        print(f"   - Sample angle: {sample_opp.get('angle')[:60]}...")
    
    
    # ============ 8. GET /api/agents/ivy/seo/link-map ============
    print("\n=== 8. Testing GET /api/agents/ivy/seo/link-map ===")
    linkmap_resp = session.get(f"{API}/agents/ivy/seo/link-map", timeout=40)
    assert linkmap_resp.status_code == 200, f"Link map failed: {linkmap_resp.status_code} {linkmap_resp.text}"
    
    linkmap_data = linkmap_resp.json()
    required_linkmap_keys = ["pillars", "total_posts", "suggestions"]
    for key in required_linkmap_keys:
        assert key in linkmap_data, f"Missing key '{key}' in link map response"
    
    print(f"✅ Link map endpoint passed")
    print(f"   - Total posts: {linkmap_data.get('total_posts')}")
    print(f"   - Pillars count: {len(linkmap_data.get('pillars', []))}")
    print(f"   - Suggestions count: {len(linkmap_data.get('suggestions', []))}")
    print(f"   - Note: Pillars/suggestions may be empty if no blog posts exist (OK)")
    
    
    # ============ 9. AUTH GUARD TEST - Call overview WITHOUT cookie ============
    print("\n=== 9. Testing Auth Guard (no cookie) ===")
    no_auth_session = requests.Session()  # Fresh session without login
    no_auth_resp = no_auth_session.get(f"{API}/agents/ivy/seo/overview", timeout=30)
    
    assert no_auth_resp.status_code in [401, 403], \
        f"Expected 401/403 without auth, got {no_auth_resp.status_code}"
    
    print(f"✅ Auth guard working correctly: {no_auth_resp.status_code}")
    print(f"   - Unauthenticated request correctly rejected")
    
    
    # ============ SUMMARY ============
    print("\n" + "="*60)
    print("🎉 ALL IVY SEO AUTOPILOT TESTS PASSED!")
    print("="*60)
    print("✅ 1. Login with session cookie")
    print("✅ 2. GET /api/agents/ivy/seo/overview")
    print("✅ 3. GET /api/agents/ivy/seo/calendar")
    print("✅ 4. POST /api/agents/ivy/seo/geo-audit")
    print("✅ 5. POST /api/agents/ivy/seo/tech-audit")
    print("✅ 6. GET /api/agents/ivy/seo/audits")
    print("✅ 7. POST /api/agents/ivy/seo/reddit")
    print("✅ 8. GET /api/agents/ivy/seo/link-map")
    print("✅ 9. Auth guard (401/403 without cookie)")
    print("="*60)


if __name__ == "__main__":
    test_ivy_seo_endpoints()
