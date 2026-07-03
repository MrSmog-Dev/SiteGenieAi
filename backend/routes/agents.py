import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from database import db
from models import AgentChatInput, ForgeBuildInput
from security import get_current_user, is_owner
from services.agents import AGENTS, AGENT_MAP, agent_reply, run_forge_build

router = APIRouter()


def _require_owner(user: dict):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="The AI Team is available to the store owner only.")


def _public(agent: dict) -> dict:
    return {k: agent[k] for k in ("id", "name", "role", "color", "tagline", "quick_actions")}


@router.get("/agents")
async def list_agents(user: dict = Depends(get_current_user)):
    _require_owner(user)
    chats = {c["agent_id"]: c async for c in db.agent_chats.find(
        {"user_id": user["user_id"]}, {"_id": 0, "agent_id": 1, "messages": {"$slice": -1}, "updated_at": 1})}
    out = []
    for a in AGENTS:
        item = _public(a)
        c = chats.get(a["id"])
        last = (c or {}).get("messages") or []
        item["last_message"] = (last[-1]["content"][:80] if last else None)
        item["updated_at"] = (c or {}).get("updated_at")
        out.append(item)
    return out


@router.get("/agents/jobs/{job_id}")
async def agent_job_status(job_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    job = await db.agent_jobs.find_one({"job_id": job_id, "user_id": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/agents/forge/build")
async def forge_build(input: ForgeBuildInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    brief = input.brief.strip()
    if len(brief) < 3:
        raise HTTPException(status_code=400, detail="Describe the niche you want Forge to build.")
    active = await db.agent_jobs.find_one(
        {"user_id": user["user_id"], "status": {"$in": ["queued", "designing", "building", "pricing"]}}, {"_id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Forge is already building a template. Wait for it to finish.")
    job_id = f"forge_{uuid.uuid4().hex[:10]}"
    await db.agent_jobs.insert_one({
        "job_id": job_id, "user_id": user["user_id"], "agent_id": "forge", "brief": brief,
        "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(run_forge_build(job_id, user["user_id"], brief))
    return {"job_id": job_id, "status": "queued"}


@router.post("/agents/ivy/blog")
async def ivy_write_blog(user: dict = Depends(get_current_user)):
    _require_owner(user)
    from services.blog import run_ivy_blog
    asyncio.create_task(run_ivy_blog(user["user_id"]))
    return {"status": "writing"}


@router.get("/agents/{agent_id}/chat")
async def get_agent_chat(agent_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail="Agent not found")
    chat = await db.agent_chats.find_one(
        {"user_id": user["user_id"], "agent_id": agent_id}, {"_id": 0, "messages": 1})
    return {"agent": _public(AGENT_MAP[agent_id]), "messages": (chat or {}).get("messages", [])}


@router.post("/agents/{agent_id}/chat")
async def send_agent_chat(agent_id: str, input: AgentChatInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    agent = AGENT_MAP.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    message = input.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty")
    chat = await db.agent_chats.find_one(
        {"user_id": user["user_id"], "agent_id": agent_id}, {"_id": 0, "messages": 1})
    history = (chat or {}).get("messages", [])
    try:
        reply = await agent_reply(agent, history, message)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"{agent['name']} took too long to reply. Try again.")
    except Exception as e:
        detail = str(e)
        if "budget" in detail.lower():
            raise HTTPException(status_code=402, detail="AI budget exhausted — top up your Emergent Universal Key.")
        raise HTTPException(status_code=502, detail=f"{agent['name']} couldn't reply right now. Try again.")
    now = datetime.now(timezone.utc).isoformat()
    new_msgs = [{"role": "user", "content": message, "ts": now},
                {"role": "agent", "content": reply, "ts": now}]
    await db.agent_chats.update_one(
        {"user_id": user["user_id"], "agent_id": agent_id},
        {"$push": {"messages": {"$each": new_msgs}}, "$set": {"updated_at": now}}, upsert=True)
    return {"reply": reply}


@router.delete("/agents/{agent_id}/chat")
async def clear_agent_chat(agent_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    await db.agent_chats.delete_one({"user_id": user["user_id"], "agent_id": agent_id})
    return {"cleared": True}
