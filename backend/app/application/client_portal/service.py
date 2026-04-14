from __future__ import annotations

import hashlib
import io
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.finance.notification_service import NotificationService
from backend.app.infrastructure.persistence.models.finance_models import InvoiceModel, NotificationModel
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.models.sales_models import (
    ClientAddressModel,
    ClientModel,
    SalesOrderLineModel,
    SalesOrderModel,
)
from backend.app.infrastructure.persistence.models.user_model import (
    ClientNotificationSettingsModel,
    PasswordResetTokenModel,
    UserModel,
)


ORDER_TIMELINE = ["DRAFT", "CONFIRMED", "PRODUCTION", "QC", "READY", "SHIPPED", "DELIVERED"]
STATUS_SEQUENCE = {
    "DRAFT": 0,
    "CONFIRMED": 1,
    "PRODUCTION": 2,
    "READY": 4,
    "SHIPPED": 5,
    "DELIVERED": 6,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


def _status_rank(status: str) -> int:
    if status == "CANCELLED":
        return -1
    return STATUS_SEQUENCE.get(str(status or "").upper(), 0)


def _payment_link(invoice_number: str) -> str:
    return f"mailto:billing@medtrack.local?subject=Payment%20for%20{invoice_number}"


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_minimal_pdf(lines: list[str]) -> bytes:
    buffer = io.StringIO()
    offsets: list[int] = []

    def write(chunk: str) -> None:
        buffer.write(chunk)

    write("%PDF-1.4\n")
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]

    content_lines = ["BT", "/F1 12 Tf", "50 760 Td", "14 TL"]
    for idx, line in enumerate(lines):
        if idx == 0:
            content_lines.append(f"({_pdf_escape(line)}) Tj")
        else:
            content_lines.append(f"T* ({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines)
    objects.append(f"<< /Length {len(content_stream.encode('utf-8'))} >>\nstream\n{content_stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(buffer.getvalue().encode("utf-8")))
        write(f"{index} 0 obj\n{obj}\nendobj\n")

    xref_offset = len(buffer.getvalue().encode("utf-8"))
    write(f"xref\n0 {len(objects) + 1}\n")
    write("0000000000 65535 f \n")
    for offset in offsets:
        write(f"{offset:010d} 00000 n \n")
    write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF")
    return buffer.getvalue().encode("utf-8")


class ClientPortalService:
    def __init__(
        self,
        session: AsyncSession,
        password_hasher,
        jwt_handler,
        email_service=None,
        environment: str = "development",
    ) -> None:
        self.session = session
        self.password_hasher = password_hasher
        self.jwt_handler = jwt_handler
        self.email_service = email_service
        self.environment = environment

    async def login_client(self, email: str, password: str, tenant_id: uuid.UUID) -> dict[str, Any]:
        user = await self._get_client_user_by_email(email=email, tenant_id=tenant_id)
        if not user or not self.password_hasher.verify(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is inactive")
        if not user.client_id:
            raise ValueError("Client account is not linked to a client record")

        token = self.jwt_handler.create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=str(user.role),
            extra_claims={"cid": str(user.client_id)},
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "client_id": user.client_id,
            "email": user.email,
            "role": user.role,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
        }

    async def refresh_client_session(self, payload: dict[str, Any]) -> dict[str, str]:
        cid = payload.get("cid")
        if not cid:
            raise ValueError("Client token is missing client context")
        token = self.jwt_handler.create_access_token(
            user_id=str(payload["sub"]),
            tenant_id=str(payload["tid"]),
            role=str(payload["role"]),
            extra_claims={"cid": str(cid)},
        )
        return {"access_token": token, "token_type": "bearer"}

    async def request_password_reset(self, email: str, tenant_id: uuid.UUID) -> dict[str, Any]:
        user = await self._get_client_user_by_email(email=email, tenant_id=tenant_id)
        response: dict[str, Any] = {
            "message": "If an active client account exists, reset instructions have been generated.",
        }
        if not user:
            return response

        await self._expire_active_reset_tokens(user.id)
        token = secrets.token_urlsafe(32)
        token_model = PasswordResetTokenModel(
            tenant_id=tenant_id,
            user_id=user.id,
            token_hash=self._hash_token(token),
            expires_at=_utc_now() + timedelta(hours=1),
        )
        self.session.add(token_model)
        await self.session.commit()

        if self.email_service and getattr(self.email_service, "send_email", None):
            await self.email_service.send_email(
                to=user.email,
                subject="MedTrack client portal password reset",
                body=(
                    "Use this reset token in the client portal password reset form: "
                    f"{token}"
                ),
            )

        if self.environment.lower() != "production":
            response["reset_token"] = token
        return response

    async def reset_password(self, token: str, new_password: str) -> dict[str, str]:
        token_row = await self._get_reset_token(token)
        if token_row is None:
            raise ValueError("Reset token is invalid or expired")

        user = await self.session.get(UserModel, token_row.user_id)
        if user is None or str(user.role).lower() != "client":
            raise ValueError("Reset token does not belong to a valid client user")

        user.hashed_password = self.password_hasher.hash(new_password)
        token_row.used_at = _utc_now()
        await self.session.commit()
        return {"message": "Password updated successfully"}

    async def get_dashboard(self, tenant_id: uuid.UUID, client_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        user, client = await self._get_user_and_client(tenant_id, client_id, user_id)
        await self._ensure_notifications(tenant_id, client_id, user_id)

        orders_total = await self.session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.client_id == client_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        active_orders = await self.session.scalar(
            select(func.count(SalesOrderModel.id)).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.client_id == client_id,
                SalesOrderModel.is_deleted.is_(False),
                SalesOrderModel.status.not_in(["DELIVERED", "CANCELLED"]),
            )
        )
        total_spent = await self.session.scalar(
            select(func.coalesce(func.sum(InvoiceModel.paid_amount), 0)).where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.client_id == client_id,
                InvoiceModel.is_deleted.is_(False),
            )
        )
        open_balance = await self.session.scalar(
            select(func.coalesce(func.sum(InvoiceModel.grand_total - InvoiceModel.paid_amount), 0)).where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.client_id == client_id,
                InvoiceModel.is_deleted.is_(False),
                InvoiceModel.status.not_in(["PAID", "VOID"]),
            )
        )
        recent_orders = await self._query_orders(
            tenant_id=tenant_id,
            client_id=client_id,
            page=1,
            page_size=5,
        )

        credit = self._serialize_credit(client)
        return {
            "welcome_name": user.first_name,
            "client_name": client.name,
            "kpis": {
                "orders": int(orders_total or 0),
                "active_orders": int(active_orders or 0),
                "spent": _money(total_spent),
                "open_balance": _money(open_balance),
                "credit_limit": credit["credit_limit"],
                "credit_used": credit["credit_used"],
                "credit_remaining": credit["credit_remaining"],
            },
            "credit": credit,
            "recent_orders": recent_orders["items"],
        }

    async def list_orders(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self._query_orders(tenant_id, client_id, page, page_size, status, search)

    async def get_order(self, tenant_id: uuid.UUID, client_id: uuid.UUID, order_id: uuid.UUID) -> dict[str, Any]:
        order = await self._get_client_order(tenant_id, client_id, order_id)
        return await self._serialize_order(order, include_lines=True)

    async def get_order_tracking(self, tenant_id: uuid.UUID, client_id: uuid.UUID, order_id: uuid.UUID) -> dict[str, Any]:
        order = await self._get_client_order(tenant_id, client_id, order_id)
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "current_status": order.status,
            "timeline": self._build_timeline(order.status),
            "tracking": {
                "estimated_delivery_date": order.delivery_date,
                "shipping_status": order.status,
                "tracking_reference": None,
                "tracking_notes": "Shipment references are assigned when logistics dispatches the order.",
            },
        }

    async def create_reorder(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        source_order_id: uuid.UUID,
        lines_input: Optional[list[dict[str, Any]]] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        source_order = await self._get_client_order(tenant_id, client_id, source_order_id)
        source_lines = source_order.lines or []
        requested_lines = lines_input or [
            {
                "product_id": line.product_id,
                "product_type": line.product_type,
                "uom_id": line.uom_id,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_rate": line.tax_rate,
            }
            for line in source_lines
        ]
        if not requested_lines:
            raise ValueError("Cannot reorder an order with no lines")

        order = SalesOrderModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client_id,
            order_number=await self._next_order_number(tenant_id),
            order_date=date.today().isoformat(),
            delivery_date=(date.today() + timedelta(days=7)).isoformat(),
            status="DRAFT",
            payment_status="PENDING",
            subtotal=0,
            discount_amount=0,
            tax_amount=0,
            grand_total=0,
            notes=notes or f"Reorder created from {source_order.order_number}",
            created_by="client-portal",
            is_active=True,
            is_deleted=False,
        )
        self.session.add(order)
        await self.session.flush()

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        availability: list[dict[str, Any]] = []
        for raw_line in requested_lines:
            quantity = Decimal(str(raw_line["quantity"]))
            unit_price = Decimal(str(raw_line.get("unit_price") or 0))
            tax_rate = Decimal(str(raw_line.get("tax_rate") or 0))
            tax_amount = (quantity * unit_price * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            line_total = (quantity * unit_price + tax_amount).quantize(Decimal("0.01"))
            subtotal += (quantity * unit_price).quantize(Decimal("0.01"))
            tax_total += tax_amount

            line = SalesOrderLineModel(
                id=uuid.uuid4(),
                sales_order_id=order.id,
                product_id=raw_line["product_id"],
                product_type=raw_line["product_type"],
                uom_id=raw_line["uom_id"],
                quantity=quantity,
                unit_price=unit_price,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                line_total=line_total,
                allocated_quantity=0,
                shipped_quantity=0,
                backorder_quantity=0,
                status="PENDING",
            )
            self.session.add(line)
            availability.append(await self._estimate_availability(tenant_id, line.product_id, quantity))

        order.subtotal = subtotal
        order.tax_amount = tax_total
        order.grand_total = subtotal + tax_total

        client = await self._get_client(tenant_id, client_id)
        credit = self._serialize_credit(client)
        projected_usage = credit["credit_used"] + _money(order.grand_total)
        credit_warning = credit["credit_limit"] is not None and projected_usage > float(credit["credit_limit"])
        await self.session.commit()

        created_order = await self._get_client_order(tenant_id, client_id, order.id)
        result = await self._serialize_order(created_order, include_lines=True)
        result["credit_warning"] = credit_warning
        result["availability"] = availability
        return result

    async def request_order_cancellation(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> dict[str, str]:
        order = await self._get_client_order(tenant_id, client_id, order_id)
        if order.status in {"DELIVERED", "CANCELLED"}:
            raise ValueError("This order can no longer be cancelled")

        order.notes = ((order.notes or "").strip() + "\nClient requested cancellation on " + date.today().isoformat()).strip()
        await self.session.commit()

        notification_service = NotificationService(self.session)
        for role in ("admin", "tenant_admin", "manager"):
            await notification_service.broadcast_to_role(
                tenant_id=tenant_id,
                role=role,
                notification_type="CLIENT_CANCEL_REQUEST",
                title=f"Cancellation requested for {order.order_number}",
                message=f"Client requested cancellation for order {order.order_number}.",
                reference_type="sales_order",
                reference_id=order.id,
            )
        return {"status": "requested"}

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        query = select(InvoiceModel).where(
            InvoiceModel.tenant_id == tenant_id,
            InvoiceModel.client_id == client_id,
            InvoiceModel.is_deleted.is_(False),
        )
        if status:
            normalized = status.upper()
            if normalized == "UNPAID":
                query = query.where(InvoiceModel.status.not_in(["PAID", "VOID"]))
            elif normalized == "OVERDUE":
                query = query.where(
                    or_(InvoiceModel.status == "OVERDUE", InvoiceModel.due_date < date.today()),
                    InvoiceModel.status.not_in(["PAID", "VOID"]),
                )
            else:
                query = query.where(InvoiceModel.status == normalized)

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        query = query.order_by(InvoiceModel.invoice_date.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        invoices = result.scalars().all()

        return {
            "items": [self._serialize_invoice(inv) for inv in invoices],
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    async def get_invoice(self, tenant_id: uuid.UUID, client_id: uuid.UUID, invoice_id: uuid.UUID) -> dict[str, Any]:
        invoice = await self._get_client_invoice(tenant_id, client_id, invoice_id)
        return self._serialize_invoice(invoice)

    async def build_invoice_pdf(self, tenant_id: uuid.UUID, client_id: uuid.UUID, invoice_id: uuid.UUID) -> tuple[str, bytes]:
        invoice = await self._get_client_invoice(tenant_id, client_id, invoice_id)
        lines = [
            f"Invoice {invoice.invoice_number}",
            f"Client: {invoice.client_name}",
            f"Invoice Date: {invoice.invoice_date}",
            f"Due Date: {invoice.due_date}",
            f"Status: {invoice.status}",
            f"Total: {_money(invoice.grand_total):.2f}",
            "",
        ]
        for idx, line in enumerate(invoice.lines or [], start=1):
            lines.append(
                f"{idx}. {line.description or line.product_type} x {line.quantity} @ {_money(line.unit_price):.2f} = {_money(line.total):.2f}"
            )
        lines.extend(
            [
                "",
                f"Paid: {_money(invoice.paid_amount):.2f}",
                f"Balance Due: {_money(invoice.grand_total - invoice.paid_amount):.2f}",
            ]
        )
        return invoice.invoice_number, _build_minimal_pdf(lines)

    async def get_credit(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> dict[str, Any]:
        client = await self._get_client(tenant_id, client_id)
        return self._serialize_credit(client)

    async def get_profile(self, tenant_id: uuid.UUID, client_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        user, client = await self._get_user_and_client(tenant_id, client_id, user_id)
        settings = await self._get_or_create_notification_settings(tenant_id, client_id, user_id)
        addresses = await self.list_addresses(tenant_id, client_id)
        return {
            "company": {
                "id": str(client.id),
                "code": client.code,
                "name": client.name,
                "email": client.email,
                "phone": client.phone,
                "address": client.address,
                "gst_number": client.gst_number,
                "payment_terms_days": client.payment_terms_days,
                "credit_limit": _money(client.credit_limit) if client.credit_limit is not None else None,
                "credit_used": _money(client.credit_used),
            },
            "contact": {
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
            "addresses": addresses,
            "notifications": self._serialize_notification_settings(settings),
        }

    async def update_profile(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        user, _client = await self._get_user_and_client(tenant_id, client_id, user_id)
        if payload.get("first_name"):
            user.first_name = payload["first_name"]
        if payload.get("last_name"):
            user.last_name = payload["last_name"]
        if payload.get("email"):
            user.email = payload["email"]
        await self.session.commit()
        return {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }

    async def list_addresses(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(ClientAddressModel).where(
                ClientAddressModel.tenant_id == tenant_id,
                ClientAddressModel.client_id == client_id,
            ).order_by(ClientAddressModel.is_default.desc(), ClientAddressModel.created_at.desc())
        )
        return [self._serialize_address(row) for row in result.scalars().all()]

    async def create_address(self, tenant_id: uuid.UUID, client_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
        await self._get_client(tenant_id, client_id)
        address = ClientAddressModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client_id,
            **payload,
        )
        self.session.add(address)
        await self._ensure_single_default_address(client_id, payload["type"], address.id if payload.get("is_default") else None)
        await self.session.commit()
        await self.session.refresh(address)
        return self._serialize_address(address)

    async def update_address(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        address_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        address = await self._get_address(tenant_id, client_id, address_id)
        for key, value in payload.items():
            setattr(address, key, value)
        if payload.get("is_default"):
            await self._ensure_single_default_address(client_id, address.type, address.id)
        await self.session.commit()
        await self.session.refresh(address)
        return self._serialize_address(address)

    async def delete_address(self, tenant_id: uuid.UUID, client_id: uuid.UUID, address_id: uuid.UUID) -> dict[str, str]:
        address = await self._get_address(tenant_id, client_id, address_id)
        await self.session.delete(address)
        await self.session.commit()
        return {"status": "deleted"}

    async def get_notifications(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        await self._ensure_notifications(tenant_id, client_id, user_id)
        query = select(NotificationModel).where(
            NotificationModel.tenant_id == tenant_id,
            NotificationModel.user_id == user_id,
        )
        if unread_only:
            query = query.where(NotificationModel.is_read.is_(False))
        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        unread_count = await self.session.scalar(
            select(func.count()).where(
                NotificationModel.tenant_id == tenant_id,
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
        )
        query = query.order_by(NotificationModel.sent_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        items = [self._serialize_notification(n) for n in result.scalars().all()]
        return {
            "items": items,
            "total": int(total or 0),
            "unread_count": int(unread_count or 0),
            "page": page,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    async def mark_notification_read(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> dict[str, int]:
        notification = await self.session.scalar(
            select(NotificationModel).where(
                NotificationModel.id == notification_id,
                NotificationModel.tenant_id == tenant_id,
                NotificationModel.user_id == user_id,
            )
        )
        if notification is None:
            raise ValueError("Notification not found")
        notification.is_read = True
        await self.session.commit()
        return {"marked_read": 1}

    async def get_notification_settings(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        settings = await self._get_or_create_notification_settings(tenant_id, client_id, user_id)
        return self._serialize_notification_settings(settings)

    async def update_notification_settings(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        settings = await self._get_or_create_notification_settings(tenant_id, client_id, user_id)
        for key, value in payload.items():
            setattr(settings, key, value)
        await self.session.commit()
        return self._serialize_notification_settings(settings)

    async def submit_support_request(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
        subject: str,
        message: str,
    ) -> dict[str, Any]:
        ticket_id = uuid.uuid4()
        client = await self._get_client(tenant_id, client_id)
        notification_service = NotificationService(self.session)
        for role in ("admin", "tenant_admin", "manager"):
            await notification_service.broadcast_to_role(
                tenant_id=tenant_id,
                role=role,
                notification_type="CLIENT_SUPPORT",
                title=f"Client support request: {subject}",
                message=f"{client.name}: {message}",
                reference_type="support_request",
                reference_id=ticket_id,
            )
        await notification_service.send(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type="CLIENT_SUPPORT",
            title="Support request received",
            message="Your support request has been sent to the MedTrack team.",
            reference_type="support_request",
            reference_id=ticket_id,
        )
        return {"ticket_id": str(ticket_id), "status": "submitted"}

    async def get_support_faq(self) -> list[dict[str, str]]:
        return [
            {
                "question": "How do I reorder a previous order?",
                "answer": "Open Reorder, pick a previous order, adjust the quantities, and submit the draft for review.",
            },
            {
                "question": "Why does an invoice show overdue?",
                "answer": "Invoices become overdue once the due date passes and the invoice is not fully paid.",
            },
            {
                "question": "What happens when I exceed my credit limit?",
                "answer": "You can still prepare a draft reorder, but the portal will warn you before the order is confirmed.",
            },
        ]

    async def _query_orders(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        page: int,
        page_size: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        query = select(SalesOrderModel).where(
            SalesOrderModel.tenant_id == tenant_id,
            SalesOrderModel.client_id == client_id,
            SalesOrderModel.is_deleted.is_(False),
        )
        if status:
            query = query.where(SalesOrderModel.status == status.upper())
        if search:
            query = query.where(SalesOrderModel.order_number.ilike(f"%{search.strip()}%"))

        total = await self.session.scalar(select(func.count()).select_from(query.subquery()))
        query = query.order_by(SalesOrderModel.order_date.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        items = [await self._serialize_order(row, include_lines=False) for row in result.scalars().all()]
        return {
            "items": items,
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
            "pages": ((int(total or 0) + page_size - 1) // page_size) if total else 0,
        }

    async def _serialize_order(self, order: SalesOrderModel, include_lines: bool) -> dict[str, Any]:
        lines = []
        availability = []
        for line in order.lines or []:
            line_payload = await self._serialize_order_line(order.tenant_id, line)
            lines.append(line_payload)
            availability.append(line_payload["availability"])
        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "client_id": str(order.client_id),
            "order_date": order.order_date,
            "delivery_date": order.delivery_date,
            "status": order.status,
            "payment_status": order.payment_status,
            "subtotal": _money(order.subtotal),
            "discount_amount": _money(order.discount_amount),
            "tax_amount": _money(order.tax_amount),
            "grand_total": _money(order.grand_total),
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "timeline": self._build_timeline(order.status),
            "lines": lines if include_lines else [],
            "line_count": len(order.lines or []),
            "tracking": {
                "estimated_delivery_date": order.delivery_date,
                "shipping_status": order.status,
                "tracking_reference": None,
            },
            "availability": availability if include_lines else [],
        }

    async def _serialize_order_line(self, tenant_id: uuid.UUID, line: SalesOrderLineModel) -> dict[str, Any]:
        product_name, product_code = await self._resolve_product_name(tenant_id, line.product_id)
        availability = await self._estimate_availability(tenant_id, line.product_id, Decimal(str(line.quantity)))
        return {
            "id": str(line.id),
            "product_id": str(line.product_id),
            "product_type": line.product_type,
            "product_name": product_name,
            "product_code": product_code,
            "uom_id": str(line.uom_id),
            "quantity": _money(line.quantity),
            "unit_price": _money(line.unit_price),
            "tax_rate": _money(line.tax_rate),
            "tax_amount": _money(line.tax_amount),
            "line_total": _money(line.line_total),
            "allocated_quantity": _money(line.allocated_quantity),
            "shipped_quantity": _money(line.shipped_quantity),
            "backorder_quantity": _money(line.backorder_quantity),
            "status": line.status,
            "availability": availability,
        }

    def _serialize_invoice(self, invoice: InvoiceModel) -> dict[str, Any]:
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "sales_order_id": str(invoice.sales_order_id) if invoice.sales_order_id else None,
            "client_id": str(invoice.client_id),
            "client_name": invoice.client_name,
            "client_address": invoice.client_address,
            "client_gst_number": invoice.client_gst_number,
            "status": invoice.status,
            "invoice_date": str(invoice.invoice_date),
            "due_date": str(invoice.due_date),
            "subtotal": _money(invoice.subtotal),
            "discount_amount": _money(invoice.discount_amount),
            "tax_amount": _money(invoice.tax_amount),
            "grand_total": _money(invoice.grand_total),
            "paid_amount": _money(invoice.paid_amount),
            "balance_due": _money(invoice.grand_total - invoice.paid_amount),
            "notes": invoice.notes,
            "terms": invoice.terms,
            "created_at": invoice.created_at.isoformat(),
            "payment_link": _payment_link(invoice.invoice_number),
            "lines": [
                {
                    "id": str(line.id),
                    "product_id": str(line.product_id),
                    "product_type": line.product_type,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price": _money(line.unit_price),
                    "discount_amount": _money(line.discount_amount),
                    "tax_rate": _money(line.tax_rate),
                    "tax_amount": _money(line.tax_amount),
                    "total": _money(line.total),
                }
                for line in (invoice.lines or [])
            ],
            "payments": [
                {
                    "id": str(payment.id),
                    "payment_number": payment.payment_number,
                    "amount": _money(payment.amount),
                    "payment_date": str(payment.payment_date),
                    "payment_method": payment.payment_method,
                }
                for payment in (invoice.payments or [])
            ],
        }

    def _serialize_credit(self, client: ClientModel) -> dict[str, Any]:
        limit = _money(client.credit_limit) if client.credit_limit is not None else None
        used = _money(client.credit_used)
        remaining = (limit - used) if limit is not None else None
        usage_percent = round((used / limit) * 100, 2) if limit not in (None, 0) else None
        return {
            "client_id": str(client.id),
            "credit_limit": limit,
            "credit_used": used,
            "credit_remaining": round(remaining, 2) if remaining is not None else None,
            "usage_percent": usage_percent,
            "is_over_limit": bool(remaining is not None and remaining < 0),
            "is_low_credit": bool(remaining is not None and limit is not None and remaining <= limit * 0.2),
        }

    def _serialize_address(self, address: ClientAddressModel) -> dict[str, Any]:
        return {
            "id": str(address.id),
            "type": address.type,
            "label": address.label,
            "contact_name": address.contact_name,
            "address_line1": address.address_line1,
            "address_line2": address.address_line2,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
            "phone": address.phone,
            "email": address.email,
            "is_default": address.is_default,
            "created_at": address.created_at.isoformat(),
            "updated_at": address.updated_at.isoformat(),
        }

    def _serialize_notification(self, notification: NotificationModel) -> dict[str, Any]:
        return {
            "id": str(notification.id),
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "reference_type": notification.reference_type,
            "reference_id": str(notification.reference_id) if notification.reference_id else None,
            "is_read": notification.is_read,
            "sent_at": notification.sent_at.isoformat(),
        }

    def _serialize_notification_settings(self, settings: ClientNotificationSettingsModel) -> dict[str, Any]:
        return {
            "order_confirmed": settings.order_confirmed,
            "order_shipped": settings.order_shipped,
            "order_delivered": settings.order_delivered,
            "invoice_overdue": settings.invoice_overdue,
            "low_credit": settings.low_credit,
            "marketing": settings.marketing,
        }

    def _build_timeline(self, current_status: str) -> list[dict[str, str]]:
        status = str(current_status or "").upper()
        if status == "CANCELLED":
            return [
                {"label": step.title(), "status": "completed" if idx <= 1 else "cancelled"}
                for idx, step in enumerate(ORDER_TIMELINE)
            ]

        rank = _status_rank(status)
        timeline = []
        for index, step in enumerate(ORDER_TIMELINE):
            step_rank = 3 if step == "QC" else index
            if rank > step_rank:
                state = "completed"
            elif rank == step_rank:
                state = "current"
            else:
                state = "upcoming"
            timeline.append({"label": step.title(), "status": state})
        return timeline

    async def _estimate_availability(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        requested_quantity: Decimal,
    ) -> dict[str, Any]:
        material = await self.session.scalar(
            select(MaterialModel).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
        if material is None:
            return {
                "source": "planning",
                "available_quantity": None,
                "status": "unknown",
                "backorder_warning": False,
                "message": "Availability will be confirmed during planning.",
            }

        available = Decimal(str(material.current_stock or 0)) - Decimal(str(material.reserved_stock or 0))
        return {
            "source": "material_stock",
            "available_quantity": _money(available),
            "status": "available" if available >= requested_quantity else "backorder",
            "backorder_warning": available < requested_quantity,
            "message": (
                "Requested quantity exceeds currently available stock."
                if available < requested_quantity
                else "Stock appears available."
            ),
        }

    async def _resolve_product_name(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> tuple[str, Optional[str]]:
        variant = await self.session.scalar(
            select(ItemVariantModel).where(
                ItemVariantModel.id == product_id,
                ItemVariantModel.tenant_id == tenant_id,
                ItemVariantModel.is_deleted.is_(False),
            )
        )
        if variant is not None:
            return variant.name, variant.code
        material = await self.session.scalar(
            select(MaterialModel).where(
                MaterialModel.id == product_id,
                MaterialModel.tenant_id == tenant_id,
                MaterialModel.is_deleted.is_(False),
            )
        )
        if material is not None:
            return material.name, material.code
        return f"Product {str(product_id)[:8]}", None

    async def _get_client_user_by_email(self, email: str, tenant_id: uuid.UUID) -> Optional[UserModel]:
        return await self.session.scalar(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
                UserModel.role == "client",
            )
        )

    async def _get_user_and_client(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[UserModel, ClientModel]:
        user = await self.session.scalar(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.client_id == client_id,
                UserModel.is_deleted.is_(False),
            )
        )
        if user is None:
            raise ValueError("Client user not found")
        client = await self._get_client(tenant_id, client_id)
        return user, client

    async def _get_client(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> ClientModel:
        client = await self.session.scalar(
            select(ClientModel).where(
                ClientModel.id == client_id,
                ClientModel.tenant_id == tenant_id,
                ClientModel.is_deleted.is_(False),
            )
        )
        if client is None:
            raise ValueError("Client not found")
        return client

    async def _get_client_order(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> SalesOrderModel:
        order = await self.session.scalar(
            select(SalesOrderModel).where(
                SalesOrderModel.id == order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.client_id == client_id,
                SalesOrderModel.is_deleted.is_(False),
            )
        )
        if order is None:
            raise ValueError("Order not found")
        return order

    async def _get_client_invoice(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> InvoiceModel:
        invoice = await self.session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.id == invoice_id,
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.client_id == client_id,
                InvoiceModel.is_deleted.is_(False),
            )
        )
        if invoice is None:
            raise ValueError("Invoice not found")
        return invoice

    async def _get_address(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        address_id: uuid.UUID,
    ) -> ClientAddressModel:
        address = await self.session.scalar(
            select(ClientAddressModel).where(
                ClientAddressModel.id == address_id,
                ClientAddressModel.tenant_id == tenant_id,
                ClientAddressModel.client_id == client_id,
            )
        )
        if address is None:
            raise ValueError("Address not found")
        return address

    async def _get_or_create_notification_settings(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ClientNotificationSettingsModel:
        settings = await self.session.scalar(
            select(ClientNotificationSettingsModel).where(
                ClientNotificationSettingsModel.user_id == user_id,
            )
        )
        if settings is None:
            settings = ClientNotificationSettingsModel(
                tenant_id=tenant_id,
                client_id=client_id,
                user_id=user_id,
            )
            self.session.add(settings)
            await self.session.commit()
            await self.session.refresh(settings)
        return settings

    async def _ensure_single_default_address(
        self,
        client_id: uuid.UUID,
        address_type: str,
        active_address_id: Optional[uuid.UUID],
    ) -> None:
        if active_address_id is None:
            return
        result = await self.session.execute(
            select(ClientAddressModel).where(
                ClientAddressModel.client_id == client_id,
                ClientAddressModel.type == address_type,
                ClientAddressModel.id != active_address_id,
                ClientAddressModel.is_default.is_(True),
            )
        )
        for row in result.scalars().all():
            row.is_default = False

    async def _ensure_notifications(self, tenant_id: uuid.UUID, client_id: uuid.UUID, user_id: uuid.UUID) -> None:
        settings = await self._get_or_create_notification_settings(tenant_id, client_id, user_id)
        notification_service = NotificationService(self.session)

        async def exists(notification_type: str, ref_type: str, ref_id: uuid.UUID) -> bool:
            return bool(
                await self.session.scalar(
                    select(func.count()).where(
                        NotificationModel.tenant_id == tenant_id,
                        NotificationModel.user_id == user_id,
                        NotificationModel.type == notification_type,
                        NotificationModel.reference_type == ref_type,
                        NotificationModel.reference_id == ref_id,
                    )
                )
            )

        async def notify_orders(order_status: str, notification_type: str, title_suffix: str, message: str, enabled: bool) -> None:
            if not enabled:
                return
            result = await self.session.execute(
                select(SalesOrderModel).where(
                    SalesOrderModel.tenant_id == tenant_id,
                    SalesOrderModel.client_id == client_id,
                    SalesOrderModel.status == order_status,
                ).limit(5)
            )
            for order in result.scalars().all():
                if not await exists(notification_type, "sales_order", order.id):
                    await notification_service.send(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        notification_type=notification_type,
                        title=f"Order {order.order_number} {title_suffix}",
                        message=message,
                        reference_type="sales_order",
                        reference_id=order.id,
                    )

        await notify_orders("CONFIRMED", "ORDER_CONFIRMED", "confirmed", "Your order has been confirmed and is being planned.", settings.order_confirmed)
        await notify_orders("SHIPPED", "ORDER_SHIPPED", "shipped", "Your order is on the way.", settings.order_shipped)
        await notify_orders("DELIVERED", "ORDER_DELIVERED", "delivered", "Your order has been marked as delivered.", settings.order_delivered)

        if settings.invoice_overdue:
            overdue_invoices = await self.session.execute(
                select(InvoiceModel).where(
                    InvoiceModel.tenant_id == tenant_id,
                    InvoiceModel.client_id == client_id,
                    or_(InvoiceModel.status == "OVERDUE", InvoiceModel.due_date < date.today()),
                    InvoiceModel.status.not_in(["PAID", "VOID"]),
                ).limit(5)
            )
            for invoice in overdue_invoices.scalars().all():
                if not await exists("INVOICE_OVERDUE", "invoice", invoice.id):
                    await notification_service.send(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        notification_type="INVOICE_OVERDUE",
                        title=f"Invoice {invoice.invoice_number} overdue",
                        message="One of your invoices is overdue. Please review the invoice list.",
                        reference_type="invoice",
                        reference_id=invoice.id,
                    )

        if settings.low_credit:
            client = await self._get_client(tenant_id, client_id)
            credit = self._serialize_credit(client)
            if (credit["is_low_credit"] or credit["is_over_limit"]) and not await exists("LOW_CREDIT", "client", client.id):
                await notification_service.send(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    notification_type="LOW_CREDIT",
                    title="Low credit remaining",
                    message="Your available credit is running low. Draft orders above the limit will be flagged.",
                    reference_type="client",
                    reference_id=client.id,
                )

    async def _expire_active_reset_tokens(self, user_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
        )
        for token in result.scalars().all():
            token.used_at = _utc_now()

    async def _get_reset_token(self, token: str) -> Optional[PasswordResetTokenModel]:
        token_hash = self._hash_token(token)
        return await self.session.scalar(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == token_hash,
                PasswordResetTokenModel.used_at.is_(None),
                PasswordResetTokenModel.expires_at > _utc_now(),
            )
        )

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def _next_order_number(self, tenant_id: uuid.UUID) -> str:
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"SO-{today}-"
        count = await self.session.scalar(
            select(func.count()).where(
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.order_number.like(f"{prefix}%"),
            )
        )
        return f"{prefix}{int(count or 0) + 1:03d}"
