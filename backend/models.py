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
    quality: Optional[str] = "quality"   # "quality" (2-pass) | "economy" (fast single-pass)


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
