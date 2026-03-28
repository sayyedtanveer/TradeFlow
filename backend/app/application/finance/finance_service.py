"""Finance Application Service — Invoice & Payment logic."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.finance_models import (
    InvoiceModel,
    InvoiceLineModel,
    SupplierInvoiceModel,
    PaymentModel,
    SupplierPaymentModel,
    FinancialTransactionModel,
)
from backend.app.infrastructure.persistence.models.sales_models import (
    SalesOrderModel,
    SalesOrderLineModel,
    ClientModel,
)
from backend.app.infrastructure.persistence.models.purchase_order_model import PurchaseOrderModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel


class FinanceService:
    """
    Finance application service.
    Handles: Invoice creation from SO, Payments, Ledger entries, AR/AP.
    All operations enforce multi-tenancy and audit trail via ledger.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    #  Invoice Numbering
    # ------------------------------------------------------------------ #
    async def _next_invoice_number(self, tenant_id: uuid.UUID, prefix: str = "INV") -> str:
        result = await self.session.execute(
            text("SELECT nextval('invoice_seq')")
        )
        seq = result.scalar()
        return f"{prefix}-{seq:06d}"

    async def _next_supplier_invoice_number(self, tenant_id: uuid.UUID) -> str:
        result = await self.session.execute(
            text("SELECT nextval('supplier_invoice_seq')")
        )
        seq = result.scalar()
        return f"SINV-{seq:06d}"

    async def _next_payment_number(self, tenant_id: uuid.UUID) -> str:
        result = await self.session.execute(
            text("SELECT nextval('payment_seq')")
        )
        seq = result.scalar()
        return f"PAY-{seq:06d}"

    async def _next_supplier_payment_number(self, tenant_id: uuid.UUID) -> str:
        result = await self.session.execute(
            text("SELECT nextval('supplier_payment_seq')")
        )
        seq = result.scalar()
        return f"SPAY-{seq:06d}"

    # ------------------------------------------------------------------ #
    #  Invoice CRUD
    # ------------------------------------------------------------------ #
    async def create_invoice_from_sales_order(
        self,
        tenant_id: uuid.UUID,
        sales_order_id: uuid.UUID,
        created_by: uuid.UUID,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
    ) -> InvoiceModel:
        """
        Create an invoice by snapshotting the sales order lines.
        One invoice per sales order enforced.
        SO must be in DELIVERED status.
        """
        # 1. Fetch SO
        so_q = await self.session.execute(
            select(SalesOrderModel).where(
                SalesOrderModel.id == sales_order_id,
                SalesOrderModel.tenant_id == tenant_id,
                SalesOrderModel.is_deleted == False,
            )
        )
        so: Optional[SalesOrderModel] = so_q.scalar_one_or_none()
        if so is None:
            raise ValueError("Sales order not found")
        if so.status != "DELIVERED":
            raise ValueError(f"Invoice can only be created for DELIVERED orders (current: {so.status})")

        # 2. Check no existing invoice
        existing = await self.session.execute(
            select(InvoiceModel).where(
                InvoiceModel.sales_order_id == sales_order_id,
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Invoice already exists for this sales order")

        # 3. Fetch client for snapshot
        client_q = await self.session.execute(
            select(ClientModel).where(ClientModel.id == so.client_id)
        )
        client: ClientModel = client_q.scalar_one()

        # 4. Compute due date from payment_terms_days
        today = date.today()
        due_date = date(today.year, today.month, today.day)
        from datetime import timedelta
        due_date = today + timedelta(days=client.payment_terms_days or 30)

        # 5. Create invoice
        invoice_number = await self._next_invoice_number(tenant_id)
        invoice = InvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            sales_order_id=sales_order_id,
            client_id=so.client_id,
            client_name=client.name,
            client_address=client.address,
            client_gst_number=client.gst_number,
            status="DRAFT",
            invoice_date=today,
            due_date=due_date,
            subtotal=float(so.subtotal),
            discount_amount=float(so.discount_amount),
            tax_amount=float(so.tax_amount),
            grand_total=float(so.grand_total),
            paid_amount=0.0,
            notes=notes,
            terms=terms,
            created_by=created_by,
        )
        self.session.add(invoice)
        await self.session.flush()  # get invoice.id

        # 6. Snapshot SO lines → invoice lines
        lines_q = await self.session.execute(
            select(SalesOrderLineModel).where(
                SalesOrderLineModel.sales_order_id == sales_order_id
            )
        )
        so_lines = lines_q.scalars().all()
        for sol in so_lines:
            il = InvoiceLineModel(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                product_id=sol.product_id,
                product_type=sol.product_type,
                description=f"Product {sol.product_id}",
                quantity=int(sol.quantity),
                unit_price=float(sol.unit_price),
                discount_amount=0.0,
                tax_rate=float(sol.tax_rate),
                tax_amount=float(sol.tax_amount),
                total=float(sol.line_total),
            )
            self.session.add(il)

        # 7. Create ledger entry (debit AR, credit Revenue)
        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="invoice",
            reference_id=invoice.id,
            account_type="RECEIVABLE",
            debit=float(so.grand_total),
            credit=0.0,
            description=f"Invoice {invoice_number} created for SO {so.order_number}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def create_invoice_manual(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        invoice_date: date,
        due_date: date,
        lines_data: List[dict],
        created_by: uuid.UUID,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
    ) -> InvoiceModel:
        """Create a manual invoice not tied to a sales order."""
        client_q = await self.session.execute(
            select(ClientModel).where(ClientModel.id == client_id, ClientModel.tenant_id == tenant_id)
        )
        client: ClientModel = client_q.scalar_one()

        subtotal = sum(d["quantity"] * d["unit_price"] - d.get("discount_amount", 0) for d in lines_data)
        tax_amount = sum(d.get("tax_amount", 0) for d in lines_data)
        grand_total = subtotal + tax_amount

        invoice_number = await self._next_invoice_number(tenant_id)
        invoice = InvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            client_id=client_id,
            client_name=client.name,
            client_address=client.address,
            client_gst_number=client.gst_number,
            status="DRAFT",
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=subtotal,
            discount_amount=sum(d.get("discount_amount", 0) for d in lines_data),
            tax_amount=tax_amount,
            grand_total=grand_total,
            paid_amount=0.0,
            notes=notes,
            terms=terms,
            created_by=created_by,
        )
        self.session.add(invoice)
        await self.session.flush()

        for ld in lines_data:
            il = InvoiceLineModel(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                product_id=uuid.UUID(ld["product_id"]),
                product_type=ld.get("product_type", "finished"),
                description=ld.get("description"),
                quantity=int(ld["quantity"]),
                unit_price=float(ld["unit_price"]),
                discount_amount=float(ld.get("discount_amount", 0)),
                tax_rate=float(ld.get("tax_rate", 0)),
                tax_amount=float(ld.get("tax_amount", 0)),
                total=float(ld["total"]),
            )
            self.session.add(il)

        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="invoice",
            reference_id=invoice.id,
            account_type="RECEIVABLE",
            debit=grand_total,
            credit=0.0,
            description=f"Invoice {invoice_number} created",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def send_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        """Mark invoice as SENT."""
        invoice = await self._get_invoice(tenant_id, invoice_id)
        if invoice.status != "DRAFT":
            raise ValueError("Only DRAFT invoices can be sent")
        invoice.status = "SENT"
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def void_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        """Void an invoice."""
        invoice = await self._get_invoice(tenant_id, invoice_id)
        if invoice.status == "PAID":
            raise ValueError("Cannot void a fully paid invoice")
        invoice.status = "VOID"
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        client_id: Optional[uuid.UUID] = None,
        overdue_only: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(InvoiceModel).where(
            InvoiceModel.tenant_id == tenant_id,
            InvoiceModel.is_deleted == False,
        )
        if status:
            q = q.where(InvoiceModel.status == status)
        if client_id:
            q = q.where(InvoiceModel.client_id == client_id)
        if overdue_only:
            q = q.where(InvoiceModel.due_date < date.today(), InvoiceModel.status.in_(["SENT", "PARTIAL"]))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_q)).scalar()

        q = q.order_by(InvoiceModel.invoice_date.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(q)
        invoices = result.scalars().all()

        return {
            "items": invoices,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    async def get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        return await self._get_invoice(tenant_id, invoice_id)

    async def _get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceModel:
        result = await self.session.execute(
            select(InvoiceModel).where(
                InvoiceModel.id == invoice_id,
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
            )
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ValueError("Invoice not found")
        return invoice

    # ------------------------------------------------------------------ #
    #  Payments
    # ------------------------------------------------------------------ #
    async def record_payment(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: str,
        created_by: uuid.UUID,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PaymentModel:
        """Record a customer payment. Enforces: amount <= balance_due."""
        invoice = await self._get_invoice(tenant_id, invoice_id)
        balance = float(invoice.grand_total) - float(invoice.paid_amount)

        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if amount > balance + 0.001:  # small tolerance for rounding
            raise ValueError(f"Payment amount ({amount}) exceeds balance due ({balance:.2f})")

        payment_number = await self._next_payment_number(tenant_id)
        payment = PaymentModel(
            tenant_id=tenant_id,
            payment_number=payment_number,
            invoice_id=invoice_id,
            client_id=invoice.client_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(payment)

        # Update invoice paid_amount and status
        new_paid = float(invoice.paid_amount) + amount
        invoice.paid_amount = new_paid
        new_balance = float(invoice.grand_total) - new_paid

        if new_balance <= 0.001:
            invoice.status = "PAID"
        elif new_paid > 0:
            invoice.status = "PARTIAL"

        # Ledger: credit AR (reducing receivable), debit Cash
        await self.session.flush()
        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="payment",
            reference_id=payment.id,
            account_type="CASH",
            debit=amount,
            credit=0.0,
            description=f"Payment {payment_number} received for Invoice {invoice.invoice_number}",
            created_by=created_by,
        )
        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="payment",
            reference_id=payment.id,
            account_type="RECEIVABLE",
            debit=0.0,
            credit=amount,
            description=f"AR reduced by Payment {payment_number}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def list_payments(
        self,
        tenant_id: uuid.UUID,
        invoice_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(PaymentModel).where(PaymentModel.tenant_id == tenant_id)
        if invoice_id:
            q = q.where(PaymentModel.invoice_id == invoice_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_q)).scalar()

        q = q.order_by(PaymentModel.payment_date.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(q)
        return {
            "items": result.scalars().all(),
            "total": total,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }

    # ------------------------------------------------------------------ #
    #  Supplier Invoices (AP)
    # ------------------------------------------------------------------ #
    async def create_supplier_invoice(
        self,
        tenant_id: uuid.UUID,
        supplier_id: uuid.UUID,
        purchase_order_id: Optional[uuid.UUID],
        supplier_invoice_ref: Optional[str],
        invoice_date: date,
        due_date: date,
        subtotal: float,
        tax_amount: float,
        grand_total: float,
        created_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> SupplierInvoiceModel:
        supplier_q = await self.session.execute(
            select(SupplierModel).where(SupplierModel.id == supplier_id, SupplierModel.tenant_id == tenant_id)
        )
        supplier = supplier_q.scalar_one()

        invoice_number = await self._next_supplier_invoice_number(tenant_id)
        si = SupplierInvoiceModel(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            supplier_invoice_ref=supplier_invoice_ref,
            purchase_order_id=purchase_order_id,
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            status="PENDING",
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_amount=tax_amount,
            grand_total=grand_total,
            paid_amount=0.0,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(si)
        await self.session.flush()

        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="supplier_invoice",
            reference_id=si.id,
            account_type="PAYABLE",
            debit=0.0,
            credit=grand_total,
            description=f"Supplier Invoice {invoice_number} from {supplier.name}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(si)
        return si

    async def record_supplier_payment(
        self,
        tenant_id: uuid.UUID,
        supplier_invoice_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: str,
        created_by: uuid.UUID,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SupplierPaymentModel:
        si_q = await self.session.execute(
            select(SupplierInvoiceModel).where(
                SupplierInvoiceModel.id == supplier_invoice_id,
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.is_deleted == False,
            )
        )
        si = si_q.scalar_one_or_none()
        if si is None:
            raise ValueError("Supplier invoice not found")

        balance = float(si.grand_total) - float(si.paid_amount)
        if amount > balance + 0.001:
            raise ValueError(f"Payment ({amount}) exceeds balance ({balance:.2f})")

        pay_number = await self._next_supplier_payment_number(tenant_id)
        payment = SupplierPaymentModel(
            tenant_id=tenant_id,
            payment_number=pay_number,
            supplier_invoice_id=supplier_invoice_id,
            supplier_id=si.supplier_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=created_by,
        )
        self.session.add(payment)

        new_paid = float(si.paid_amount) + amount
        si.paid_amount = new_paid
        if float(si.grand_total) - new_paid <= 0.001:
            si.status = "PAID"
        elif new_paid > 0:
            si.status = "PARTIAL"

        await self.session.flush()
        await self._create_ledger_entry(
            tenant_id=tenant_id,
            reference_type="supplier_payment",
            reference_id=payment.id,
            account_type="PAYABLE",
            debit=amount,
            credit=0.0,
            description=f"Supplier Payment {pay_number}",
            created_by=created_by,
        )

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def list_supplier_invoices(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        supplier_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(SupplierInvoiceModel).where(
            SupplierInvoiceModel.tenant_id == tenant_id,
            SupplierInvoiceModel.is_deleted == False,
        )
        if status:
            q = q.where(SupplierInvoiceModel.status == status)
        if supplier_id:
            q = q.where(SupplierInvoiceModel.supplier_id == supplier_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_q)).scalar()
        q = q.order_by(SupplierInvoiceModel.invoice_date.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(q)
        return {
            "items": result.scalars().all(),
            "total": total,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }

    # ------------------------------------------------------------------ #
    #  Dashboard / Analytics
    # ------------------------------------------------------------------ #
    async def get_ar_summary(self, tenant_id: uuid.UUID) -> dict:
        """Accounts Receivable summary."""
        result = await self.session.execute(
            select(
                func.sum(InvoiceModel.grand_total).label("total_billed"),
                func.sum(InvoiceModel.paid_amount).label("total_collected"),
                func.sum(InvoiceModel.grand_total - InvoiceModel.paid_amount).label("total_outstanding"),
                func.count(InvoiceModel.id).filter(
                    InvoiceModel.status.in_(["SENT", "PARTIAL"])
                ).label("open_count"),
            ).where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.is_deleted == False,
            )
        )
        row = result.one()
        return {
            "total_billed": float(row.total_billed or 0),
            "total_collected": float(row.total_collected or 0),
            "total_outstanding": float(row.total_outstanding or 0),
            "open_count": row.open_count or 0,
        }

    async def get_ap_summary(self, tenant_id: uuid.UUID) -> dict:
        """Accounts Payable summary."""
        result = await self.session.execute(
            select(
                func.sum(SupplierInvoiceModel.grand_total).label("total_payable"),
                func.sum(SupplierInvoiceModel.paid_amount).label("total_paid"),
                func.sum(SupplierInvoiceModel.grand_total - SupplierInvoiceModel.paid_amount).label("outstanding"),
                func.count(SupplierInvoiceModel.id).filter(
                    SupplierInvoiceModel.status.in_(["PENDING", "PARTIAL"])
                ).label("open_count"),
            ).where(
                SupplierInvoiceModel.tenant_id == tenant_id,
                SupplierInvoiceModel.is_deleted == False,
            )
        )
        row = result.one()
        return {
            "total_payable": float(row.total_payable or 0),
            "total_paid": float(row.total_paid or 0),
            "outstanding": float(row.outstanding or 0),
            "open_count": row.open_count or 0,
        }

    async def get_cash_flow(self, tenant_id: uuid.UUID, months: int = 6) -> List[dict]:
        """Monthly cash flow (collections vs payments)."""
        result = await self.session.execute(
            text("""
                SELECT
                    date_trunc('month', created_at) as month,
                    SUM(debit) FILTER (WHERE account_type = 'CASH') as cash_in,
                    SUM(credit) FILTER (WHERE account_type = 'PAYABLE') as cash_out
                FROM financial_transactions
                WHERE tenant_id = :tenant_id
                    AND created_at >= NOW() - INTERVAL ':months months'
                GROUP BY date_trunc('month', created_at)
                ORDER BY month
            """),
            {"tenant_id": tenant_id, "months": months}
        )
        return [
            {"month": str(row.month)[:7], "cash_in": float(row.cash_in or 0), "cash_out": float(row.cash_out or 0)}
            for row in result
        ]

    async def get_revenue_by_month(self, tenant_id: uuid.UUID, months: int = 6) -> List[dict]:
        """Revenue per month from invoices."""
        result = await self.session.execute(
            text("""
                SELECT
                    date_trunc('month', invoice_date) as month,
                    COUNT(*) as invoice_count,
                    SUM(grand_total) as revenue,
                    SUM(paid_amount) as collected
                FROM invoices
                WHERE tenant_id = :tenant_id AND is_deleted = false
                    AND invoice_date >= NOW() - INTERVAL ':months months'
                GROUP BY date_trunc('month', invoice_date)
                ORDER BY month
            """),
            {"tenant_id": tenant_id, "months": months}
        )
        return [
            {
                "month": str(row.month)[:7],
                "invoice_count": row.invoice_count,
                "revenue": float(row.revenue or 0),
                "collected": float(row.collected or 0),
            }
            for row in result
        ]

    # ------------------------------------------------------------------ #
    #  Overdue Invoice Check
    # ------------------------------------------------------------------ #
    async def mark_overdue_invoices(self, tenant_id: Optional[uuid.UUID] = None) -> int:
        """Background job: mark SENT/PARTIAL invoices as OVERDUE if past due_date."""
        from sqlalchemy import update
        today = date.today()
        q = (
            update(InvoiceModel)
            .where(
                InvoiceModel.due_date < today,
                InvoiceModel.status.in_(["SENT", "PARTIAL"]),
                InvoiceModel.is_deleted == False,
            )
            .values(status="OVERDUE")
        )
        if tenant_id:
            q = q.where(InvoiceModel.tenant_id == tenant_id)

        result = await self.session.execute(q)
        await self.session.commit()
        return result.rowcount

    # ------------------------------------------------------------------ #
    #  Ledger
    # ------------------------------------------------------------------ #
    async def _create_ledger_entry(
        self,
        tenant_id: uuid.UUID,
        reference_type: str,
        reference_id: uuid.UUID,
        account_type: str,
        debit: float,
        credit: float,
        description: str,
        created_by: Optional[uuid.UUID] = None,
    ) -> FinancialTransactionModel:
        entry = FinancialTransactionModel(
            tenant_id=tenant_id,
            reference_type=reference_type,
            reference_id=reference_id,
            account_type=account_type,
            debit=debit,
            credit=credit,
            description=description,
            created_by=created_by,
        )
        self.session.add(entry)
        return entry

    async def get_ledger(
        self,
        tenant_id: uuid.UUID,
        reference_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        q = select(FinancialTransactionModel).where(FinancialTransactionModel.tenant_id == tenant_id)
        if reference_type:
            q = q.where(FinancialTransactionModel.reference_type == reference_type)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(count_q)).scalar()
        q = q.order_by(FinancialTransactionModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(q)
        return {
            "items": result.scalars().all(),
            "total": total,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }
