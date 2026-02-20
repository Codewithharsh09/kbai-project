"""
KBAI Benchmark Tab Swagger Documentation

Contains all KBAI Benchmark related API documentation including:
- Benchmark creation
- Benchmark listing
- Error models related to benchmark operations
"""

from flask_restx import Namespace, fields

# Create Benchmark Namespace
benchmark_ns = Namespace(
    'benchmark',
    description='KBAI Benchmark operations',
    path='/api/v1/kbai-benchmark/benchmark'
)

# =============================================================================
# REQUEST MODELS
# =============================================================================

# Balance Sheet Model
balance_sheet_model = benchmark_ns.model('BalanceSheet', {
    'year': fields.Integer(
        required=True,
        description='Year of the balance sheet',
        example=2020
    ),
    'budgetType': fields.String(
        required=True,
        description='Budget type',
        example='Provisional'
    ),
    'month': fields.Integer(
        required=False,
        description='Month of the balance sheet (optional)',
        example=12
    )
})

# Payload for creating a new benchmark
create_benchmark_payload_model = benchmark_ns.model('CreateBenchmarkPayload', {
    'balanceSheetToCompare': fields.Nested(
        balance_sheet_model,
        required=True,
        description='Balance sheet to compare'
    ),
    'comparitiveBalancesheet': fields.Nested(
        balance_sheet_model,
        required=True,
        description='Comparative balance sheet'
    ),
    'referenceBalanceSheet': fields.Nested(
        balance_sheet_model,
        required=True,
        description='Reference balance sheet'
    )
})

# =============================================================================
# RESPONSE MODELS
# =============================================================================

# Single Benchmark Response Model
benchmark_create_response_model = benchmark_ns.model('BenchmarkCreateResponse', {
    'message': fields.String(
        description='Response message',
        example='Benchmark report created successfully'
    ),
    'data': fields.Raw(
        description='Created benchmark data',
        example={}
    ),
    'success': fields.Boolean(
        description='Operation success status for benchmark',
        example=True
    )
})
# ...existing code...

# List Response Model for Benchmarks
benchmarks_list_response = benchmark_ns.model('BenchmarksYearListResponse', {
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Balance sheet years retrieved successfully'
    ),
    'data': fields.Raw(
        description='Balance years data',
        example={
            'balance_years': [
                2019,
                2020,
                2021,
                2025
            ]
        }
    )
})

# List Response Model for Benchmarks
benchmarks_report_list_response = benchmark_ns.model('BenchmarksReportrListResponse', {
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Benchmark reports retrieved successfully'
    ),
    'data': fields.Raw(
        description='Benchmark report data',
        example={
            'balance_sheets': [
               {
                    "id_report": 133,
                    "name": "Benchmark Report",
                    "time": "2025-12-12T15:10:42.144426",
                    "balances": {
                        "balanceSheetToCompare": "Istanza08508360016.xbrl",
                        "referenceBalanceSheet": "Istanza08508360016 (2).xbrl",
                        "ComparitiveBalancesheet": "Provisional 2020 "
                    }
      },
      {
                    "id_report": 134,
                    "name": "Benchmark Report",
                    "time": "2025-12-12T15:25:08.108158",
                    "balances": {
                        "balanceSheetToCompare": "Istanza08508360016.xbrl",
                        "referenceBalanceSheet": "Istanza08508360016 (2).xbrl",
                        "ComparitiveBalancesheet": "Provisional 2020 "
                    }
      },
      {
                    "id_report": 135,
                    "name": "Benchmark Report",
                    "time": "2025-12-12T15:26:40.027639",
                    "balances": {
                        "balanceSheetToCompare": "Istanza08508360016.xbrl",
                        "referenceBalanceSheet": "Istanza08508360016 (2).xbrl",
                        "ComparitiveBalancesheet": "Provisional 2020 "
                    }
      },
            ],
      "pagination": {
      "page": 4,
      "per_page": 10,
      "total": 37,
      "total_pages": 4
    }
        }
    )
})


# Benchmark Report Details Data Model
benchmark_report_details_data_model = benchmark_ns.model('BenchmarkReportDetailsData', {
    'id_report': fields.Integer(
        description='Report ID',
        example=133
    ),
    'name': fields.String(
        description='Report name',
        example='Benchmark Report'
    ),
    'time': fields.String(
        description='Report creation time',
        example='2025-12-12T15:10:42.144426'
    ),
    'benchmarks': fields.Raw(
        description='Balances with file and KPIs',
        example={
            "balanceSheetToCompare": {
                "file": "Istanza08508360016.xbrl",
                "kpis": {"EBITDA": 12.5}
            },
            "comparitiveBalancesheet": {
                "file": "Istanza08508360016 (2).xbrl",
                "kpis": {"EBITDA": 10.0}
            },
            "referenceBalanceSheet": {
                "file": "Provisional 2025.xbrl",
                "kpis": {"EBITDA": 15.0}
            }
        }
    )
})

# Benchmark Report Details Response Model
benchmark_report_details_response = benchmark_ns.model('BenchmarkReportDetailsResponse', {
    'message': fields.String(
        description='Response message',
        example='Benchmarks fetched successfully'
    ),
    'data': fields.Nested(benchmark_report_details_data_model)
})

