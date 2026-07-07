import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends

from database import db
from models import AgentChatInput, ForgeBuildInput, WarRoomInput, AgentMemoryInput
from security import get_current_user, is_owner
from services.agents import AGENTS, AGENT_MAP, agent_reply, run_forge_build
from services.team import detect_and_route_memos, post_war_room, run_war_room_meeting
from services.activity import get_activity_feed, get_status_board
from services.memory import (get_memory, add_fact, delete_memory_item,
                             get_team_brain, add_shared_fact, delete_shared_item)

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


@router.get("/agents/activity")
async def agent_activity_feed(limit: int = 40, before: str = None, agent_id: str = None,
                             user: dict = Depends(get_current_user)):
    _require_owner(user)
    limit = max(1, min(int(limit or 40), 100))
    items = await get_activity_feed(user["user_id"], limit=limit, before=before, agent_id=agent_id)
    return {"activities": items, "agents": {a["id"]: {"name": a["name"], "color": a["color"],
                                                       "role": a["role"]} for a in AGENTS}}


@router.get("/agents/status")
async def agent_status_board(user: dict = Depends(get_current_user)):
    _require_owner(user)
    return await get_status_board(user["user_id"])


@router.get("/agents/team-memory")
async def get_team_memory(user: dict = Depends(get_current_user)):
    _require_owner(user)
    brain = await get_team_brain(user["user_id"])
    return {"facts": brain.get("facts", [])}


@router.post("/agents/team-memory")
async def add_team_memory(input: AgentMemoryInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    text = (input.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Memory text is empty.")
    await add_shared_fact(user["user_id"], text, input.kind or "fact")
    return await get_team_brain(user["user_id"])


@router.delete("/agents/team-memory/{mem_id}")
async def delete_team_memory(mem_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    ok = await delete_shared_item(user["user_id"], mem_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"deleted": True}


@router.get("/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail="Agent not found")
    mem = await get_memory(user["user_id"], agent_id)
    return {"agent": _public(AGENT_MAP[agent_id]),
            "facts": mem.get("facts", []),
            "open_threads": [t for t in mem.get("open_threads", []) if t.get("status") != "done"],
            "rolling_summary": mem.get("rolling_summary", "")}


@router.post("/agents/{agent_id}/memory")
async def add_agent_memory(agent_id: str, input: AgentMemoryInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    if agent_id not in AGENT_MAP:
        raise HTTPException(status_code=404, detail="Agent not found")
    text = (input.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Memory text is empty.")
    await add_fact(user["user_id"], agent_id, text, input.kind or "fact")
    return await get_memory(user["user_id"], agent_id)


@router.delete("/agents/{agent_id}/memory/{mem_id}")
async def delete_agent_memory(agent_id: str, mem_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    ok = await delete_memory_item(user["user_id"], agent_id, mem_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"deleted": True}


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


@router.get("/agents/war-room")
async def get_war_room(user: dict = Depends(get_current_user)):
    _require_owner(user)
    room = await db.war_room.find_one({"user_id": user["user_id"]}, {"_id": 0, "messages": 1})
    meeting = await db.war_room_meetings.find_one(
        {"user_id": user["user_id"]}, {"_id": 0}, sort=[("created_at", -1)])
    tasks = await db.team_tasks.find(
        {"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"messages": (room or {}).get("messages", []), "meeting": meeting, "tasks": tasks}


@router.post("/agents/war-room")
async def start_war_room(input: WarRoomInput, user: dict = Depends(get_current_user)):
    _require_owner(user)
    topic = input.topic.strip()
    if len(topic) < 3:
        raise HTTPException(status_code=400, detail="Give the team a topic to discuss.")
    fresh = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    active = await db.war_room_meetings.find_one(
        {"user_id": user["user_id"], "status": {"$in": ["starting", "running"]},
         "updated_at": {"$gte": fresh}}, {"_id": 1})
    if active:
        raise HTTPException(status_code=409, detail="A meeting is already in progress. Let the team finish.")
    meeting_id = f"meet_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    await db.war_room_meetings.insert_one({
        "meeting_id": meeting_id, "user_id": user["user_id"], "topic": topic,
        "status": "starting", "created_at": now, "updated_at": now})
    await post_war_room(user["user_id"], None, topic, role="owner")
    asyncio.create_task(run_war_room_meeting(meeting_id, user["user_id"], topic))
    return {"meeting_id": meeting_id, "status": "starting"}


@router.delete("/agents/war-room")
async def clear_war_room(user: dict = Depends(get_current_user)):
    _require_owner(user)
    await db.war_room.delete_one({"user_id": user["user_id"]})
    return {"cleared": True}


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
        reply = await agent_reply(agent, history, message, user_id=user["user_id"])
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
        {"$push": {"messages": {"$each": new_msgs, "$slice": -200}}, "$set": {"updated_at": now}}, upsert=True)
    asyncio.create_task(detect_and_route_memos(user["user_id"], agent_id, message, reply))
    from services.memory import extract_and_store_memory
    asyncio.create_task(extract_and_store_memory(user["user_id"], agent_id, message, reply))
    return {"reply": reply}


@router.delete("/agents/{agent_id}/chat")
async def clear_agent_chat(agent_id: str, user: dict = Depends(get_current_user)):
    _require_owner(user)
    await db.agent_chats.delete_one({"user_id": user["user_id"], "agent_id": agent_id})
    return {"cleared": True}
