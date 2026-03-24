"""Layered alias for billing configuration logic.

Canonical runtime implementation remains in src.billing_router while the
application-layer path is adopted incrementally by callers.
"""

from ...billing_router import (  # noqa: F401
    BillingConfig,
    _select_model_by_tension,
    _select_model_by_tension_phase1,
    select_billing_config,
)

__all__ = [
    "BillingConfig",
    "select_billing_config",
    "_select_model_by_tension",
    "_select_model_by_tension_phase1",
]
