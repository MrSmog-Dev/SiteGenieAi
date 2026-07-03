from fastapi import APIRouter

from config import SUBSCRIPTION_PLANS, CREDIT_PACKS

router = APIRouter()


@router.get("/plans")
async def get_plans():
    return {"subscriptions": SUBSCRIPTION_PLANS, "credit_packs": CREDIT_PACKS}
