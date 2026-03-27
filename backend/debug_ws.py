import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import create_engine
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.application.bom.handlers.routing_handlers import RoutingHandlers
from backend.app.interfaces.api.v1.schemas.routing_schemas import WorkstationCreate
import uuid

async def test_create_workstation():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    tenant_id = uuid.uuid4()
    
    # Create request
    ws_create = WorkstationCreate(
        code=f"TEST-{uuid.uuid4().hex[:4]}",
        name="Test WS",
        capacity_hours_per_day=8,
        hourly_rate=10.0
    )
    
    from backend.app.infrastructure.persistence.database import create_session_factory
    Session = create_session_factory(engine)
    
    async with Session() as session:
        # We don't have event_dispatcher, mock it or pass None if allowed
        class DummyDispatcher:
            async def publish(self, *args, **kwargs): pass
            
        uow = SQLAlchemyUnitOfWork(session, DummyDispatcher())
        from backend.app.infrastructure.persistence.repositories.workstation_repository import WorkstationRepository
        from backend.app.infrastructure.persistence.repositories.bom_repository import BOMRepository
        from backend.app.infrastructure.persistence.repositories.operation_repository import OperationRepository
        handler = RoutingHandlers(uow, BOMRepository(session), WorkstationRepository(uow), OperationRepository(uow))
        
        from backend.app.application.bom.commands.routing_commands import AddWorkstationCommand
        cmd = AddWorkstationCommand(tenant_id=tenant_id, **ws_create.model_dump())
        try:
            ws_id = await handler.handle_add_workstation(cmd)
            print(f"Success! WS ID: {ws_id}")
            await uow.commit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_create_workstation())
