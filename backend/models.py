from typing import Optional
from pydantic import BaseModel, EmailStr


class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionInput(BaseModel):
    session_id: str


class GenerateInput(BaseModel):
    business_name: str
    industry: str
    description: str
    style: Optional[str] = "modern"
    primary_color: Optional[str] = "#0055FF"
    contact_email: Optional[str] = ""
    phone: Optional[str] = ""
    target_audience: Optional[str] = ""
    key_services: Optional[str] = ""
    brand_keywords: Optional[str] = ""
    pages: Optional[str] = ""
    quality: Optional[str] = "quality"   # "economy" | "quality" | "premium"
    model: Optional[str] = None          # override build model (e.g. claude-sonnet-4-6, claude-haiku-4-5)


class CheckoutInput(BaseModel):
    kind: str          # "subscription" | "credits"
    plan_id: str       # key in SUBSCRIPTION_PLANS or CREDIT_PACKS
    origin_url: str


class SubCheckoutInput(BaseModel):
    plan_id: str
    origin_url: str


class EditInput(BaseModel):
    instructions: str


class SlugInput(BaseModel):
    slug: str


class MarketListInput(BaseModel):
    template_id: str


class MarketCheckoutInput(BaseModel):
    origin_url: str


class MarketPriceInput(BaseModel):
    price_usd: float


class AgentChatInput(BaseModel):
    message: str


class ForgeBuildInput(BaseModel):
    brief: str


class WarRoomInput(BaseModel):
    topic: str


class ResetBusinessInput(BaseModel):
    confirm: str
    include_leads: bool = False


class LeadScanInput(BaseModel):
    url: str


class LeadHuntInput(BaseModel):
    location: str
    category: str


class LeadStatusInput(BaseModel):
    status: str


class DomainInput(BaseModel):
    domain: str


class TemplateDetailsInput(BaseModel):
    """Owner/buyer edits to a purchased or generated site's core details ("Make it yours")."""
    business_name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    primary_color: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None


class SupportChatInput(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[list] = None
    contact_email: Optional[str] = None


class FeedbackStatusInput(BaseModel):
    status: str   # "new" | "reviewed" | "actioned" | "dismissed"
