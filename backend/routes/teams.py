from fastapi import APIRouter, HTTPException, Depends

from models import TeamInviteInput
from security import get_current_user
from services.teams import (
    get_team_state, invite_member, list_my_invites, accept_invite,
    revoke_invite, remove_member, leave_team,
)

router = APIRouter()


def _require_team_owner(user: dict):
    if user.get("team_role") != "owner" or not user.get("team_id"):
        raise HTTPException(status_code=403, detail="Only the team owner can manage members.")


@router.get("/team-account")
async def team_account(user: dict = Depends(get_current_user)):
    """Team state for the Billing page (owner or member)."""
    return await get_team_state(user)


@router.get("/team-account/invites")
async def my_invites(user: dict = Depends(get_current_user)):
    """Pending invites addressed to me (to accept after signing up)."""
    return {"invites": await list_my_invites(user)}


@router.post("/team-account/invite")
async def team_invite(input: TeamInviteInput, user: dict = Depends(get_current_user)):
    _require_team_owner(user)
    try:
        return await invite_member(user, str(input.email))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/team-account/accept/{invite_id}")
async def team_accept(invite_id: str, user: dict = Depends(get_current_user)):
    try:
        return await accept_invite(user, invite_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/team-account/invite/{invite_id}")
async def team_revoke(invite_id: str, user: dict = Depends(get_current_user)):
    _require_team_owner(user)
    await revoke_invite(user, invite_id)
    return {"revoked": True}


@router.delete("/team-account/member/{member_id}")
async def team_remove(member_id: str, user: dict = Depends(get_current_user)):
    _require_team_owner(user)
    try:
        await remove_member(user, member_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"removed": True}


@router.post("/team-account/leave")
async def team_leave(user: dict = Depends(get_current_user)):
    try:
        await leave_team(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"left": True}
