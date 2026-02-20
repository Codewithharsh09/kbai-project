"""
Comparison Report Swagger Documentation

Contains all comparison report API documentation including:
- Year-over-year financial KPI comparison
- Report generation and storage
"""

from flask_restx import Namespace, fields

# Create Comparison Report Namespace
comparison_report_ns = Namespace(
    'comparison-report',
    description='Generate Benchmark report operations',
    path='/api/v1/kbai-balance/comparison/benchmark'
)

# =============================================================================
# REQUEST MODELS
# =============================================================================

comparison_report_request_model = comparison_report_ns.model('ComparisonReportRequest', {
    'id_balance_year1': fields.Integer(
        required=True,
        description='Balance sheet ID for first year',
        example=1
    ),
    'id_balance_year2': fields.Integer(
        required=True,
        description='Balance sheet ID for second year',
        example=2
    ),
    'analysis_name': fields.String(
        required=False,
        description='Optional custom name for the analysis',
        example='Q4 2023 vs Q4 2024 Comparison'
    ),
    'debug_mode': fields.Boolean(
        required=False,
        description='Include debug information in response',
        example=False,
        default=False
    )
})

# =============================================================================
# RESPONSE MODELS
# =============================================================================

balance_sheet_dropdown_item_model = comparison_report_ns.model('BalanceSheetDropdownItem', {
    'id_balance': fields.Integer(description='Balance sheet ID'),
    'year': fields.Integer(description='Year'),
    'month': fields.Integer(description='Month (1-12)'),
    'type': fields.String(description='Balance sheet type'),
    'mode': fields.String(description='Upload mode'),
    'display_name': fields.String(description='Display name for dropdown')
})

benchmark_report_response_model = comparison_report_ns.model('BenchmarkReportResponse', {
    'message': fields.String(description='Response message'),
    'data': fields.Raw(description='Benchmark report data'),
    'success': fields.Boolean(description='Operation success status')
})

comparison_data_model = comparison_report_ns.model('ComparisonData', {
    'KPIs_Year1': fields.Raw(description='All KPIs for year 1'),
    'KPIs_Year2': fields.Raw(description='All KPIs for year 2'),
    'Comparison': fields.Raw(description='KPI comparison data'),
    'Missing_Fields': fields.List(fields.String, description='List of missing fields'),
    'Status': fields.String(description='Analysis status'),
    'Year1': fields.Integer(description='Year 1 value'),
    'Year2': fields.Integer(description='Year 2 value'),
    'Year1_Balance_ID': fields.Integer(description='Balance ID for year 1'),
    'Year2_Balance_ID': fields.Integer(description='Balance ID for year 2')
})

comparison_report_response_model = comparison_report_ns.model('ComparisonReportResponse', {
    'id_analysis': fields.Integer(
        description='Analysis record ID',
        example=1
    ),
    'id_report': fields.Integer(
        description='Report record ID',
        example=1
    ),
    'analysis_name': fields.String(
        description='Name of the analysis',
        example='Comparison 2023 vs 2024'
    ),
    'report_name': fields.String(
        description='Name of the report',
        example='Comparison Report 2023 vs 2024'
    ),
    'year1': fields.Integer(
        description='First year',
        example=2023
    ),
    'year2': fields.Integer(
        description='Second year',
        example=2024
    ),
    'id_balance_year1': fields.Integer(
        description='Balance sheet ID for year 1',
        example=1
    ),
    'id_balance_year2': fields.Integer(
        description='Balance sheet ID for year 2',
        example=2
    ),
    'comparison_data': fields.Nested(comparison_data_model),
    'created_at': fields.String(
        description='Creation timestamp',
        example='2024-01-15T10:30:00'
    )
})

# Error models
validation_error_model = comparison_report_ns.model('ValidationError', {
    'message': fields.String(description='Error message'),
    'data': fields.Raw(description='Error details')
})

not_found_error_model = comparison_report_ns.model('NotFoundError', {
    'message': fields.String(description='Error message'),
    'data': fields.Raw(description='Error details')
})

internal_error_model = comparison_report_ns.model('InternalError', {
    'message': fields.String(description='Error message'),
    'error_details': fields.String(description='Detailed error information')
})

# Add these models at the end before the error models

kpi_data_item_model = comparison_report_ns.model('KpiDataItem', {
    'id_balance': fields.Integer(description='Balance sheet ID'),
    'year': fields.Integer(description='Year'),
    'month': fields.Integer(description='Month'),
    'type': fields.String(description='Balance sheet type'),
    'kpis': fields.Raw(description='KPI values'),
    'missing_fields': fields.List(fields.String, description='Missing fields')
})

comparison_report_detail_response_model = comparison_report_ns.model('ComparisonReportDetailResponse', {
    'id_analysis': fields.Integer(description='Analysis ID'),
    'id_report': fields.Integer(description='Report ID'),
    'analysis_name': fields.String(description='Analysis name'),
    'report_name': fields.String(description='Report name'),
    'analysis_type': fields.String(description='Analysis type'),
    'created_at': fields.String(description='Creation timestamp'),
    'time': fields.String(description='Analysis time'),
    'balance_sheets': fields.List(fields.Raw, description='Balance sheets used'),
    'kpi_data': fields.List(fields.Nested(kpi_data_item_model), description='KPI data for each balance sheet'),
    'comparison_data': fields.Nested(comparison_data_model, description='Comparison results')
})