# Success Response Model (with balance field)
benchmark_delete_response_model = benchmark_ns.model('BenchmarkDeleteResponse', {
    'success': fields.Boolean(
        description='Operation success status for benchmark',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Benchmark deleted successfully'
    )
})
 

# Benchmark List Item Model
benchmark_list_item_model = benchmark_ns.model('BenchmarkListItem', {
    'id_benchmark': fields.Integer(
        description='Benchmark record ID',
        example=25
    ),
    'company_id': fields.Integer(
        description='Company ID',
        example=549
    ),
    'year': fields.Integer(
        description='Benchmark year',
        example=2023
    ),
    'type': fields.String(
        description='Benchmark type',
        example='industry'
    ),
    'benchmarks': fields.Raw(
        description='Benchmark values',
        example={'EBITDA': 12.5}
    ),
    'note': fields.String(
        description='Optional notes for benchmark',
        example='Industry median for 2023',
        allow_none=True
    ),
    'created_at': fields.String(
        description='Creation timestamp for benchmark',
        example='2024-11-05T17:56:33Z'
    ),
    'updated_at': fields.String(
        description='Last update timestamp for benchmark',
        example='2024-11-05T17:56:33Z'
    ),
    'is_deleted': fields.String(
        description='Deletion flag for benchmark',
        example='N',
        enum=['N', 'Y']
    ),
    'deleted_at': fields.String(
        description='Deletion timestamp for benchmark',
        example=None,
        allow_none=True
    )
})

# List Response Model for Benchmarks
benchmarks_list_response_model = benchmark_ns.model('BenchmarksListResponse', {
    'message': fields.String(
        description='Response message',
        example='Benchmarks retrieved successfully'
    ),
    'data': fields.List(
        fields.Nested(benchmark_list_item_model),
        description='List of benchmarks'
    ),
    'pagination': fields.Raw(
        description='Pagination information',
        example={
            'page': 1,
            'per_page': 10,
            'total': 25,
            'pages': 3
        }
    ),
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    )
})

# List Response Model for Benchmarks
benchmarks_report_response_model = benchmark_ns.model('BenchmarksReportResponse', {
     'success': fields.Boolean(
        description='Operation success status',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Benchmarks fetched successfully'
    ),
    'data': fields.String(
        description='List of benchmarks',
        example={
            "benchmarks": {
      "417": {
        "EBITDA": -753537,
        "EBIT_Reddito_Operativo": -639749,
        "MOL_RICAVI_%": -880.14,
        "EBITDA_Margin_%": -791.51,
        "Margine_Contribuzione_%": -886.01,
        "Patrimonio_Netto": 49271543,
        "Mark_Up": -0.8986,
        "Fatturato_Equilibrio_BEP": -45675.75,
        "Spese_Generali_Ratio": 4.7268,
        "Ricavi_Totali": 85616,
        "Costi_Variabili": 844181
      },
      "418": {
        "Ricavi_Totali": 83495,
        "EBITDA": -755658,
        "EBIT_Reddito_Operativo": -641870,
        "MOL_RICAVI_%": -905.03,
        "EBITDA_Margin_%": -811.83,
        "Margine_Contribuzione_%": -911.06,
        "Patrimonio_Netto": 48934346,
        "Mark_Up": -0.9011,
        "Fatturato_Equilibrio_BEP": -44420,
        "Spese_Generali_Ratio": 4.8469,
        "Costi_Variabili": 844181
      },
      "419": {
        "EBITDA": 44748968,
        "EBIT_Reddito_Operativo": 45332968,
        "MOL_RICAVI_%": 98.33,
        "EBITDA_Margin_%": 98.09,
        "Margine_Contribuzione_%": 98.09,
        "Patrimonio_Netto": 82100884,
        "Mark_Up": 51.3246,
        "Fatturato_Equilibrio_BEP": 377410.88,
        "Spese_Generali_Ratio": 0.0081,
        "Costi_Variabili": 869778
      }
    }
  } 
    )
})


# =============================================================================
# ERROR MODELS
# =============================================================================

validation_error_model = benchmark_ns.model('ValidationError', {
    'error': fields.String(
        description='Error type',
        example='Validation error'
    ),
    'message': fields.String(
        description='Error message',
        example='Year is required and must be an integer'
    )
})

internal_error_model = benchmark_ns.model('InternalError', {
    'error': fields.String(
        description='Error type',
        example='Internal server error'
    ),
    'message': fields.String(
        description='Error message',
        example='Failed to process benchmark'
    )
})

not_found_error_model = benchmark_ns.model('NotFoundError', {
    'error': fields.String(
        description='Error type',
        example='Not found'
    ),
    'message': fields.String(
        description='Error message',
        example='Benchmark with ID 1 not found'
    )
})

# =============================================================================
# EXPORT ALL MODELS
# =============================================================================

__all__ = [
    'benchmark_ns',
    'balance_sheet_model',
    'create_benchmark_payload_model',
    'benchmark_create_response_model',
    'benchmarks_list_response',
    'benchmarks_report_list_response',
    'benchmark_report_details_data_model',
    'benchmark_report_details_response',
    'validation_error_model',
    'internal_error_model',
    'not_found_error_model',
    'benchmark_list_item_model',
    'benchmark_delete_response_model'
]

