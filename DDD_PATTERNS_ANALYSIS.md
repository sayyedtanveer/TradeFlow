# DDD Implementation Patterns Analysis

## Overview
The MedTrack application follows Domain-Driven Design (DDD) principles with a clear separation of concerns across multiple bounded contexts (domains). This document outlines the specific patterns, implementations, and file structures used.

---

## 1. VALUE OBJECTS

### Definition
Value Objects are immutable objects that represent a measurable, assignable, or describable aspect of the domain. Equality is based on value, not identity.

### Implementation Pattern
- **Base Class**: [backend/app/domain/shared/base_value_object.py](backend/app/domain/shared/base_value_object.py)
  - Enforces immutability via ABC
  - Requires `_validate()` method override
  - Implements value-based equality (`__eq__` and `__hash__`)
  - Provides default `__repr__`

### Key Characteristics
```python
class BaseValueObject(ABC):
    def __post_init__(self) -> None:
        self._validate()
    
    @abstractmethod
    def _validate(self) -> None:
        """Raise ValueError or DomainException if value is invalid."""
    
    def __eq__(self, other: Any) -> bool:
        # Value-based equality, not identity
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__
```

### Identified Value Objects
Currently, the codebase leverages standard Python types (Decimal, Enum) for value objects:
- **Decimal**: For monetary amounts and quantities (e.g., `quantity`, `scrap_percentage`, `reorder_level`)
- **Enum**: For statuses and types
  - `MaterialType` (RAW, FINISHED) - [backend/app/domain/inventory/entities/material.py](backend/app/domain/inventory/entities/material.py)
  - `BatchStatus` (IN_STOCK, DEPLETED, EXPIRED) - [backend/app/domain/inventory/entities/batch.py](backend/app/domain/inventory/entities/batch.py)

**Note**: No custom Value Object classes currently exist. Future candidates:
- `Money` (amount + currency)
- `DateRange` (valid_from + valid_to)
- `ProductCode`
- `MaterialCode`

---

## 2. ENTITIES

### Definition
Entities have identity (id + tenant_id). Unlike Value Objects, two entities are equal if they have the same identity, not the same values. Entities encapsulate domain logic.

### Base Implementation
**File**: [backend/app/domain/shared/base_entity.py](backend/app/domain/shared/base_entity.py)

```python
class BaseEntity(ABC):
    def __init__(
        self,
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_deleted: bool = False,
        deleted_at: Optional[datetime] = None,
    ) -> None:
        self._id: uuid.UUID = id or uuid.uuid4()
        self._tenant_id: uuid.UUID = tenant_id or uuid.uuid4()
        self._created_at: datetime = created_at or datetime.now(timezone.utc)
        self._updated_at: datetime = updated_at or datetime.now(timezone.utc)
        self._is_deleted: bool = is_deleted
        self._deleted_at: Optional[datetime] = deleted_at
        self._domain_events: List["DomainEvent"] = []
```

### Characteristics
- **Tenant Isolation**: All entities must have a `tenant_id` for multi-tenancy
- **Soft Delete**: Support for `is_deleted` flag (no hard deletes)
- **Timestamps**: Auto-tracked `created_at` and `updated_at`
- **Domain Events**: `_domain_events` collection for event-driven architecture
- **Immutable Primary Key**: UUID-based identity

### Key Domain Entities

#### Inventory Domain
- **Material** - [backend/app/domain/inventory/entities/material.py](backend/app/domain/inventory/entities/material.py)
  - Represents inventory items (raw or finished goods)
  - Domain rules:
    - `current_stock >= 0`
    - `reserved_stock <= current_stock`
    - Stock mutations logged as transactions
  - Properties: `code`, `name`, `material_type`, `current_stock`, `reserved_stock`, `is_batch_tracked`, `is_serialized`

- **Batch** - [backend/app/domain/inventory/entities/batch.py](backend/app/domain/inventory/entities/batch.py)
  - Represents tracked batches of batch-tracked materials
  - Domain rules:
    - `batch_number` is immutable
    - `expiry_date` must be in future
    - `quantity >= 0`
  - Properties: `material_id`, `batch_number`, `quantity`, `remaining_quantity`, `expiry_date`, `status`

- **InventoryTransaction** - [backend/app/domain/inventory/entities/inventory_transaction.py](backend/app/domain/inventory/entities/inventory_transaction.py)
  - Immutable audit log of stock movements
  - Types: IN, OUT, TRANSFER, ADJUSTMENT
  - Maintains full traceability

- **SerialNumber** - [backend/app/domain/inventory/entities/serial_number.py](backend/app/domain/inventory/entities/serial_number.py)
  - Tracks individual serialized units
  - Props: `material_id`, `serial_number`, `status`, `location_id`

