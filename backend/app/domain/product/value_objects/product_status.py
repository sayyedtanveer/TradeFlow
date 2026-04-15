from enum import Enum
from typing import Set


class ProductStatus(str, Enum):
    """
    Lifecycle states for product templates.
    
    - DRAFT: Initial state, not yet ready for use
    - ACTIVE: Ready for use in BOMs, procurement, sales
    - INACTIVE: No longer in use but history maintained
    - ARCHIVED: Historic records, rarely accessed
    """
    
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"

    # State transition rules
    VALID_TRANSITIONS = {
        DRAFT:    {ACTIVE, ARCHIVED},           # Draft can go to Active or Archived
        ACTIVE:   {INACTIVE, ARCHIVED},         # Active can go to Inactive or Archived
        INACTIVE: {ACTIVE, ARCHIVED},           # Inactive can go back to Active or Archived
        ARCHIVED: set(),                        # Archived is terminal
    }

    @staticmethod
    def can_transition(from_status: "ProductStatus", to_status: "ProductStatus") -> bool:
        """Check if a transition is allowed."""
        if from_status == to_status:
            return True  # No-op transitions are allowed
        return to_status in ProductStatus.VALID_TRANSITIONS.get(from_status, set())

    @staticmethod
    def validate_transition(from_status: "ProductStatus", to_status: "ProductStatus") -> None:
        """Raise ValueError if transition is not allowed."""
        if not ProductStatus.can_transition(from_status, to_status):
            raise ValueError(
                f"Cannot transition from {from_status.value} to {to_status.value}. "
                f"Valid transitions from {from_status.value}: {', '.join(s.value for s in ProductStatus.VALID_TRANSITIONS[from_status])}"
            )

    @property
    def is_active_state(self) -> bool:
        """Returns True if product is in ACTIVE state."""
        return self == ProductStatus.ACTIVE

    @property
    def is_usable(self) -> bool:
        """Returns True if product can be used in operations (ACTIVE or DRAFT)."""
        return self in {ProductStatus.ACTIVE, ProductStatus.DRAFT}
