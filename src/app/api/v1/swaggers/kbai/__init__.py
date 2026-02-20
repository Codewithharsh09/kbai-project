# Kbai schema swaggers

from .companies_tab import (
    kbai_companies_ns,
    create_company_model,
    update_company_model,
    company_response_model,
    companies_list_response_model,
    user_companies_response_model,
    companies_dropdown_response_model,
    validation_error_model,
    not_found_error_model,
    internal_error_model,
    success_message_model,
)

try:
    from .pre_dashboard_tab import (
        kbai_pre_dashboard_ns,
        pre_dashboard_model,
    )
except ImportError:
    kbai_pre_dashboard_ns = None
    pre_dashboard_model = None