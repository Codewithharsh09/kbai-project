"""
Service for handling KBAI Pre-Dashboard CRUD operations.

This module provides business logic for managing pre-dashboard records
that track the progress of companies through various setup steps.
"""

import logging
from typing import Dict, Any, Tuple
from flask import current_app

from src.app.database.models import KbaiPreDashboard, KbaiCompany

logger = logging.getLogger(__name__)

class KbaiPreDashboardService:
    """Service for handling KBAI pre-dashboard operations"""
    
    def __init__(self):
        pass
    
    # -----------------------------------------------------------------------
    # CHECK BALANCE SHEET COUNT - Check if company has enough balance sheets
    # -----------------------------------------------------------------------
    def check_balance_sheet_count(self, company_id: int) -> Dict[str, Any]:
        """
        Check if company has at least 2 balance sheets (required for comparison step).
        Returns count, flag (true if >= 2), and file names as objects with id_balance.
        
        Args:
            company_id: Company ID
            
        Returns:
            Dictionary with count, flag, and file names as objects with id_balance
        """
        try:
            from src.app.database.models import KbaiBalance
            
            # Get all balance sheets that are not deleted and have balance data
            balance_sheets = (
                KbaiBalance.query
                .filter_by(id_company=company_id, is_deleted=False)
                .filter(KbaiBalance.balance.isnot(None))
                .order_by(KbaiBalance.created_at.asc())
                .all()
            )
            
            total_count = len(balance_sheets)

            display_balance_sheets = balance_sheets[:2]
            balance_count = len(display_balance_sheets)
            
            # Extract file info as objects with id_balance
            file_names = []
            for balance_sheet in display_balance_sheets:
                file_info = {
                    'id_balance': balance_sheet.id_balance,
                    'file': balance_sheet.file if balance_sheet.file else None
                }
                file_names.append(file_info)
            
            # Flag is true if count >= 2 (user has uploaded 2 balance sheets)
            flag = total_count >= 2
            
            return {
                'balance_sheet_count': balance_count,
                'flag': flag,
                'file_names': file_names,
                'can_compare': flag,
                'step_compare_enabled': flag
            }
            
        except Exception as e:
            current_app.logger.error(f"Error checking balance sheet count for company {company_id}: {str(e)}")
            return {
                'balance_sheet_count': 0,
                'flag': False,
                'file_names': [],
                'can_compare': False,
                'step_compare_enabled': False,
                'error': str(e)
            }
    
    # -----------------------------------------------------------------------
    # FIND ONE - Get pre-dashboard by company ID
    # -----------------------------------------------------------------------
    def findOne(self, company_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Get pre-dashboard by company ID
        
        Args:
            company_id: Company ID
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Check if company exists
            company = KbaiCompany.findOne(id_company=company_id)
            if not company:
                return {
                    'error': 'Not found',
                    'message': 'Company not found'
                }, 404
            
            # Get pre-dashboard record
            pre_dashboard = KbaiPreDashboard.findOne(id_company=company_id)
            
            if not pre_dashboard:
                # Pre-dashboard should have been created when company was created
                # Return detailed diagnostic information to help identify the issue
                error_details = {
                    'error_type': 'Pre-dashboard record missing',
                    'company_id': company_id,
                    'message': 'Pre-dashboard record was not created during company creation',
                    'possible_causes': [
                        'Pre-dashboard creation failed silently during company creation',
                        'Company was created before auto-creation logic was added',
                        'Database constraint violation during creation (foreign key, unique constraint)',
                        'Table schema mismatch between local and staging',
                        'Database permissions issue preventing insert',
                        'Transaction rollback occurred after company creation'
                    ],
                    'diagnostic_info': {
                        'company_exists': True,
                        'company_id': company_id,
                        'company_created_at': company.created_at.isoformat() if hasattr(company, 'created_at') and company.created_at else 'Unknown',
                        'suggestion': 'Check company creation logs for pre-dashboard creation errors. Verify table schema matches between environments.'
                    }
                }
                
                current_app.logger.error(
                    f"Pre-dashboard not found for company {company_id}. "
                    f"Company exists but pre-dashboard was never created. "
                    f"Check company creation logs for errors."
                )
                
                return {
                    'error': 'Not found',
                    'message': 'Pre-dashboard record not found for this company',
                    'details': error_details
                }, 404
            
            
            # Add balance sheet count check with count, flag, and file names
            balance_check = self.check_balance_sheet_count(company_id)
            
            # Auto-update step_upload if 2 or more balance sheets exist
            if balance_check['balance_sheet_count'] >= 2 and not pre_dashboard.step_upload:
                success, update_error = pre_dashboard.update({'step_upload': True})
                if success:
                    logger.info(f"Auto-updated step_upload to true for company {company_id} (balance_count: {balance_check['balance_sheet_count']})")
                    # Re-query to get updated object from database
                    pre_dashboard = KbaiPreDashboard.findOne(id_company=company_id)
                    if pre_dashboard:
                        # Get updated data after step_upload update
                        pre_dashboard_data = pre_dashboard.to_dict()
                    else:
                        logger.error(f"Failed to re-query pre-dashboard after update for company {company_id}")
                        pre_dashboard_data = pre_dashboard.to_dict()
                else:
                    logger.error(f"Failed to auto-update step_upload for company {company_id}: {update_error}")
                    pre_dashboard_data = pre_dashboard.to_dict()
            else:
                # Get pre-dashboard data (no update needed)
                pre_dashboard_data = pre_dashboard.to_dict()
            
            pre_dashboard_data['step_status'] = {
                'balance_sheet_count': balance_check['balance_sheet_count'],
                'flag': balance_check['flag'],
                'file_names': balance_check['file_names'],
                'step_compare_enabled': balance_check['step_compare_enabled'],
                'can_compare': balance_check['can_compare']
            }
            
            return {
                'message': 'Pre-dashboard retrieved successfully',
                'data': pre_dashboard_data,
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving pre-dashboard for company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve pre-dashboard record'
            }, 500
    
    # -----------------------------------------------------------------------
    # UPDATE - Update pre-dashboard information
    # -----------------------------------------------------------------------
    def update(self, company_id: int, update_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Update pre-dashboard information
        
        Args:
            company_id: Company ID
            update_data: Dictionary containing update information
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Check if company exists
            company = KbaiCompany.findOne(id_company=company_id)
            if not company:
                return {
                    'error': 'Not found',
                    'message': 'Company not found'
                }, 404
            
            # Get pre-dashboard record, create if it doesn't exist
            pre_dashboard = KbaiPreDashboard.findOne(id_company=company_id)
            
            if not pre_dashboard:
                # Auto-create pre-dashboard record if it doesn't exist
                pre_dashboard, error = KbaiPreDashboard.create({
                    'id_company': company_id,
                    'step_upload': False,
                    'step_compare': False,
                    'step_competitor': False,
                    'step_predictive': False,
                    'completed_flag': False
                })
                
                if not pre_dashboard or error:
                    current_app.logger.error(f"Failed to create pre-dashboard for company {company_id}: {error}")
                    return {
                        'error': 'Internal server error',
                        'message': 'Failed to create pre-dashboard record'
                    }, 500
            
            # Update pre-dashboard record
            success, error = pre_dashboard.update(update_data)
            
            if not success:
                current_app.logger.error(f"Error updating pre-dashboard: {error}")
                return {
                    'error': 'Internal server error',
                    'message': 'Failed to update pre-dashboard record'
                }, 500
            
            # Get updated record
            updated_pre_dashboard = KbaiPreDashboard.findOne(id_company=company_id)
            
            return {
                'message': 'Pre-dashboard updated successfully',
                'data': updated_pre_dashboard.to_dict(),
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error updating pre-dashboard for company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to update pre-dashboard record'
            }, 500
    

# Create service instance
kbai_pre_dashboard_service = KbaiPreDashboardService()
