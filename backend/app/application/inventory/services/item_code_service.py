from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.item_code_sequence_model import ItemCodeSequenceModel
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel
from backend.app.infrastructure.persistence.models.material_category_model import MaterialCategoryModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


ITEM_TYPE_PREFIX = {
    "raw": "RM",
    "RAW": "RM",
    "rm": "RM",
    "finished": "FG",
    "finished_good": "FG",
    "FG": "FG",
    "semi_finished": "SF",
    "semi-finished": "SF",
    "SF": "SF",
}


def normalize_item_type(value: str | None) -> str:
    key = str(value or "raw").strip().replace(" ", "_")
    return ITEM_TYPE_PREFIX.get(key, ITEM_TYPE_PREFIX.get(key.lower(), "RM"))


def normalize_item_code(value: str) -> str:
    normalized = " ".join(str(value or "").split()).strip().upper()
    if not normalized:
        raise ValueError("Item code is required.")
    if len(normalized) > 50:
        raise ValueError("Item code must be at most 50 characters.")
    return normalized


def normalize_category_prefix(value: str | None, *, fallback_name: str = "GEN") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(value or "").upper())
    if not cleaned:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", fallback_name.upper())
    return (cleaned or "GEN")[:10]


class ItemCodeService:
    """Tenant-scoped item code generation backed by an atomic sequence table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def validate_manual_code(
        self,
        *,
        tenant_id: uuid.UUID,
        code: str,
        target: str,
    ) -> str:
        normalized = normalize_item_code(code)
        if await self.code_exists(tenant_id=tenant_id, code=normalized, target=target):
            raise ValueError(f"Item code '{normalized}' already exists in this tenant.")
        return normalized

    async def generate(
        self,
        *,
        tenant_id: uuid.UUID,
        item_type: str,
        category_id: uuid.UUID,
        target: str,
    ) -> str:
        category = await self._session.scalar(
            select(MaterialCategoryModel).where(
                MaterialCategoryModel.id == category_id,
                MaterialCategoryModel.tenant_id == tenant_id,
                MaterialCategoryModel.is_deleted.is_(False),
            )
        )
        if category is None:
            raise ValueError("Category is required for item code generation.")

        type_prefix = normalize_item_type(item_type)
        category_prefix = normalize_category_prefix(category.code_prefix, fallback_name=category.name)
        if category.code_prefix != category_prefix:
            category.code_prefix = category_prefix

        sequence = await self._session.scalar(
            select(ItemCodeSequenceModel)
            .where(
                ItemCodeSequenceModel.tenant_id == tenant_id,
                ItemCodeSequenceModel.item_type == type_prefix,
                ItemCodeSequenceModel.category_id == category_id,
            )
            .with_for_update()
        )
        if sequence is None:
            sequence = ItemCodeSequenceModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                item_type=type_prefix,
                category_id=category_id,
                next_number=await self._initial_next_number(
                    tenant_id=tenant_id,
                    type_prefix=type_prefix,
                    category_prefix=category_prefix,
                    target=target,
                ),
            )
            self._session.add(sequence)
            await self._session.flush()

        while True:
            candidate = f"{type_prefix}-{category_prefix}-{sequence.next_number:04d}"
            sequence.next_number += 1
            if not await self.code_exists(tenant_id=tenant_id, code=candidate, target=target):
                return candidate

    async def code_exists(self, *, tenant_id: uuid.UUID, code: str, target: str) -> bool:
        model = MaterialModel if target == "material" else ItemTemplateModel
        stmt = select(model.id).where(
            model.tenant_id == tenant_id,
            func.upper(model.code) == normalize_item_code(code),
            model.is_deleted.is_(False),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def _initial_next_number(
        self,
        *,
        tenant_id: uuid.UUID,
        type_prefix: str,
        category_prefix: str,
        target: str,
    ) -> int:
        model = MaterialModel if target == "material" else ItemTemplateModel
        like_prefix = f"{type_prefix}-{category_prefix}-"
        rows = (
            await self._session.execute(
                select(model.code).where(
                    model.tenant_id == tenant_id,
                    model.code.ilike(f"{like_prefix}%"),
                    model.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        max_seen = 0
        for code in rows:
            suffix = str(code).replace(like_prefix, "", 1)
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
        return max_seen + 1
