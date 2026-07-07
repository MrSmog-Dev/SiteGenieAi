from fastapi import APIRouter, HTTPException, Depends

from database import db
from models import BuildMessageInput
from security import get_current_user
from services.build import (create_session, get_session, handle_message, attach_template)

router = APIRouter()


@router.post("/build/session")
async def start_build(user: dict = Depends(get_current_user)):
    return await create_session(user["user_id"])


@router.get("/build/{session_id}")
async def build_session(session_id: str, user: dict = Depends(get_current_user)):
    s = await get_session(user["user_id"], session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Build session not found")
    return s


@router.post("/build/{session_id}/message")
async def build_message(session_id: str, input: BuildMessageInput, user: dict = Depends(get_current_user)):
    s = await get_session(user["user_id"], session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Build session not found")
    text = (input.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")
    return await handle_message(user, s, text, model=input.model, quality=input.quality)


@router.post("/build/{session_id}/attach/{template_id}")
async def build_attach(session_id: str, template_id: str, user: dict = Depends(get_current_user)):
    s = await get_session(user["user_id"], session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Build session not found")
    tpl = await db.templates.find_one({"template_id": template_id, "user_id": user["user_id"]}, {"_id": 1})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await attach_template(session_id, template_id)
    return {"attached": True}
