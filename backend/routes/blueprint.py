from fastapi import APIRouter, HTTPException, Depends

from models import BlueprintCreateInput, BlueprintUpdateInput, BlueprintStatusInput
from security import get_current_user
from services.blueprint import (
    create_blueprint, get_blueprint, list_blueprints, update_spec, set_status, delete_blueprint,
)

router = APIRouter()


@router.post("/blueprints")
async def create(input: BlueprintCreateInput, user: dict = Depends(get_current_user)):
    spec = input.spec.model_dump() if input.spec else {}
    return await create_blueprint(user["user_id"], input.name, spec)


@router.get("/blueprints")
async def list_all(user: dict = Depends(get_current_user)):
    return await list_blueprints(user["user_id"])


@router.get("/blueprints/{blueprint_id}")
async def get(blueprint_id: str, user: dict = Depends(get_current_user)):
    bp = await get_blueprint(user["user_id"], blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


@router.put("/blueprints/{blueprint_id}")
async def update(blueprint_id: str, input: BlueprintUpdateInput, user: dict = Depends(get_current_user)):
    bp = await update_spec(user["user_id"], blueprint_id, input.name, input.spec.model_dump())
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


@router.put("/blueprints/{blueprint_id}/status")
async def update_status(blueprint_id: str, input: BlueprintStatusInput, user: dict = Depends(get_current_user)):
    try:
        bp = await set_status(user["user_id"], blueprint_id, input.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not bp:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return bp


@router.delete("/blueprints/{blueprint_id}")
async def delete(blueprint_id: str, user: dict = Depends(get_current_user)):
    ok = await delete_blueprint(user["user_id"], blueprint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return {"success": True}
