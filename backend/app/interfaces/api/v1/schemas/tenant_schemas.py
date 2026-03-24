from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
import uuid


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool


class FileUploadResponse(BaseModel):
    filename: str
    url: str
    content_type: str
    size_bytes: int
    category: str
