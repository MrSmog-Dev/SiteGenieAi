"""Team multi-seat (up to 5) with a shared credit pool.

A Team is owned by the billing user (Team plan). The owner invites teammates by email; accepted
members carry team_id/team_owner_id/team_role='member' on their user record and draw from the owner's
shared credit pool. On cancel/downgrade the team is disbanded and members revert to Free.
"""
import uuid
from datetime import datetime, timezone

from config import logger
from database import db

MAX_SEATS = 5   # owner + up to 4 members = 5 total


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_team_for_owner(owner_id: str) -> dict:
    """Create the team when a user activates the Team plan (idempotent)."""
    team = await db.teams.find_one({"owner_user_id": owner_id}, {"_id": 0})
    if team:
        return team
    team_id = f"team_{uuid.uuid4().hex[:10]}"
    team = {"team_id": team_id, "owner_user_id": owner_id,
            "member_ids": [], "created_at": _now(), "updated_at": _now()}
    await db.teams.insert_one(dict(team))
    await db.users.update_one({"user_id": owner_id},
                              {"$set": {"team_id": team_id, "team_owner_id": owner_id, "team_role": "owner"}})
    return team


async def get_team_state(user: dict) -> dict:
    """Team view for the Billing page — for owner or member."""
    team = None
    if user.get("team_id"):
        team = await db.teams.find_one({"team_id": user["team_id"]}, {"_id": 0})
    if not team:
        return {"is_team": False, "role": None}
    owner = await db.users.find_one({"user_id": team["owner_user_id"]},
                                    {"_id": 0, "user_id": 1, "name": 1, "email": 1})
    members = await db.users.find(
        {"user_id": {"$in": team.get("member_ids", [])}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1}).to_list(10)
    invites = await db.team_invites.find(
        {"team_id": team["team_id"], "status": "pending"},
        {"_id": 0, "invite_id": 1, "email": 1, "created_at": 1}).to_list(20)
    seats_used = 1 + len(members)
    return {
        "is_team": True,
        "role": user.get("team_role"),
        "team_id": team["team_id"],
        "owner": owner,
        "members": members,
        "pending_invites": invites,
        "seats_used": seats_used,
        "seats_total": MAX_SEATS,
        "seats_available": max(0, MAX_SEATS - seats_used - len(invites)),
    }


async def invite_member(owner: dict, email: str) -> dict:
    email = (email or "").lower().strip()
    if not email or "@" not in email:
        raise ValueError("Enter a valid email.")
    team = await db.teams.find_one({"owner_user_id": owner["user_id"]}, {"_id": 0})
    if not team:
        raise ValueError("You don't have a Team plan.")
    if email == owner.get("email", "").lower():
        raise ValueError("You're already on the team.")
    members = await db.users.find({"user_id": {"$in": team.get("member_ids", [])}},
                                  {"_id": 0, "email": 1}).to_list(10)
    if any(m.get("email", "").lower() == email for m in members):
        raise ValueError("That person is already a member.")
    pending = await db.team_invites.count_documents({"team_id": team["team_id"], "status": "pending"})
    if 1 + len(members) + pending >= MAX_SEATS:
        raise ValueError(f"Your team is full ({MAX_SEATS} seats). Remove a member or invite first.")
    existing = await db.team_invites.find_one(
        {"team_id": team["team_id"], "email": email, "status": "pending"}, {"_id": 1})
    if existing:
        raise ValueError("There's already a pending invite for that email.")
    invite_id = f"inv_{uuid.uuid4().hex[:12]}"
    await db.team_invites.insert_one({
        "invite_id": invite_id, "team_id": team["team_id"], "owner_user_id": owner["user_id"],
        "email": email, "status": "pending", "created_at": _now()})
    logger.info("team invite created for %s", email)
    return {"invite_id": invite_id, "email": email}


async def list_my_invites(user: dict) -> list:
    """Pending invites addressed to this user's email (so they can accept after signing up)."""
    return await db.team_invites.find(
        {"email": user.get("email", "").lower(), "status": "pending"}, {"_id": 0}).to_list(10)


async def accept_invite(user: dict, invite_id: str) -> dict:
    inv = await db.team_invites.find_one({"invite_id": invite_id, "status": "pending"}, {"_id": 0})
    if not inv:
        raise ValueError("Invite not found or already used.")
    if inv["email"] != user.get("email", "").lower():
        raise ValueError("This invite is for a different email.")
    if user.get("team_id"):
        raise ValueError("You're already on a team. Leave it first.")
    team = await db.teams.find_one({"team_id": inv["team_id"]}, {"_id": 0})
    if not team:
        raise ValueError("That team no longer exists.")
    if 1 + len(team.get("member_ids", [])) >= MAX_SEATS:
        raise ValueError("That team is full.")
    await db.teams.update_one({"team_id": team["team_id"]},
                              {"$addToSet": {"member_ids": user["user_id"]}, "$set": {"updated_at": _now()}})
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"team_id": team["team_id"], "team_owner_id": team["owner_user_id"],
                                        "team_role": "member"}})
    await db.team_invites.update_one({"invite_id": invite_id},
                                     {"$set": {"status": "accepted", "accepted_at": _now(),
                                               "accepted_by": user["user_id"]}})
    return {"joined": True, "team_id": team["team_id"]}


async def revoke_invite(owner: dict, invite_id: str):
    await db.team_invites.update_one(
        {"invite_id": invite_id, "owner_user_id": owner["user_id"], "status": "pending"},
        {"$set": {"status": "revoked"}})


async def remove_member(owner: dict, member_id: str):
    team = await db.teams.find_one({"owner_user_id": owner["user_id"]}, {"_id": 0})
    if not team or member_id not in team.get("member_ids", []):
        raise ValueError("Not a member of your team.")
    await db.teams.update_one({"team_id": team["team_id"]},
                              {"$pull": {"member_ids": member_id}, "$set": {"updated_at": _now()}})
    await _revert_member(member_id)


async def leave_team(user: dict):
    if user.get("team_role") != "member" or not user.get("team_id"):
        raise ValueError("You're not a team member.")
    await db.teams.update_one({"team_id": user["team_id"]},
                              {"$pull": {"member_ids": user["user_id"]}, "$set": {"updated_at": _now()}})
    await _revert_member(user["user_id"])


async def _revert_member(member_id: str):
    """Detach a member -> back to their own Free tier."""
    await db.users.update_one(
        {"user_id": member_id},
        {"$set": {"team_id": None, "team_owner_id": None, "team_role": None}})


async def disband_team(owner_id: str):
    """On Team plan cancel/downgrade: remove all members (revert to Free) and delete the team."""
    team = await db.teams.find_one({"owner_user_id": owner_id}, {"_id": 0})
    if not team:
        return
    for mid in team.get("member_ids", []):
        await _revert_member(mid)
    await db.team_invites.update_many(
        {"team_id": team["team_id"], "status": "pending"}, {"$set": {"status": "revoked"}})
    await db.teams.delete_one({"team_id": team["team_id"]})
    await db.users.update_one({"user_id": owner_id},
                              {"$set": {"team_id": None, "team_owner_id": None, "team_role": None}})
