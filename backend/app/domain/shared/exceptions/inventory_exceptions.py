"""Shared inventory domain exceptions used across modules."""


class InsufficientStockError(Exception):
    error_code = "INSUFFICIENT_STOCK"
