import asyncio

from fastapi import APIRouter, HTTPException, Depends

from config import GOOGLE_PLACES_API_KEY
from database import db
from models import LeadScanInput, LeadHuntInput, LeadStatusInput
from security import get_current_user, is_owner
from services.leads import (
    scan_website, upsert_weak_site_lead, hunt_places, set_lead_outreach, LEAD_STATUSES,
    leads_remaining_this_month, MONTHLY_LEAD_CAP,
)

router = APIRouter()


def _require_owner(user: dict):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Rex's lead tools are available to the store owner only.")


@router.get("/leads")
async def list_leads(user: dict = Depends(get_current_user)):
    _require_owner(user)
    return await db.leads.find({"archived": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(300)


@router.get("/leads/hunt/status")
async def hunt_status(user: dict = Depends(get_current_user)):
    _require_owner(user)
    return {"places_configured": bool(GOOGLE_PLACES_API_KEY),
            "leads_remaining_this_month": await leads_remaining_this_month(),
            "monthly_lead_cap": MONTHLY_LEAD_CAP}


@router.post("/leads/hunt")
async def hunt(input: LeadHuntInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if not GOOGLE_PLACES_API_KEY:
        raise HTTPException(status_code=424,
                            detail="Google Places API key not connected yet — add GOOGLE_PLACES_API_KEY to unlock Rex's hunting.")
    location, category = input.location.strip(), input.category.strip()
    if not location or not category:
        raise HTTPException(status_code=400, detail="Give Rex a location and a business type.")
    try:
        result = await hunt_places(location, category)
        from services.automation import rex_autopilot
        asyncio.create_task(rex_autopilot(user["user_id"]))
        return result
    except RuntimeError as e:
        # 424 (not 502) so Cloudflare doesn't hide our error message with its own 5xx page.
        raise HTTPException(status_code=424, detail=str(e))


@router.post("/leads/scan")
async def scan(input: LeadScanInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if not input.url.strip():
        raise HTTPException(status_code=400, detail="Give Rex a website URL to scan.")
    try:
        result = await scan_website(input.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    lead_added, lead_id = False, None
    if result["score"] <= 65:
        info = await upsert_weak_site_lead(result)
        lead_added, lead_id = True, info["lead_id"]
    result.pop("domain", None)
    return {**result, "lead_added": lead_added, "lead_id": lead_id}


@router.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, input: LeadStatusInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if input.status not in LEAD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {LEAD_STATUSES}")
    res = await db.leads.update_one({"lead_id": lead_id}, {"$set": {"status": input.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    demo_triggered = False
    if input.status == "contacted":
        lead = await db.leads.find_one({"lead_id": lead_id}, {"_id": 0, "demo_status": 1})
        if (lead or {}).get("demo_status") not in ("queued", "building", "ready"):
            from datetime import datetime, timezone
            await db.leads.update_one({"lead_id": lead_id},
                                      {"$set": {"demo_status": "queued",
                                                "updated_at": datetime.now(timezone.utc).isoformat()}})
            from services.automation import run_lead_demo
            asyncio.create_task(run_lead_demo(lead_id))
            demo_triggered = True
    return {"lead_id": lead_id, "status": input.status, "demo_triggered": demo_triggered}


@router.post("/leads/{lead_id}/outreach")
async def draft_outreach(lead_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    lead = await db.leads.find_one({"lead_id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        return await set_lead_outreach(lead)
    except Exception:
        raise HTTPException(status_code=502, detail="Rex couldn't draft the pitch right now — try again.")


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    res = await db.leads.delete_one({"lead_id": lead_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"deleted": True}
