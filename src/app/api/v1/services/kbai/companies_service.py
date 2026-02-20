import logging
from typing import Dict, Any, Tuple
from datetime import datetime

from flask import current_app

from src.app.database.models import KbaiCompany, TbLicences, TbUser, TbUserCompany, kbai_balance
from src.extensions import db

logger = logging.getLogger(__name__)

class KbaiCompaniesService:
    """
    Service for managing KBAI companies.
    Provides 5 essential CRUD operations: create, update, delete, findOne, find
    """
    
    def __init__(self):
        self.default_page_size = 10
        self.max_page_size = 100
    
    # =============================================================================
    # COMPANY PERMISSION HELPER
    # =============================================================================
    
    def check_company_permission(
        self, 
        current_user: 'TbUser', 
        company: 'KbaiCompany' = None, 
        action: str = 'manage'
    ) -> Tuple[bool, str]:
        """
        Check if current user has permission to perform action on company
        
        Args:
            current_user: User performing the action
            company: Company being acted upon (None for create action)
            action: Type of action ('create', 'update', 'delete', 'view')
            
        Returns:
            Tuple of (has_permission, error_message)
            
        Permission Rules (Simplified):
        - superadmin: Can manage ALL companies
        - staff: Can manage ALL companies
        - admin: Can manage ONLY companies they directly created (mapped in tb_user_company)
        - user role: Cannot manage companies (403 error)
        """
        user_role = current_user.role.lower()
        
        # Superadmin and Staff have full access
        if user_role in ['superadmin', 'staff']:
            return True, ""
        
        # User role cannot manage companies
        if user_role == 'user':
            return False, "Users with role 'user' cannot manage companies"
        
        # For create action, admin can create
        if action == 'create':
            if user_role == 'admin':
                return True, ""
            return False, f"Only superadmin, staff, and admin can create companies"
        
        # For update/delete, check if user is directly mapped to this company
        if company is None:
            return False, "Company not found"
        
        # Check if user is mapped to this company in tb_user_company (direct ownership)
        user_company = TbUserCompany.query.filter_by(
            id_user=current_user.id_user,
            id_company=company.id_company
        ).first()
        
        if user_company:
            # User is directly mapped to this company
            return True, ""
        
        # Admin can only manage companies they are directly mapped to
        return False, f"You can only {action} companies you created"
    
    # ---------------------------------------------------------------------------
    # CREATE - Create a new company
    # ---------------------------------------------------------------------------
    def create(self, company_data: Dict[str, Any], current_user_id: int = None) -> Tuple[Dict[str, Any], int]:
        """
        Create a new KBAI company with permission check
        
        Args:
            company_data: Dictionary containing company information
            current_user_id: ID of user creating the company
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Check permissions
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                if not current_user:
                    return {
                        'error': 'User not found',
                        'message': 'Current user does not exist'
                    }, 404
                
                # Check if user can create companies
                has_permission, error_msg = self.check_company_permission(
                    current_user=current_user,
                    company=None,  # No company yet for create
                    action='create'
                )
                
                if not has_permission:
                    return {
                        'error': 'Permission denied',
                        'message': error_msg
                    }, 403
                
                # LICENSE VALIDATION: Check if user has available licenses
                from src.app.api.v1.services.public.license_service import LicenseManager
                is_valid, error_msg, stats = LicenseManager.validate_license_availability_for_company(current_user_id)
                
                if not is_valid:
                    return {
                        'error': 'No licenses available',
                        'message': error_msg,
                        'license_stats': stats
                    }, 400
                
                # AUTO-SELECT AVAILABLE LICENSE: Get one available license from admin's licenses
                from src.app.database.models.public.licence_admin import LicenceAdmin
                
                # Get admin's licenses that are NOT used by any active company
                available_license = db.session.query(LicenceAdmin.id_licence)\
                    .filter(LicenceAdmin.id_user == current_user_id)\
                    .filter(~LicenceAdmin.id_licence.in_(
                        db.session.query(KbaiCompany.id_licence)
                        .filter(KbaiCompany.id_licence.isnot(None))
                    ))\
                    .first()
                                    
                if not available_license:
                    return {
                        'error': 'No licenses available',
                        'message': 'You do not have any available licenses to create a company. All your licenses are currently in use.',
                        'license_stats': stats
                    }, 400
                
                # Set the auto-selected license
                licence_id = available_license[0]
                current_app.logger.info(f"Auto-selected license ID {licence_id} for company creation by user {current_user_id}")
                # Add license to company data
                company_data['id_licence'] = licence_id
            
            # Use model function to create company
            company, error = KbaiCompany.create(company_data)
            
            if error:
                if "required" in error.lower():
                    return {
                        'error': 'Validation error',
                        'message': error
                    }, 400
                elif "already exists" in error.lower():
                    return {
                        'error': 'Validation error',
                        'message': error
                    }, 400
                else:
                    current_app.logger.error(f"Database error creating company: {error}")
                    return {
                        'error': 'Database error',
                        'message': 'Failed to create company'
                    }, 500
            
            current_app.logger.info(f"KBAI company created: {company.id_company}")
            
            # Create mapping in tb_user_company if current_user_id provided
            if current_user_id:
                try:
                    user_company = TbUserCompany(
                        id_user=current_user_id,
                        id_company=company.id_company,
                        date_assigned=datetime.utcnow()
                    )
                    db.session.add(user_company)
                    db.session.commit()
                    current_app.logger.info(f"User {current_user_id} mapped to company {company.id_company}")
                except Exception as e:
                    current_app.logger.error(f"Error creating user-company mapping: {str(e)}")
                    # Don't fail company creation if mapping fails
            
            return {
                'message': 'Company created successfully',
                'data': company.to_dict(),
                'success': True
            }, 201
            
        except Exception as e:
            current_app.logger.error(f"Error creating company: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to create company'
            }, 500
    
    # -----------------------------------------------------------------------
    # FIND ONE - Get company by ID
    # -----------------------------------------------------------------------
    def findOne(self, company_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Get company by ID
        
        Args:
            company_id: Company ID
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': 'Company not found'
                }, 404
            
            return {
                'message': 'Company retrieved successfully',
                'data': company.to_dict(),
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve company'
            }, 500
    
    # -----------------------------------------------------------------------
    # UPDATE - Update company information
    # -----------------------------------------------------------------------
    def update(self, company_id: int, update_data: Dict[str, Any], current_user_id: int = None) -> Tuple[Dict[str, Any], int]:
        """
        Update company information with permission check
        
        Args:
            company_id: Company ID
            update_data: Dictionary containing fields to update
            current_user_id: ID of user updating the company
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': 'Company not found'
                }, 404
            
            # Check permissions
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                if not current_user:
                    return {
                        'error': 'User not found',
                        'message': 'Current user does not exist'
                    }, 404
                
                has_permission, error_msg = self.check_company_permission(
                    current_user=current_user,
                    company=company,
                    action='update'
                )
                
                if not has_permission:
                    return {
                        'error': 'Permission denied',
                        'message': error_msg
                    }, 403
            
            # Use model function to update company
            success, error = company.update(update_data)
            
            if not success:
                current_app.logger.error(f"Error updating company {company_id}: {error}")
                return {
                    'error': 'Database error',
                    'message': 'Failed to update company'
                }, 500
            
            current_app.logger.info(f"KBAI company updated: {company_id}")
            company_data = company.to_dict()
            return {
                'message': 'Company updated successfully',
                'data': company_data,
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error updating company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to update company'
            }, 500
    
    # -----------------------------------------------------------------------
    # DELETE - Delete company
    # -----------------------------------------------------------------------
    def delete(self, company_id: int, current_user_id: int = None) -> Tuple[Dict[str, Any], int]:
        """
        Delete company with permission check
        
        Args:
            company_id: Company ID
            current_user_id: ID of user deleting the company
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': 'Company not found'
                }, 404
            
            # Check permissions
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                if not current_user:
                    return {
                        'error': 'User not found',
                        'message': 'Current user does not exist'
                    }, 404
                
                has_permission, error_msg = self.check_company_permission(
                    current_user=current_user,
                    company=company,
                    action='delete'
                )
                
                if not has_permission:
                    return {
                        'error': 'Permission denied',
                        'message': error_msg
                    }, 403
            
            # Use model function to delete company
            success, error = company.delete()
            
            if not success:
                current_app.logger.error(f"Error deleting company {company_id}: {error}")
                return {
                    'error': 'Database error',
                    'message': 'Failed to delete company'
                }, 500
            
            current_app.logger.info(f"KBAI company deleted: {company_id}")
            
            return {
                'message': 'Company deleted successfully',
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error deleting company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to delete company'
            }, 500
    
    # -----------------------------------------------------------------------
    # FIND - Find companies with filtering and pagination
    # -----------------------------------------------------------------------
    def find(self, page: int = 1, per_page: int = None, 
             search: str = None, **filters) -> Tuple[Dict[str, Any], int]:
        """
        Find companies with filtering and pagination (always sorted by latest first)
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for company name, contact person, or email
            **filters: Field filters like email='test@example.com', id_licence=1, status_flag='ACTIVE', etc.
            
        Returns:
            Tuple of (response_data, status_code)
            
        Examples:
            service.find()  # Get all companies (latest first)
            service.find(email='test@example.com')  # Filter by email
            service.find(id_licence=1, status_flag='ACTIVE')  # Multiple filters
            service.find(search='Tech')  # Search in company name
        """
        try:
            # Validate pagination parameters
            if per_page is None:
                per_page = self.default_page_size
            else:
                per_page = min(per_page, self.max_page_size)
            
            page = max(1, page)
            
            # Use flexible model method with is_deleted filter
            companies, total, error = KbaiCompany.find(
                page=page,
                per_page=per_page,
                search=search,
                is_deleted=False,
                **filters
            )
            
            if error:
                current_app.logger.error(f"Error finding companies: {error}")
                return {
                    'error': 'Internal server error',
                    'message': 'Failed to retrieve companies'
                }, 500
            
            # Convert to dictionaries
            companies_data = []
            for company in companies:
                if hasattr(company, 'to_dict'):
                    # It's a KbaiCompany object
                    companies_data.append(company.to_dict())
                else:
                    # It's a Row object from select_columns
                    companies_data.append(dict(company._mapping))
            
            for company_data in companies_data:
                ebitda_status = self.calculate_ebitda_status(company_data['id_company'])
                company_data['ebitda_status'] = ebitda_status
                
            return {
                'message': 'Companies retrieved successfully',
                'data': companies_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                },
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error finding companies: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve companies'
            }, 500
    
    # -----------------------------------------------------------------------
    # EBITDA STATUS CALCULATION
    # -----------------------------------------------------------------------
    def calculate_ebitda_status(self, company_id: int) -> Dict[str, Any]:
        """
        Calculate EBITDA status (red/yellow/green) based on latest comparison.
        
        Formula:
        - red: (EBITDA2 - EBITDA1)/EBITDA2 < -1%
        - yellow: -1% <= (EBITDA2 - EBITDA1)/EBITDA2 <= 0%
        - green: (EBITDA2 - EBITDA1)/EBITDA2 > 0
        
        Args:
            company_id: Company ID
            
        Returns:
            Dictionary with status, ebitda1, ebitda2, and calculation details
        """
        try:
            from src.app.database.models import (
                KbaiAnalysis, 
                KbaiAnalysisKpi, 
                KbaiBalance, 
                KbaiKpiValue
            )
            
            # Check if company has at least 2 active (non-deleted) balance sheets
            active_balance_count = (
                KbaiBalance.query
                .filter_by(id_company=company_id)
                .filter(KbaiBalance.is_deleted == False)
                .count()
            )
            
            if active_balance_count < 2:
                return {
                    'status': None,
                    'message': 'At least 2 active balance sheets required.',
                    'ebitda1': None,
                    'ebitda2': None
                }
            
            # Get latest analysis for this company
            latest_analysis = (
                db.session.query(KbaiAnalysis)
                .join(KbaiAnalysisKpi, KbaiAnalysis.id_analysis == KbaiAnalysisKpi.id_analysis)
                .join(KbaiBalance, KbaiAnalysisKpi.id_balance == KbaiBalance.id_balance)
                .filter(
                    KbaiBalance.id_company == company_id,
                    KbaiBalance.is_deleted == False,
                    KbaiAnalysis.analysis_type == 'year_comparison'
                )
                .distinct()
                .order_by(KbaiAnalysis.time.desc())
                .first()
            )
            
            if not latest_analysis:
                return {
                    'status': None,
                    'message': 'No comparison found for this company',
                    'ebitda1': None,
                    'ebitda2': None
                }
            
            # Get analysis KPIs to get balance IDs
            analysis_kpis = (
                KbaiAnalysisKpi.query
                .filter_by(id_analysis=latest_analysis.id_analysis)
                .order_by(KbaiAnalysisKpi.id_balance)
                .all()
            )
            
            if len(analysis_kpis) < 2:
                return {
                    'status': None,
                    'message': 'Incomplete comparison data',
                    'ebitda1': None,
                    'ebitda2': None
                }
            
            # Get balance IDs (should be 2 for comparison)
            balance_ids = [ak.id_balance for ak in analysis_kpis[:2]]
            
            # Get balances to determine which is year1 and year2 (filter deleted)
            balances = (
                KbaiBalance.query
                .filter(KbaiBalance.id_balance.in_(balance_ids))
                .filter(KbaiBalance.is_deleted == False)  # Filter out deleted balance sheets
                .all()
            )
            
            # Check if we have both balances (valid comparison)
            if len(balances) < 2:
                return {
                    'status': None,
                    'message': 'Comparison references deleted balance sheets. Valid comparison not available.',
                    'ebitda1': None,
                    'ebitda2': None
                }
            
            # Sort by year to get year1 (older) and year2 (newer)
            balances_sorted = sorted(balances, key=lambda b: b.year)
            balance_year1 = balances_sorted[0]
            balance_year2 = balances_sorted[1] if len(balances_sorted) > 1 else balances_sorted[0]
            
            # Get EBITDA values from kpi_values table
            # EBITDA KPI code is "m_cod_380"
            ebitda1_value = KbaiKpiValue.query.filter_by(
                id_balance=balance_year1.id_balance,
                kpi_code='m_cod_380',
                kpi_name='EBITDA'
            ).first()
            
            ebitda2_value = KbaiKpiValue.query.filter_by(
                id_balance=balance_year2.id_balance,
                kpi_code='m_cod_380',
                kpi_name='EBITDA'
            ).first()
            
            if not ebitda1_value or not ebitda2_value:
                return {
                    'status': None,
                    'message': 'EBITDA values not found in kpi_values table',
                    'ebitda1': None,
                    'ebitda2': None
                }
            
            ebitda1 = float(ebitda1_value.value)
            ebitda2 = float(ebitda2_value.value)
            
            # Calculate status based on formula: (EBITDA2 - EBITDA1)/EBITDA2
            if ebitda2 == 0:
                # Avoid division by zero
                return {
                    'status': None,
                    'message': 'Cannot calculate status: EBITDA2 is zero',
                    'ebitda1': ebitda1,
                    'ebitda2': ebitda2
                }
            
            change_ratio = (ebitda2 - ebitda1) / ebitda2
            change_percentage = change_ratio * 100
            
            # Determine status
            if change_ratio < -0.01:  # < -1%
                status = 'red'
            elif -0.01 <= change_ratio <= 0:  # -1% <= ratio <= 0%
                status = 'yellow'
            else:  # > 0%
                status = 'green'
            
            return {
                'status': status,
                'change_percentage': round(change_percentage, 2)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error calculating EBITDA status for company {company_id}: {str(e)}")
            return {
                'status': None,
                'message': f'Error calculating status: {str(e)}',
                'ebitda1': None,
                'ebitda2': None
            }
    
    # -----------------------------------------------------------------------
    # FIND BY USER - Get companies assigned to specific user (with pagination)
    # -----------------------------------------------------------------------
    def find_by_user(self, tb_user_id: int, page: int = 1, per_page: int = None, 
                     search: str = None, status: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Get companies assigned to a specific user
        
        Args:
            tb_user_id: User ID to get companies for
            page: Page number (1-based)
            per_page: Items per page
            search: Search term
            status: Status filter
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Validate pagination parameters
            if per_page is None:
                per_page = self.default_page_size
            else:
                per_page = min(per_page, self.max_page_size)
            
            page = max(1, page)
            
            # Get company IDs for this user from tb_user_company
            user_company_mappings = TbUserCompany.query.filter_by(id_user=tb_user_id).all()
            company_ids = [mapping.id_company for mapping in user_company_mappings]
            
            if not company_ids:
                # User has no companies assigned
                return {
                    'message': f'No companies assigned to user {tb_user_id}',
                    'data': {
                        'companies' : [],
                        'pagination': {
                            'page': page,
                            'per_page': per_page,
                            'total': 0,
                            'pages': 0
                        },
                    },
                    'success': True
                }, 200
            
            # Build query for companies
            from sqlalchemy import or_
            query = KbaiCompany.query.filter(
                KbaiCompany.id_company.in_(company_ids),
                KbaiCompany.is_deleted == False
            )
            
            # Apply search filter if provided
            if search:
                query = query.filter(
                    or_(
                        KbaiCompany.company_name.ilike(f'%{search}%'),
                        KbaiCompany.contact_person.ilike(f'%{search}%'),
                        KbaiCompany.email.ilike(f'%{search}%')
                    )
                )
            
            # Apply status filter if provided
            if status:
                query = query.filter(KbaiCompany.status_flag == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and sorting (latest first)
            offset = (page - 1) * per_page
            companies = query.order_by(KbaiCompany.created_at.desc()).offset(offset).limit(per_page).all()
            
            # Convert to dict
            companies_data = [company.to_dict() for company in companies]
            
            # Add EBITDA status to each company
            for company_data in companies_data:
                ebitda_status = self.calculate_ebitda_status(company_data['id_company'])
                company_data['ebitda_status'] = ebitda_status
            
            return {
                'message': f'Companies for user {tb_user_id} retrieved successfully',
                'data': {
                    "companies" : companies_data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    },
                },
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Error finding companies for user {tb_user_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve user companies'
            }, 500

    # -----------------------------------------------------------------------
    # FIND COMPANIES - Get simple list for dropdown (no pagination)
    # -----------------------------------------------------------------------
    def find_companies(self, tb_user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Get simple list of companies for dropdown
        Returns only id_company and company_name, no pagination
        
        Args:
            tb_user_id: User ID to get companies for
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            # Get all company IDs assigned to this user
            user_company_mappings = TbUserCompany.query.filter_by(
                id_user=tb_user_id
            ).all()
            company_ids = [mapping.id_company for mapping in user_company_mappings]
            
            current_app.logger.info(f"User {tb_user_id} has {len(company_ids)} companies mapped: {company_ids}")
            
            if not company_ids:
                return {
                    'message': f'No companies assigned to user {tb_user_id}',
                    'data': {
                        'companies' : [],
                    },
                    'success': True
                }, 200

            # Get companies using filter and fetchall
            companies = db.session.query(KbaiCompany).filter(
                KbaiCompany.id_company.in_(company_ids),
                KbaiCompany.is_deleted == False
            ).order_by(KbaiCompany.company_name.asc()).all()
            
            current_app.logger.info(f"Found {len(companies)} active companies for user {tb_user_id}")
            
            # Return only id_company and company_name
            companies_data = [
                {
                    'id_company': company.id_company,
                    'company_name': company.company_name
                }
                for company in companies
            ]
            
            return {
                'message': 'Companies list retrieved successfully',
                'data': {
                    'companies' : companies_data,
                },
                'success': True
            }, 200

        except Exception as e:
            current_app.logger.error(f"Error finding companies for user {tb_user_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': 'Failed to retrieve user companies'
            }, 500

# Create service instance
kbai_companies_service = KbaiCompaniesService()