- **Location** - [backend/app/domain/inventory/entities/location.py](backend/app/domain/inventory/entities/location.py)
  - Physical storage locations
  - Used for warehouse/bin organization

- **UnitOfMeasure** - [backend/app/domain/inventory/entities/unit_of_measure.py](backend/app/domain/inventory/entities/unit_of_measure.py)
  - Standard units (kg, pcs, m, L, etc.)
  - Base unit for conversions

- **UOMConversion** - [backend/app/domain/inventory/entities/uom_conversion.py](backend/app/domain/inventory/entities/uom_conversion.py)
  - Cross-unit conversion rates (e.g., 1000 g = 1 kg)

#### BOM Domain
- **BillOfMaterial (BOM)** - [backend/app/domain/bom/entities/bom.py](backend/app/domain/bom/entities/bom.py)
  - Aggregate root for bill of materials
  - Domain rules:
    - Must reference exactly one product (template_id OR variant_id, not both)
    - Version must be non-empty
    - Can be activated/deactivated
    - Enforces no self-references
  - Key methods:
    - `add_line(BOMLine)` - Adds line item with circular dependency check
    - `add_operation(BOMOperation)` - Adds manufacturing operation
    - `activate()` / `deactivate()`
  - Properties: `version`, `valid_from`, `valid_to`, `is_active`, `lines`, `operations`

- **BOMLine** - [backend/app/domain/bom/entities/bom_line.py](backend/app/domain/bom/entities/bom_line.py)
  - Component line in BOM
  - Domain rules:
    - Must reference exactly one component (material_id OR template_id OR variant_id)
    - `quantity > 0`
    - `scrap_percentage` between 0-100
  - Properties: `bom_id`, `quantity`, `scrap_percentage`, `unit_id`, `material_id`, `template_id`, `variant_id`

- **BOMOperation** - [backend/app/domain/bom/entities/bom_operation.py](backend/app/domain/bom/entities/bom_operation.py)
  - Manufacturing routing steps

- **Operation** - [backend/app/domain/bom/entities/operation.py](backend/app/domain/bom/entities/operation.py)
  - Reusable manufacturing operations

- **Workstation** - [backend/app/domain/bom/entities/workstation.py](backend/app/domain/bom/entities/workstation.py)
  - Equipment/locations where operations occur

#### Product Domain (Configurable Master Data)
- **ItemTemplate** - [backend/app/domain/product/entities/item_template.py](backend/app/domain/product/entities/item_template.py)
  - Product master record with configurable attributes
  - Supports variants via attribute definitions
  - Props: `code`, `name`, `attributes`, `category_id`, `base_unit_id`

- **ItemVariant** - [backend/app/domain/product/entities/item_variant.py](backend/app/domain/product/entities/item_variant.py)
  - Specific product configuration (e.g., "Size-S, Color-Red")
  - Props: `template_id`, `variant_key`, `attribute_values`, `standard_cost`, `selling_price`

- **MaterialCategory** - [backend/app/domain/inventory/entities/material_category.py](backend/app/domain/inventory/entities/material_category.py)
  - Hierarchical product classification

---

## 3. SERVICES

### Domain Services vs Application Services

#### Domain Services
Located in: `backend/app/domain/{domain}/services/`

**Purpose**: Encapsulate domain logic that doesn't naturally belong to a single entity or uses multiple entities.

**File**: [backend/app/domain/bom/services/bom_validation_service.py](backend/app/domain/bom/services/bom_validation_service.py)

Example - **BOMValidationService**:
```python
class BOMValidationService:
    def __init__(self, bom_provider: BOMProvider):
        self._bom_provider = bom_provider
    
    async def validate_no_circular_dependencies(
        self, tenant_id: uuid.UUID, new_bom: BillOfMaterial, max_depth: int = 20
    ) -> None:
        """Validates that BOM won't introduce circular references."""
        # Uses BOMProvider protocol for dependency injection
        # Recursively checks entire BOM hierarchy
```

**Pattern**: Injection via protocols/interfaces for loose coupling.

Other Domain Services:
- [backend/app/domain/bom/services/bom_browser_service.py](backend/app/domain/bom/services/bom_browser_service.py) - BOM navigation/traversal
- [backend/app/domain/bom/services/cost_rollup_service.py](backend/app/domain/bom/services/cost_rollup_service.py) - Cost calculations

#### Application Services (Handlers)
Located in: `backend/app/application/{domain}/handlers/`

**Purpose**: Orchestrate user requests using domain services and repositories. Implement Command/Query patterns.

**File**: [backend/app/application/inventory/handlers/inventory_handlers.py](backend/app/application/inventory/handlers/inventory_handlers.py)

