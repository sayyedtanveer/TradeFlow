from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────
class RegisterTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Company name")
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$", description="URL-safe identifier")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(default="starter", pattern=r"^(starter|professional|enterprise)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    tenant_id: str = Field(..., description="UUID of the tenant to authenticate against")


# ── Response schemas ───────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Nested user object returned inside /auth/me
class UserInMeResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    tenant_id: str
    is_active: bool


# Nested tenant object returned inside /auth/me
class TenantInMeResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool


# Shape expected by frontend MeResponse type
class UserProfileResponse(BaseModel):
    user: UserInMeResponse
    tenant: TenantInMeResponse
    permissions: List[str] = []


class RegisterTenantResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    slug: str
    user_id: str
    email: str
    role: str
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    tenant_id: str
    email: str
    role: str
    full_name: str
