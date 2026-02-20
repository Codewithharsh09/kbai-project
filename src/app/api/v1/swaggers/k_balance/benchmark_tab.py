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

# Payload for update a note for partiular benchmark report
update_benchmark_payload_model = benchmark_ns.model('UpdateBenchmarkPayload', {
    'note': fields.String(
        required=True,
        description='New note content for the benchmark report',
        example='This is an updated note for the benchmark report.'
    ),
    'name': fields.String(
        required=False,
        description='name for the benchmark report',
        example='Kpi Name'
    )
})

# =============================================================================
# RESPONSE MODELS
# =============================================================================

# Add Competitor Comparison Response Model
add_competitor_comparison_response_model = benchmark_ns.model('AddCompetitorComparisonResponse', {
    'message': fields.String(
        description='Response message',
        example='Competitor comparison report created successfully'
    ),
    'data': fields.Raw(
        description='Created competitor comparison data',
        example={}
    ),
    'success': fields.Boolean(
        description='Operation success status for competitor comparison',
        example=True
    )
})


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

# Update Benchmark Response Model
benchmark_update_response_model = benchmark_ns.model('BenchmarkUpdateResponse', {
     'success': fields.Boolean(
        description='Operation success status for benchmark',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Benchmark KPI note updated successfully'
    ),
    'data': fields.Raw(
        description='updated benchmark data',
        example={}
    )
})


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


# List Response Model for Competitor Reports
competitor_reports_response_model = benchmark_ns.model('CompetitorReportsResponse', {
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Competitor Benchmark Reports fetched successfully'
    ),
    'data': fields.Raw(
        description='Competitor reports data',
        example={
                "parent_id_report": 106,
                "parent_analysis_id": 116,
                "parent_name": "testing6",
                "time": "2026-01-19T10:20:03.149354",
                "benchmarks": {
                    "competitor": {
                        "file": "provisional 2020 ",
                        "kpis": {"EBITDA": 10.0,"EBIT_Reddito_Operativo": 10.0,"MOL_RICAVI_%": 10.0,"EBITDA_Margin_%": 10.0,"Margine_Contribuzione_%": 10.0,"Patrimonio_Netto": 10.0,"Mark_Up": 10.0,"Fatturato_Equilibrio_BEP": 10.0,"Spese_Generali_Ratio": 10.0,"Ricavi_Totali": 10.0,"Costi_Variabili": 10.0},
                        "year": 2020
                    }
                },
                "kpi_statuses": {
                    "EBITDA": {
                        "status": "ALARMING",
                        "note": "Average",
                        "goal": 70.0,
                        "synthesis": "The company recorded a increase of +3.0% compared to 2020. Compared to the previous fiscal year, the value shows a decrease of 4.5%",
                        "suggestion": [
                            'Immediate restructuring required to restore profitability.'
                        ]
                    }
                }
            }
    )
    }
)
# Suggested Competitors Response Model
suggested_competitors_response_model = benchmark_ns.model('SuggestedCompetitorsResponse', {
    'success': fields.Boolean(
        description='Operation success status',
        example=True
    ),
    'message': fields.String(
        description='Response message',
        example='Competitor companies retrieved successfully'
    ),
    'data': fields.List(
        fields.Raw(
            description='Suggested competitor with nested balances',
            example={
                "id_company": 1,
                "company_name": "Competitor S.r.l.",
                "balances": [
                    {
                        "id_balance": 10,
                        "year": 2024,
                        "type": "final",
                        "file": "Balance_2024.pdf"
                    }
                ]
            }
        )
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
update_validation_error_model = benchmark_ns.model('NoteValidationError', {
    'error': fields.String(
        description='Error type',
        example='Validation error'
    ),
    'message': fields.String(
        description='Error message',
        example='id_analysis and KPI name are required'
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
    "parent_id_report": 123,
    "parent_analysis_id": 123,
    "parent_name": "TestComp2-2020-2025-2026",
    "time": "2025-12-23T12:22:14.936514",
    "benchmarks": {
      "balanceSheetToCompare": {
        "file": "Provisional 2020 ",
        "kpis": {
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
        "year": 2020
      },
      "comparitiveBalancesheet": {
        "file": "final 2026 dicembre",
        "kpis": {},
        "year": 2026
      },
      "referenceBalanceSheet": {
        "file": "forecast 2025 ",
        "kpis": {},
        "year": 2025
      }
    },
    "kpi_statuses": {
      "EBITDA": {
        "status": "ALARMING",
        "note": "Average",
        "goal": 70.0,
        "synthesis": "The company recorded a increase of +3.0% compared to 2020. Compared to the previous fiscal year, the value shows a decrease of 4.5%",
        "suggestion": [
          "Immediate restructuring required to restore profitability."
        ]
      },
      "EBIT_Reddito_Operativo": {
        "status": "AVERAGE",
        "note": "Average",
        "goal": 10.0,
        "synthesis": "The company recorded a increase of +6.0% compared to 2020. Compared to the previous fiscal year, the value shows a decrease of 3.4%",
        "suggestion": [
          "Monitor this KPI regularly and take corrective actions if required."
        ]
      },
    },
    "competitor_reports": [
        {
            "competitor_id_report": 83,
            "comparison_name": "testing4",
            "type": "Diretto",
            "competitor_name": "lotobola",
            "balance_name": "provisional 2026 ",
            "time": "2026-01-15T09:27:28.477819"
        }
    ]
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

validation_error_getbenchmark_model = benchmark_ns.model('ValidationErrorBenchmark', {
    'error': fields.String(
        description='Error type',
        example='Validation error'
    ),
    'message': fields.String(
        description='Error message',
        example='Report ID is required'
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


not_found_error_getBenchmark_model = benchmark_ns.model('NotFoundErrorGetBenchmark', {
    'error': fields.String(
        description='Error type',
        example='Not found'
    ),
    'message': fields.String(
        description='Error message',
        example='Report not found'
    )
})

note_not_found_error_model = benchmark_ns.model('NoteNotFoundError', {
    'error': fields.String(
        description='Error type',
        example='Not found'
    ),
    'message': fields.String(
        description='Error message',
        example='Analysis not found'
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
    'add_competitor_comparison_response_model',
    'benchmarks_list_response',
    'benchmarks_report_list_response',
    'competitor_reports_response_model',
    'benchmark_report_details_data_model',
    'benchmark_report_details_response',
    'validation_error_model',
    'internal_error_model',
    'not_found_error_model',
    'benchmark_list_item_model',
    'benchmark_delete_response_model',
    'update_benchmark_payload_model',
    'update_validation_error_model',
    'note_not_found_error_model',
    'validation_error_getbenchmark_model',
    'not_found_error_getBenchmark_model',
    'suggested_competitors_response_model'
]

