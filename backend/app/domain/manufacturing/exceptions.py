"""Manufacturing domain exceptions stub — retained for backward compatibility.

These exceptions are referenced by retained infrastructure code and will be
removed when manufacturing tables are dropped.
"""


class InsufficientStockError(Exception):
    """Deprecated: Use backend.app.domain.shared.exceptions.inventory_exceptions.InsufficientStockError instead."""
    error_code = "INSUFFICIENT_STOCK"


class MaterialNotIssuedError(Exception):
    error_code = "MATERIAL_NOT_ISSUED"


class BOMNotFoundError(Exception):
    error_code = "BOM_NOT_FOUND"


class WorkOrderImmutableError(Exception):
    error_code = "WO_IMMUTABLE"
