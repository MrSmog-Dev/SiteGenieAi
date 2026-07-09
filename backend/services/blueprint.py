"""Website Blueprint - the planning layer for a website project.

A Blueprint is created standalone, with no dependency on a generated website. It is
progressively populated with structured planning info, moves through draft -> ready ->
generated, and is versioned in place (a capped history of prior spec snapshots).

Generation (Forge, /templates/generate, the Build Canvas) does not read or write
Blueprints yet - that wiring is a future phase. A generated website/template/build
session may later store an optional blueprint_id to point back at the Blueprint that
produced it; this module doesn't assume or require that reference to exist.
"""
import uuid
from datetime import datetime, timezone

from database import db

MAX_HISTORY = 50
VALID_STATUSES = ("draft", "ready", "generated", "archived")


def _now():
    return datetime.now(timezone.utc)


async def create_blueprint(user_id: str, name: str | None, spec: dict | None) -> dict:
    bp_id = f"bp_{uuid.uuid4().hex[:12]}"
    doc = {
        "blueprint_id": bp_id,
        "user_id": user_id,
        "name": name or "Untitled Website Project",
        "status": "draft",
        "version": 1,
        "spec": spec or {},
        "history": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.blueprints.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def get_blueprint(user_id: str, blueprint_id: str) -> dict | None:
    return await db.blueprints.find_one(
        {"blueprint_id": blueprint_id, "user_id": user_id}, {"_id": 0})


async def list_blueprints(user_id: str) -> list[dict]:
    return await db.blueprints.find(
        {"user_id": user_id}, {"_id": 0, "history": 0}
    ).sort("updated_at", -1).to_list(200)


async def update_spec(user_id: str, blueprint_id: str, name: str | None, spec: dict) -> dict | None:
    """Progressive edit: merges into the existing spec and pushes the prior version to history."""
    existing = await get_blueprint(user_id, blueprint_id)
    if not existing:
        return None
    snapshot = {"version": existing["version"], "spec": existing["spec"], "updated_at": existing["updated_at"]}
    merged_spec = {**existing.get("spec", {}), **{k: v for k, v in spec.items() if v is not None}}
    update = {
        "spec": merged_spec,
        "version": existing["version"] + 1,
        "updated_at": _now(),
    }
    if name:
        update["name"] = name
    await db.blueprints.update_one(
        {"blueprint_id": blueprint_id, "user_id": user_id},
        {"$set": update, "$push": {"history": {"$each": [snapshot], "$slice": -MAX_HISTORY}}},
    )
    return await get_blueprint(user_id, blueprint_id)


async def set_status(user_id: str, blueprint_id: str, status: str) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    res = await db.blueprints.update_one(
        {"blueprint_id": blueprint_id, "user_id": user_id},
        {"$set": {"status": status, "updated_at": _now()}},
    )
    if res.matched_count == 0:
        return None
    return await get_blueprint(user_id, blueprint_id)


async def delete_blueprint(user_id: str, blueprint_id: str) -> bool:
    res = await db.blueprints.delete_one({"blueprint_id": blueprint_id, "user_id": user_id})
    return res.deleted_count > 0
