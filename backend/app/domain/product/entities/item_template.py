from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.domain.shared.base_entity import BaseEntity


class ItemTemplate(BaseEntity):
    """
    Aggregate root for a product template.

    A template defines the structure of a product, including which attributes
    (e.g., Size, Color) are valid for its variants.

    Domain Rules:
    - `code` must be unique per tenant (enforced at application+DB layer)
    - `attributes` is a list of dicts: [{"key": "SIZE", "label": "Size", "values": ["S", "M", "L"]}, ...]
    - is_active defaults to True
    """

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        tenant_id: uuid.UUID,
        code: str,
        name: str,
        description: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        base_unit_id: Optional[uuid.UUID] = None,
        attributes: Optional[List[Dict[str, Any]]] = None,
        is_active: bool = True,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            id=id,
            tenant_id=tenant_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
        )

        code = code.strip().upper()
        if not code:
            raise ValueError("ItemTemplate code is required.")
        if len(code) > 50:
            raise ValueError("ItemTemplate code must be at most 50 characters.")
        if not name or not name.strip():
            raise ValueError("ItemTemplate name is required.")

        self._code = code
        self._name = name.strip()
        self._description = description
        self._category_id = category_id
        self._base_unit_id = base_unit_id
        self._attributes: List[Dict[str, Any]] = attributes or []
        self._is_active = is_active

        self._validate_attributes()

    # ── Private validation ────────────────────────────────────────────────────

    def _validate_attributes(self) -> None:
        """Ensure each attribute definition has a 'key' and 'label', and optional 'values'."""
        seen_keys: set = set()
        for attr in self._attributes:
            key = attr.get("key")
            label = attr.get("label")
            values = attr.get("values", [])
            
            if not key or not str(key).strip():
                raise ValueError("Each attribute must have a non-empty 'key'.")
            if not label or not str(label).strip():
                raise ValueError("Each attribute must have a non-empty 'label'.")
                
            if not isinstance(values, list):
                raise ValueError("Attribute 'values' must be a list of strings.")
                
            key_upper = str(key).upper()
            if key_upper in seen_keys:
                raise ValueError(f"Duplicate attribute key: '{key_upper}'.")
            seen_keys.add(key_upper)
            
            # Ensure values are clean
            attr["values"] = [str(v).strip() for v in values if str(v).strip()]

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def category_id(self) -> Optional[uuid.UUID]:
        return self._category_id

    @property
    def base_unit_id(self) -> Optional[uuid.UUID]:
        return self._base_unit_id

    @property
    def attributes(self) -> List[Dict[str, Any]]:
        return list(self._attributes)

    @property
    def is_active(self) -> bool:
        return self._is_active

    # ── Behaviour ─────────────────────────────────────────────────────────────

    def update(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        base_unit_id: Optional[uuid.UUID] = None,
        attributes: Optional[List[Dict[str, Any]]] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        if name is not None:
            if not name.strip():
                raise ValueError("Name cannot be empty.")
            self._name = name.strip()
        if description is not None:
            self._description = description
        if category_id is not None:
            self._category_id = category_id
        if base_unit_id is not None:
            self._base_unit_id = base_unit_id
        if attributes is not None:
            self._attributes = attributes
            self._validate_attributes()
        if is_active is not None:
            self._is_active = is_active
        self._touch()

    def attribute_keys(self) -> List[str]:
        """Return attribute keys in template-defined order."""
        return [str(a["key"]).upper() for a in self._attributes]
