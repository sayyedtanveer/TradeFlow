from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


@dataclass(frozen=True)
class GetItemTemplateQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class ListItemTemplatesQuery:
    tenant_id: uuid.UUID
    query: Optional[str] = None          # text search on name/code
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class GetItemVariantQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class ListItemVariantsQuery:
    template_id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 50
