"""
Notification Service for WebSocket-based operational alerts.
Broadcasts real-time alerts for key manufacturing events.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from backend.app.infrastructure.websocket.connection_manager import ConnectionManager


@dataclass
class NotificationPayload:
    """Standard notification payload structure."""
    id: str
    type: str
    title: str
    message: str
    data: dict
    timestamp: str
    priority: str = "info"  # info, warning, error, success


class NotificationService:
    """
    Service for broadcasting operational notifications via WebSocket.
    
    Notification Types:
    - WO_STATUS_CHANGED: Work order state transition
    - MATERIAL_SHORTAGE: Material shortage detected
    - QC_RESULT: Quality inspection result (approved/rejected)
    - DELIVERY_STATUS: Delivery order status change
    - INVENTORY_ALERT: Low stock or stock out
    - PRODUCTION_ALERT: Production issues or milestones
    """

    # Notification Type Constants
    WO_STATUS_CHANGED = "WO_STATUS_CHANGED"
    MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE"
    QC_RESULT = "QC_RESULT"
    DELIVERY_STATUS = "DELIVERY_STATUS"
    INVENTORY_ALERT = "INVENTORY_ALERT"
    PRODUCTION_ALERT = "PRODUCTION_ALERT"
    DOCUMENT_GENERATED = "DOCUMENT_GENERATED"

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    def _create_payload(
        self,
        notification_type: str,
        title: str,
        message: str,
        data: dict,
        priority: str = "info",
    ) -> NotificationPayload:
        """Create a standardized notification payload."""
        return NotificationPayload(
            id=str(uuid.uuid4()),
            type=notification_type,
            title=title,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            priority=priority,
        )

    async def notify_wo_status_change(
        self,
        tenant_id: uuid.UUID,
        wo_id: uuid.UUID,
        wo_number: str,
        old_status: str,
        new_status: str,
        assigned_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Notify about work order status change.
        
        Sent to: Assigned user (if any) and all tenant users.
        """
        payload = self._create_payload(
            notification_type=self.WO_STATUS_CHANGED,
            title=f"Work Order {wo_number} Status Changed",
            message=f"Status changed from {old_status} to {new_status}",
            data={
                "wo_id": str(wo_id),
                "wo_number": wo_number,
                "old_status": old_status,
                "new_status": new_status,
            },
            priority="info",
        )

        # Notify assigned user if specified
        if assigned_user_id:
            await self.connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=assigned_user_id,
                message_type="notification",
                payload=payload.__dict__,
            )

        # Broadcast to all tenant users
        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_material_shortage(
        self,
        tenant_id: uuid.UUID,
        wo_id: uuid.UUID,
        wo_number: str,
        material_id: uuid.UUID,
        material_name: str,
        required_quantity: float,
        available_quantity: float,
    ) -> None:
        """
        Notify about material shortage.
        
        Sent to: All tenant users (storekeepers, planners).
        """
        payload = self._create_payload(
            notification_type=self.MATERIAL_SHORTAGE,
            title=f"Material Shortage for {wo_number}",
            message=f"Material '{material_name}' shortage: required {required_quantity}, available {available_quantity}",
            data={
                "wo_id": str(wo_id),
                "wo_number": wo_number,
                "material_id": str(material_id),
                "material_name": material_name,
                "required_quantity": required_quantity,
                "available_quantity": available_quantity,
                "shortage_quantity": required_quantity - available_quantity,
            },
            priority="warning",
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_qc_result(
        self,
        tenant_id: uuid.UUID,
        inspection_id: uuid.UUID,
        wo_id: uuid.UUID,
        wo_number: str,
        result: str,
        inspector_id: Optional[uuid.UUID] = None,
        assigned_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Notify about QC inspection result.
        
        Sent to: Inspector, assigned user, and all tenant users.
        """
        title = f"QC Result for {wo_number}"
        if result == "APPROVED":
            message = f"Quality inspection approved for {wo_number}"
            priority = "success"
        elif result == "REJECTED":
            message = f"Quality inspection rejected for {wo_number}"
            priority = "error"
        else:
            message = f"Quality inspection result: {result} for {wo_number}"
            priority = "info"

        payload = self._create_payload(
            notification_type=self.QC_RESULT,
            title=title,
            message=message,
            data={
                "inspection_id": str(inspection_id),
                "wo_id": str(wo_id),
                "wo_number": wo_number,
                "result": result,
            },
            priority=priority,
        )

        # Notify inspector
        if inspector_id:
            await self.connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=inspector_id,
                message_type="notification",
                payload=payload.__dict__,
            )

        # Notify assigned user
        if assigned_user_id:
            await self.connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=assigned_user_id,
                message_type="notification",
                payload=payload.__dict__,
            )

        # Broadcast to tenant
        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_delivery_status(
        self,
        tenant_id: uuid.UUID,
        delivery_id: uuid.UUID,
        delivery_number: str,
        old_status: str,
        new_status: str,
        client_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Notify about delivery status change.
        
        Sent to: All tenant users.
        """
        payload = self._create_payload(
            notification_type=self.DELIVERY_STATUS,
            title=f"Delivery {delivery_number} Status Changed",
            message=f"Status changed from {old_status} to {new_status}",
            data={
                "delivery_id": str(delivery_id),
                "delivery_number": delivery_number,
                "old_status": old_status,
                "new_status": new_status,
            },
            priority="info",
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_inventory_alert(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        material_name: str,
        current_stock: float,
        reorder_level: float,
        alert_type: str = "low_stock",
    ) -> None:
        """
        Notify about inventory alerts (low stock, stock out).
        
        Sent to: All tenant users (storekeepers).
        """
        if alert_type == "stock_out":
            title = f"Stock Out: {material_name}"
            message = f"Material '{material_name}' is out of stock"
            priority = "error"
        else:
            title = f"Low Stock: {material_name}"
            message = f"Material '{material_name}' is below reorder level: {current_stock} < {reorder_level}"
            priority = "warning"

        payload = self._create_payload(
            notification_type=self.INVENTORY_ALERT,
            title=title,
            message=message,
            data={
                "material_id": str(material_id),
                "material_name": material_name,
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "alert_type": alert_type,
            },
            priority=priority,
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_production_alert(
        self,
        tenant_id: uuid.UUID,
        wo_id: uuid.UUID,
        wo_number: str,
        alert_type: str,
        message: str,
        assigned_user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Notify about production alerts (scrap, downtime, milestones).
        
        Sent to: Assigned user and all tenant users.
        """
        payload = self._create_payload(
            notification_type=self.PRODUCTION_ALERT,
            title=f"Production Alert for {wo_number}",
            message=message,
            data={
                "wo_id": str(wo_id),
                "wo_number": wo_number,
                "alert_type": alert_type,
            },
            priority="warning",
        )

        if assigned_user_id:
            await self.connection_manager.send_to_user(
                tenant_id=tenant_id,
                user_id=assigned_user_id,
                message_type="notification",
                payload=payload.__dict__,
            )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id=tenant_id,
            message_type="notification",
            payload=payload.__dict__,
        )

    async def notify_document_generated(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        document_type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        entity_number: str,
        user_id: uuid.UUID,
    ) -> None:
        """
        Notify about document generation.
        
        Sent to: User who requested the document.
        """
        payload = self._create_payload(
            notification_type=self.DOCUMENT_GENERATED,
            title=f"Document Generated: {document_type}",
            message=f"{document_type} for {entity_type} {entity_number} has been generated",
            data={
                "document_id": str(document_id),
                "document_type": document_type,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "entity_number": entity_number,
            },
            priority="success",
        )

        await self.connection_manager.send_to_user(
            tenant_id=tenant_id,
            user_id=user_id,
            message_type="notification",
            payload=payload.__dict__,
        )
