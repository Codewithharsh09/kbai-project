"""
KBAI Schemas Package

Contains Marshmallow schemas for KBAI domain entities:
- Companies
- Pre-dashboard data
- Sectors, zones, and related entities
"""

from .kbai_companies_schemas import (
    CreateCompanySchema,
    UpdateCompanySchema,
)

from .kbai_pre_dashboard_schemas import (
    UpdatePreDashboardSchema,
    PreDashboardResponseSchema,
)

__all__ = [
    # Companies
    'CreateCompanySchema',
    'UpdateCompanySchema',
    
    # Pre-Dashboard
    'UpdatePreDashboardSchema',
    'PreDashboardResponseSchema',
]