Example - **CreateMaterialHandler**:
```python
class CreateMaterialHandler:
    def __init__(self, material_repo: MaterialRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = material_repo
        self._uow = uow
    
    async def handle(self, cmd: CreateMaterialCommand) -> MaterialResult:
        if await self._repo.code_exists(cmd.code, cmd.tenant_id):
            raise ValueError(f"Material with code '{cmd.code}' already exists...")
        
        material = Material(...)
        await self._repo.save(material)
        await self._uow.commit()  # Dispatches domain events
        return MaterialResult(...)
```

**Pattern**: 
- One handler per command/query
- Repository for data access
- Unit of Work for transaction management
- Domain events dispatched on commit

---

## 4. REPOSITORIES

### Implementation Pattern

**Base Repository Interface**: [backend/app/domain/shared/interfaces/repository_interface.py](backend/app/domain/shared/interfaces/repository_interface.py)

```python
class IRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[T]:
        """Return entity or None (excludes soft-deleted)."""
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """Insert or update the entity."""
    
    @abstractmethod
    async def delete(self, id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """Soft-delete the entity."""
    
    @abstractmethod
    async def list(self, tenant_id: uuid.UUID, filters: dict, page: int, page_size: int) -> List[T]:
        """Return paginated list (excludes soft-deleted)."""
```

### Base Repository Abstract Implementation
**File**: [backend/app/infrastructure/persistence/repositories/base_repository.py](backend/app/infrastructure/persistence/repositories/base_repository.py)

**Key Features**:
- Automatic tenant isolation (WHERE tenant_id = :tenant_id)
- Automatic soft-delete filtering (WHERE is_deleted = false)
- Generic CRUD boilerplate elimination
- Three abstract mapping hooks:
  - `_model_class()` - Returns SQLAlchemy model
  - `_to_entity(model)` - ORM → Domain entity mapping
  - `_to_model(entity)` - Domain entity → ORM mapping

### Concrete Repository Example

**File**: [backend/app/infrastructure/persistence/repositories/material_repository.py](backend/app/infrastructure/persistence/repositories/material_repository.py)

```python
class MaterialRepository(BaseRepository[Material, MaterialModel]):
    def _model_class(self) -> Type[MaterialModel]:
        return MaterialModel
    
    def _to_entity(self, model: MaterialModel) -> Material:
        return Material(
            id=model.id,
            tenant_id=model.tenant_id,
            code=model.code,
            # ... mapping
        )
    
    def _to_model(self, entity: Material) -> MaterialModel:
        return MaterialModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code,
            # ... reverse mapping
        )
    
    # Custom queries
    async def get_by_code(self, code: str, tenant_id: uuid.UUID) -> Optional[Material]:
        stmt = select(MaterialModel).where(
            MaterialModel.code == code,
            MaterialModel.tenant_id == tenant_id,
            MaterialModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def search(self, tenant_id: uuid.UUID, query: str, page: int) -> List[Material]:
        # Custom search with filters
        ...
```

### Available Repositories
- [backend/app/infrastructure/persistence/repositories/material_repository.py](backend/app/infrastructure/persistence/repositories/material_repository.py)
- [backend/app/infrastructure/persistence/repositories/batch_repository.py](backend/app/infrastructure/persistence/repositories/batch_repository.py)
- [backend/app/infrastructure/persistence/repositories/bom_repository.py](backend/app/infrastructure/persistence/repositories/bom_repository.py)
- [backend/app/infrastructure/persistence/repositories/item_template_repository.py](backend/app/infrastructure/persistence/repositories/item_template_repository.py)
- [backend/app/infrastructure/persistence/repositories/item_variant_repository.py](backend/app/infrastructure/persistence/repositories/item_variant_repository.py)
- [backend/app/infrastructure/persistence/repositories/serial_number_repository.py](backend/app/infrastructure/persistence/repositories/serial_number_repository.py)
- [backend/app/infrastructure/persistence/repositories/transaction_repository.py](backend/app/infrastructure/persistence/repositories/transaction_repository.py)
- [backend/app/infrastructure/persistence/repositories/location_repository.py](backend/app/infrastructure/persistence/repositories/location_repository.py)
- [backend/app/infrastructure/persistence/repositories/unit_of_measure_repository.py](backend/app/infrastructure/persistence/repositories/unit_of_measure_repository.py)
- [backend/app/infrastructure/persistence/repositories/uom_conversion_repository.py](backend/app/infrastructure/persistence/repositories/uom_conversion_repository.py)

---

## 5. DOMAIN EVENTS

### Definition
Domain events represent significant business occurrences within the domain. They enable:
- Eventual consistency between bounded contexts
- Audit trails
- Integration with external systems

### Base Domain Event
**File**: [backend/app/domain/shared/domain_event.py](backend/app/domain/shared/domain_event.py)

```python
@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[uuid.UUID] = field(default=None)
```

### Event Management in Entities

