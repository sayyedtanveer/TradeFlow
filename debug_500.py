import asyncio
import uuid
import sys

from backend.app.config import get_settings
from backend.app.domain.product.entities.item_template import ItemTemplate
from backend.app.infrastructure.persistence.database import create_engine, create_session_factory
from backend.app.infrastructure.persistence.repositories.item_template_repository import ItemTemplateRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.infrastructure.events.event_dispatcher import EventDispatcher

async def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    
    tenant_id = uuid.UUID('b5ef68c4-18be-4fa6-a439-a23c34877550')
    
    async with session_factory() as session:
        repo = ItemTemplateRepository(session)
        dispatcher = EventDispatcher(None)
        uow = SQLAlchemyUnitOfWork(session, dispatcher)
        
        template = ItemTemplate(
            tenant_id=tenant_id,
            code="DEBUG_CODE_1",
            name="Debug Name",
            attributes=[{"key": "SIZE", "label": "Size"}],
        )
        
        try:
            print("Saving template...")
            await repo.save(template)
            print("Committing UOW...")
            await uow.commit()
            print("SUCCESS. ID:", template.id)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
