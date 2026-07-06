import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends

from database import db
from models import SupportChatInput, FeedbackStatusInput
from security import check_rate_limit, get_current_user, is_owner
from services.support import halo_reply, detect_customer_feedback, get_page

router = APIRouter()


def _require_owner(user: dict):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="The feedback inbox is available to the store owner only.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/support/chat")
async def support_chat(input: SupportChatInput, request: Request):
    """Public customer support chat with Halo — no auth required."""
    message = (input.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty")
    if len(message) > 2000:
        message = message[:2000]
    # light abuse protection keyed on client IP
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "anon").split(",")[0].strip()
    try:
        await check_rate_limit(f"support:{ip}", max_count=30, window_seconds=300)
    except HTTPException:
        raise HTTPException(status_code=429, detail="You're sending messages a bit fast — give me a moment.")

    session_id = (input.session_id or f"sess_{uuid.uuid4().hex[:12]}").strip()[:64]
    history = input.history or []
    try:
        reply = await halo_reply(history, message)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Halo took too long to respond. Please try again.")
    except Exception:
        raise HTTPException(status_code=502, detail="Halo is unavailable right now. Please try again in a moment.")

    now = _now()
    new_msgs = [{"role": "user", "content": message, "ts": now},
                {"role": "assistant", "content": reply, "ts": now}]
    await db.support_chats.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {"$each": new_msgs, "$slice": -100}},
         "$set": {"updated_at": now}, "$setOnInsert": {"created_at": now}}, upsert=True)

    contact = {"email": input.contact_email} if input.contact_email else None
    asyncio.create_task(detect_customer_feedback(session_id, message, reply, contact))
    return {"reply": reply, "session_id": session_id}


@router.get("/support/pages/{kind}")
async def support_page(kind: str):
    page = await get_page(kind)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page



FEEDBACK_STATUSES = {"new", "reviewed", "actioned", "dismissed"}
FEEDBACK_KINDS = {"feature", "bug", "complaint", "praise", "feedback"}


@router.get("/support/feedback")
async def list_feedback(status: str = None, kind: str = None, limit: int = 100,
                        user: dict = Depends(get_current_user)):
    """Owner-only Customer Feedback inbox with filters + summary counts."""
    _require_owner(user)
    q = {}
    if status and status in FEEDBACK_STATUSES:
        q["status"] = status
    if kind and kind in FEEDBACK_KINDS:
        q["kind"] = kind
    limit = max(1, min(int(limit or 100), 300))
    items = await db.customer_feedback.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    by_status = {s["_id"]: s["n"] async for s in db.customer_feedback.aggregate(
        [{"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
    by_kind = {s["_id"]: s["n"] async for s in db.customer_feedback.aggregate(
        [{"$group": {"_id": "$kind", "n": {"$sum": 1}}}])}
    total = await db.customer_feedback.count_documents({})
    new_count = by_status.get("new", 0)
    return {"feedback": items, "total": total, "new_count": new_count,
            "by_status": by_status, "by_kind": by_kind}


@router.patch("/support/feedback/{feedback_id}")
async def update_feedback(feedback_id: str, input: FeedbackStatusInput,
                          user: dict = Depends(get_current_user)):
    _require_owner(user)
    if input.status not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = await db.customer_feedback.update_one(
        {"feedback_id": feedback_id},
        {"$set": {"status": input.status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"feedback_id": feedback_id, "status": input.status}


@router.delete("/support/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    res = await db.customer_feedback.delete_one({"feedback_id": feedback_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"deleted": True}