**In BaseEntity** ([backend/app/domain/shared/base_entity.py](backend/app/domain/shared/base_entity.py)):
```python
def add_domain_event(self, event: "DomainEvent") -> None:
    self._domain_events.append(event)

def pull_domain_events(self) -> List["DomainEvent"]:
    events = list(self._domain_events)
    self._domain_events.clear()
    return events
```

### Event Dispatch Pattern

**Unit of Work**: [backend/app/infrastructure/persistence/unit_of_work.py](backend/app/infrastructure/persistence/unit_of_work.py)

```python
class SQLAlchemyUnitOfWork(IUnitOfWork):
    async def commit(self) -> None:
        await self._session.flush()
        await self._session.commit()
        
        # Collect and dispatch domain events
        events = []
        for tracked_entity in self._session.identity_map.values():
            if hasattr(tracked_entity, 'pull_domain_events'):
                events.extend(tracked_entity.pull_domain_events())
        
        for event in events:
            await self._dispatcher.dispatch(event)
```

### Event Bus & Dispatcher
- **EventDispatcher**: [backend/app/infrastructure/events/event_dispatcher.py](backend/app/infrastructure/events/event_dispatcher.py)
- **EventBus**: [backend/app/infrastructure/events/event_bus.py](backend/app/infrastructure/events/event_bus.py)
- **EventHandler Interface**: [backend/app/infrastructure/events/event_handler_interface.py](backend/app/infrastructure/events/event_handler_interface.py)

### Implemented Domain Events
- **UserCreated** - [backend/app/domain/tenant/events/user_created.py](backend/app/domain/tenant/events/user_created.py)
  - Raised when a new user is created
  - Can trigger downstream handlers (e.g., send welcome email)

**Note**: Event handlers can be registered and will execute asynchronously after UnitOfWork commit.

---

## 6. DATABASE MODELS (SQLAlchemy ORM)

Located in: `backend/app/infrastructure/persistence/models/`

### Model Pattern
- **Base**: All models inherit from SQLAlchemy `Base` via `backend.app.infrastructure.persistence.database`
- **Async ORM**: Uses `sqlalchemy.ext.asyncio` for async/await support
- **Type Safety**: Uses `Mapped` annotations for columns

### Material Model Example
**File**: [backend/app/infrastructure/persistence/models/material_model.py](backend/app/infrastructure/persistence/models/material_model.py)

```python
class MaterialModel(Base):
    __tablename__ = "materials"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_material_tenant_code"),
        Index("ix_materials_tenant_id", "tenant_id"),
        Index("ix_materials_is_deleted", "is_deleted"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    current_stock: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    reserved_stock: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

### Key Patterns
- **Tenant Isolation**: Always include `tenant_id` column with index
- **Soft Delete**: `is_deleted` + `deleted_at` columns
- **Timestamps**: Auto-managed `created_at` + `updated_at`
- **Precision**: Use `Numeric(18, 4)` for financial data
- **Constraints**: Unique constraints include `tenant_id` for tenant isolation
- **Indexes**: Strategic indexes on `tenant_id` and `is_deleted` for query performance

### Key Models
- [backend/app/infrastructure/persistence/models/material_model.py](backend/app/infrastructure/persistence/models/material_model.py)
- [backend/app/infrastructure/persistence/models/batch_model.py](backend/app/infrastructure/persistence/models/batch_model.py)
- [backend/app/infrastructure/persistence/models/bom_model.py](backend/app/infrastructure/persistence/models/bom_model.py)
- [backend/app/infrastructure/persistence/models/item_template_model.py](backend/app/infrastructure/persistence/models/item_template_model.py)
- [backend/app/infrastructure/persistence/models/item_variant_model.py](backend/app/infrastructure/persistence/models/item_variant_model.py)
- [backend/app/infrastructure/persistence/models/serial_number_model.py](backend/app/infrastructure/persistence/models/serial_number_model.py)
- [backend/app/infrastructure/persistence/models/location_model.py](backend/app/infrastructure/persistence/models/location_model.py)
- [backend/app/infrastructure/persistence/models/unit_of_measure_model.py](backend/app/infrastructure/persistence/models/unit_of_measure_model.py)
- [backend/app/infrastructure/persistence/models/uom_conversion_model.py](backend/app/infrastructure/persistence/models/uom_conversion_model.py)
- [backend/app/infrastructure/persistence/models/inventory_transaction_model.py](backend/app/infrastructure/persistence/models/inventory_transaction_model.py)

---

## 7. API SCHEMAS (Pydantic)

Located in: `backend/app/interfaces/api/v1/schemas/`

### Pattern
- Request DTOs: `*Request` classes with validation
- Response DTOs: `*Response` classes with `model_config = {"from_attributes": True}`
- Immutable dataclasses: `@dataclass(frozen=True)` for commands
- Pydantic validators: Use `@model_validator` for cross-field validation

### Inventory Schemas
**File**: [backend/app/interfaces/api/v1/schemas/inventory_schemas.py](backend/app/interfaces/api/v1/schemas/inventory_schemas.py)

```python
class CreateMaterialRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    material_type: str = Field("raw", pattern="^(raw|finished)$")
    category_id: Optional[uuid.UUID] = None
    is_batch_tracked: bool = False
    is_serialized: bool = False

class UpdateMaterialRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # ... other fields

class MaterialResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    material_type: str
    current_stock: Decimal
    reserved_stock: Decimal
    available_stock: Decimal
    is_batch_tracked: bool
    is_active: bool
    
    model_config = {"from_attributes": True}

class AddStockRequest(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_id: Optional[uuid.UUID] = None
    to_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None

class TransactionRequest(BaseModel):
    material_id: uuid.UUID
    transaction_type: str = Field(..., pattern="^(in|out|transfer|adjustment)$")
    quantity: Decimal = Field(..., gt=0)
    # ... other fields
```

### BOM Schemas
**File**: [backend/app/interfaces/api/v1/schemas/bom_schemas.py](backend/app/interfaces/api/v1/schemas/bom_schemas.py)

```python
class BOMLineRequest(BaseModel):
    quantity: Decimal = Field(gt=0)
    scrap_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    material_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    
    @model_validator(mode="after")
    def check_exactly_one_component(self):
        refs = [x for x in (self.material_id, self.template_id, self.variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("Exactly one of material_id, template_id, or variant_id must be provided.")
        return self

class CreateBOMRequest(BaseModel):
    version: str = Field(min_length=1, max_length=50)
    valid_from: datetime
    template_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    lines: List[BOMLineRequest] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def check_exactly_one_product(self):
        refs = [x for x in (self.template_id, self.variant_id) if x is not None]
        if len(refs) != 1:
            raise ValueError("Exactly one of template_id or variant_id must be provided.")
        return self

class BOMResponse(BaseModel):
    id: uuid.UUID
    version: str
    is_active: bool
    lines: List[BOMLineResponse]
    
    model_config = {"from_attributes": True}
```

### Product Schemas
**File**: [backend/app/interfaces/api/v1/schemas/product_schemas.py](backend/app/interfaces/api/v1/schemas/product_schemas.py)

```python
class AttributeDefinition(BaseModel):
    key: str = Field(..., description="e.g. 'SIZE'")
    label: str = Field(..., description="e.g. 'Size'")
    values: List[str] = Field(default_factory=list)

class CreateItemTemplateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    attributes: List[AttributeDefinition] = Field(default_factory=list)

class ItemVariantResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    code: str
    variant_key: str
    attribute_values: Dict[str, Any]
    standard_cost: Decimal
    selling_price: Optional[Decimal]
    
    model_config = {"from_attributes": True}
```

---

## 8. APPLICATION LAYER (Commands, Queries, Handlers)

### Command Pattern
**Location**: `backend/app/application/{domain}/commands/`

Commands are **immutable dataclasses** representing user intents.

**Example**: [backend/app/application/inventory/commands/inventory_commands.py](backend/app/application/inventory/commands/inventory_commands.py)

```python
@dataclass(frozen=True)
class CreateMaterialCommand:
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    code: str
    name: str
    material_type: str = "raw"
    description: Optional[str] = None
    # ... other fields

@dataclass(frozen=True)
class UpdateMaterialCommand:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: Optional[str] = None
    # ... other fields

@dataclass(frozen=True)
class AddStockCommand:
    """Stock IN — increases current_stock."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    created_by: uuid.UUID
    # ... other fields

@dataclass(frozen=True)
class RemoveStockCommand:
    """Stock OUT — decreases current_stock. Enforces no-negative rule."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    # ... other fields

@dataclass(frozen=True)
class AdjustStockCommand:
    """Direct quantity adjustment."""
    tenant_id: uuid.UUID
    material_id: uuid.UUID
    new_quantity: Decimal
    # ... other fields
```

### Query Pattern
**Location**: `backend/app/application/{domain}/queries/`

Queries are also **immutable dataclasses** representing read intents.

**Example**: [backend/app/application/inventory/queries/inventory_queries.py](backend/app/application/inventory/queries/inventory_queries.py)

```python
@dataclass(frozen=True)
class ListMaterialsQuery:
    tenant_id: uuid.UUID
    query: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20

@dataclass(frozen=True)
class GetMaterialQuery:
    id: uuid.UUID
    tenant_id: uuid.UUID

@dataclass(frozen=True)
class GetStockQuery:
    material_id: uuid.UUID
    tenant_id: uuid.UUID

@dataclass(frozen=True)
class GetTransactionsQuery:
    tenant_id: uuid.UUID
    material_id: Optional[uuid.UUID] = None
    page: int = 1
    page_size: int = 50

@dataclass(frozen=True)
class GetBatchesByMaterialQuery:
    tenant_id: uuid.UUID
    material_id: uuid.UUID

@dataclass(frozen=True)
class GetExpiringBatchesQuery:
    tenant_id: uuid.UUID
    days_ahead: int = 30

@dataclass(frozen=True)
class GetSerialDetailsQuery:
    tenant_id: uuid.UUID
    serial_number: str
```

### Handler Pattern
**Location**: `backend/app/application/{domain}/handlers/`

Command/Query handlers orchestrate domain logic using repositories and services.

**Example**: [backend/app/application/inventory/handlers/inventory_handlers.py](backend/app/application/inventory/handlers/inventory_handlers.py)

```python
class CreateMaterialHandler:
    def __init__(self, material_repo: MaterialRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = material_repo
        self._uow = uow
    
    async def handle(self, cmd: CreateMaterialCommand) -> MaterialResult:
        # Validate domain constraints
        if await self._repo.code_exists(cmd.code, cmd.tenant_id):
            raise ValueError(f"Material with code '{cmd.code}' already exists...")
        
        # Create domain entity
        material = Material(
            tenant_id=cmd.tenant_id,
            code=cmd.code,
            name=cmd.name,
            material_type=cmd.material_type,
            description=cmd.description,
            category_id=cmd.category_id,
            base_unit_id=cmd.base_unit_id,
            reorder_level=cmd.reorder_level,
            location_id=cmd.location_id,
            is_batch_tracked=cmd.is_batch_tracked,
            is_serialized=cmd.is_serialized,
        )
        
        # Persist
        await self._repo.save(material)
        await self._uow.commit()  # Triggers domain event dispatch
        
        # Return DTO
        return _to_result(material)

class AddStockHandler:
    def __init__(self, material_repo: MaterialRepository, tx_repo: TransactionRepository, uow: SQLAlchemyUnitOfWork):
        self._material_repo = material_repo
        self._tx_repo = tx_repo
        self._uow = uow
    
    async def handle(self, cmd: AddStockCommand) -> MaterialResult:
        # Fetch entity
        material = await self._material_repo.get_by_id(cmd.material_id, cmd.tenant_id)
        if not material:
            raise ValueError(f"Material {cmd.material_id} not found.")
        
        # Call domain method
        material.add_stock(cmd.quantity)
        
        # Log transaction
        tx = InventoryTransaction(
            tenant_id=cmd.tenant_id,
            material_id=material.id,
            transaction_type=TransactionType.IN,
            quantity=cmd.quantity,
            unit_id=cmd.unit_id,
            to_location_id=cmd.to_location_id,
            created_by=cmd.created_by,
            remarks=cmd.remarks,
            reference_type=ReferenceType.PURCHASE_ORDER if cmd.reference_id else None,
            reference_id=cmd.reference_id,
        )
        await self._tx_repo.save(tx)
        
        # Persist changes
        await self._material_repo.save(material)
        await self._uow.commit()
        
        return _to_result(material)
```

### BOM Handlers
**File**: [backend/app/application/bom/handlers/bom_handlers.py](backend/app/application/bom/handlers/bom_handlers.py)

```python
class BOMHandlers:
    def __init__(self, bom_repo: BOMRepository, uow: SQLAlchemyUnitOfWork):
        self._repo = bom_repo
        self._uow = uow
    
    async def handle_create(self, cmd: CreateBOMCommand) -> BillOfMaterial:
        # Build aggregate
        bom = BillOfMaterial(
            tenant_id=cmd.tenant_id,
            template_id=cmd.template_id,
            variant_id=cmd.variant_id,
            version=cmd.version,
            valid_from=cmd.valid_from,
            valid_to=cmd.valid_to,
            created_by=cmd.created_by,
            approved_by=cmd.approved_by,
        )
        
        # Add lines
        for line_input in cmd.lines:
            bom.add_line(BOMLine(...))
        
        # Validate circular dependencies (domain service)
        provider = InfrastructureBOMProvider(self._repo)
        validator = BOMValidationService(provider)
        await validator.validate_no_circular_dependencies(cmd.tenant_id, bom)
        
        # Persist
        await self._repo.save(bom)
        await self._uow.commit()
        return bom
    
    async def handle_update(self, cmd: UpdateBOMCommand) -> BillOfMaterial:
        # Fetch and modify
        bom = await self._repo.get_by_id(cmd.bom_id, cmd.tenant_id)
        if not bom:
            raise ValueError(f"BOM {cmd.bom_id} not found.")
        if bom.is_active:
            raise ValueError("Cannot update an active BOM.")
        
        # Update fields
        if cmd.valid_from is not None:
            bom.valid_from = cmd.valid_from
        if cmd.lines is not None:
            bom.lines.clear()
            for line_input in cmd.lines:
                bom.add_line(BOMLine(...))
        
        # Validate
        provider = InfrastructureBOMProvider(self._repo)
        validator = BOMValidationService(provider)
        await validator.validate_no_circular_dependencies(cmd.tenant_id, bom)
        
        # Persist
        await self._repo.save(bom)
        await self._uow.commit()
        return bom
```

### Query Handlers
**File**: [backend/app/application/inventory/handlers/inventory_query_handler.py](backend/app/application/inventory/handlers/inventory_query_handler.py)

```python
class ListMaterialsQueryHandler:
    def __init__(self, material_repo: MaterialRepository):
        self._repo = material_repo
    
    async def handle(self, query: ListMaterialsQuery) -> List[MaterialResult]:
        materials = await self._repo.search(
            tenant_id=query.tenant_id,
            query=query.query,
            category=query.category,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        return [_to_result(m) for m in materials]

class GetMaterialQueryHandler:
    def __init__(self, material_repo: MaterialRepository):
        self._repo = material_repo
    
    async def handle(self, query: GetMaterialQuery) -> MaterialResult:
        material = await self._repo.get_by_id(query.id, query.tenant_id)
        if not material:
            raise ValueError(f"Material {query.id} not found.")
        return _to_result(material)
```

---

## 9. UNIT OF WORK PATTERN

**File**: [backend/app/infrastructure/persistence/unit_of_work.py](backend/app/infrastructure/persistence/unit_of_work.py)

The Unit of Work pattern coordinates multiple operations into a single atomic transaction and manages domain event dispatch.

```python
class SQLAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession, event_dispatcher: EventDispatcher) -> None:
        self._session = session
        self._dispatcher = event_dispatcher
        self._pending_events: List[DomainEvent] = []
    
    async def commit(self) -> None:
        # 1. Flush SQLAlchemy session
        await self._session.flush()
        
        # 2. Commit database transaction
        await self._session.commit()
        
        # 3. Collect domain events from all tracked entities
        events = []
        for tracked_entity in self._session.identity_map.values():
            if hasattr(tracked_entity, 'pull_domain_events'):
                events.extend(tracked_entity.pull_domain_events())
        
        # 4. Dispatch events via event bus
        for event in events:
            await self._dispatcher.dispatch(event)
    
    async def rollback(self) -> None:
        await self._session.rollback()
```

**Usage Pattern** (in handlers):
```python
async def handle(self, cmd: SomeCommand) -> Result:
    entity = await repo.get_by_id(...)
    entity.do_something()  # May raise domain event
    
    await repo.save(entity)
    await self._uow.commit()  # Commits transaction AND dispatches events
    
    return result
```

---

## 10. SHARED DOMAIN INTERFACES

**Location**: `backend/app/domain/shared/interfaces/`

### IRepository Interface
[backend/app/domain/shared/interfaces/repository_interface.py](backend/app/domain/shared/interfaces/repository_interface.py)

Defines contract for all repositories:
- `get_by_id()` - Fetch by primary key
- `get_including_deleted()` - Admin retrieval of deleted records
- `save()` - Insert or update
- `delete()` - Soft delete
- `list()` - Paginated list with filters

### IUnitOfWork Interface
[backend/app/domain/shared/interfaces/unit_of_work_interface.py](backend/app/domain/shared/interfaces/unit_of_work_interface.py)

Defines contract for transaction management:
- `commit()` - Commit and dispatch events
- `rollback()` - Rollback transaction
- `__aenter__` / `__aexit__` - Async context manager support

### IDomainService Interface
[backend/app/domain/shared/interfaces/domain_service_interface.py](backend/app/domain/shared/interfaces/domain_service_interface.py)

Marker interface for domain services (used for dependency injection).

---

## 11. ARCHITECTURAL FLOW

### Command Execution Flow
```
API Route (fastapi)
  ↓
Request DTO (Pydantic Schema)
  ↓
Route Handler (converts request to Command)
  ↓
Command → Application Service(Handler)
  ↓
Handler validates using Repository
  ↓
Handler creates/updates Domain Entity
  ↓
Handler calls Domain Service (if needed, e.g., BOMValidationService)
  ↓
Handler saves Entity to Repository
  ↓
Handler calls UnitOfWork.commit()
  ↓
UoW flushes & commits DB transaction
  ↓
UoW collects domain events from entities
  ↓
UoW dispatches events via EventDispatcher
  ↓
Response DTO returned to API
```

### Query Execution Flow
```
API Route (fastapi)
  ↓
Query → Query Handler (QueryService)
  ↓
Handler queries Repository (no domain logic)
  ↓
Repository maps ORM Model → Domain Entity
  ↓
Handler converts Entity → Response DTO
  ↓
Response DTO returned to API
```

---

## 12. KEY PATTERNS AND BEST PRACTICES

### Dependency Injection
- **Protocol-based**: Use `Protocol` from `typing` for loose coupling
  ```python
  class BOMProvider(Protocol):
      async def get_active_bom(...) -> Optional[BillOfMaterial]: ...
  
  class BOMValidationService:
      def __init__(self, bom_provider: BOMProvider):
          self._bom_provider = bom_provider
  ```

### Tenant Isolation
- **Every** entity must have `tenant_id`
- **Every** repository query filters by `tenant_id`
- **Every** database model has unique constraints on `(tenant_id, code)`

### Soft Deletes
- All entities support soft deletion via `is_deleted` flag
- Repository queries exclude soft-deleted records by default
- Admin endpoint can retrieve deleted records using `get_including_deleted()`

### Validation Layers
1. **API Schema** (Pydantic): Request structure + field validation
2. **Domain Entity** (in `__init__`): Business rule enforcement
3. **Domain Service**: Complex, multi-entity rules (e.g., circular dependency)
4. **Repository**: Unique constraint checks (e.g., `code_exists()`)

### Immutability
- Commands and Queries: `@dataclass(frozen=True)`
- Domain Events: `@dataclass(frozen=True)`
- Value Objects: `BaseValueObject` subclasses

### Error Handling
- Domain exceptions raised in entity constructors
- ValidationError for API schema violations
- Handled consistently in route layers

---

## 13. SUMMARY TABLE

| Concept | Location | Pattern | Key Files |
|---------|----------|---------|-----------|
| **Value Objects** | `domain/{domain}/` | Immutable, ABCs | `base_value_object.py` |
| **Entities** | `domain/{domain}/entities/` | Identity-based, with domain logic | `base_entity.py`, `material.py`, `bom.py` |
| **Domain Services** | `domain/{domain}/services/` | Stateless, Protocol-based injection | `bom_validation_service.py` |
| **Application Services** | `application/{domain}/handlers/` | Command/Query handlers, coordinate logic | `inventory_handlers.py`, `bom_handlers.py` |
| **Repositories** | `infrastructure/persistence/repositories/` | Generic base + concrete implementations | `base_repository.py`, `material_repository.py` |
| **Domain Events** | `domain/shared/` + `domain/{domain}/events/` | Immutable, dispatched after UoW commit | `domain_event.py` |
| **Models (ORM)** | `infrastructure/persistence/models/` | SQLAlchemy async, tenant isolation | `material_model.py`, `bom_model.py` |
| **Schemas (DTO)** | `interfaces/api/v1/schemas/` | Pydantic, request + response | `inventory_schemas.py`, `bom_schemas.py` |
| **Commands** | `application/{domain}/commands/` | Frozen dataclasses | `inventory_commands.py`, `bom_commands.py` |
| **Queries** | `application/{domain}/queries/` | Frozen dataclasses | `inventory_queries.py` |
| **Interfaces** | `domain/shared/interfaces/` | Abstraction layer | `repository_interface.py`, `unit_of_work_interface.py` |
| **Unit of Work** | `infrastructure/persistence/` | Transaction coordination + event dispatch | `unit_of_work.py` |

---

## 14. BOUNDED CONTEXTS

The application is organized into the following bounded contexts:

1. **Inventory** - Stock, batches, serial numbers, locations, units
2. **Product** - Item templates, variants, configurable attributes
3. **BOM** - Bills of material, routing, operations, workstations
4. **Manufacturing** - (Currently minimal; reserved for future expansion)
5. **Procurement** - (Currently minimal; reserved for future expansion)
6. **Finance** - (Currently minimal; reserved for future expansion)
7. **Quality** - (Currently minimal; reserved for future expansion)
8. **Sales** - (Currently minimal; reserved for future expansion)
9. **Tenant** - Multi-tenancy, user management, permissions
10. **Shared** - Common interfaces, base classes, domain events

Each context has its own `entities/`, `services/`, `repositories/`, `commands/`, `queries/`, and `handlers/` folders.

---

## 15. FUTURE ENHANCEMENTS

Based on the existing patterns, future improvements could include:

1. **Custom Value Objects** - Create Money, DateRange, ProductCode, etc.
2. **Event Sourcing** - Store all events for audit/replay capabilities
3. **CQRS Read Models** - Denormalized projections for complex queries
4. **Saga Pattern** - Distributed transactions across bounded contexts
5. **Event Handlers** - Implement actual event subscribers (email, notifications, etc.)
6. **Specification Pattern** - Complex domain queries encapsulated as objects
7. **Aggregate Factory** - Complex creation logic delegated to factories

---

Generated: 2026-03-26
