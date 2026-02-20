import logging
from typing import Dict, Any, Tuple
from datetime import datetime

from flask import current_app, request
from src.common.localization import get_message

from src.app.database.models import KbaiCompany, TbLicences, TbUser, TbUserCompany, kbai_balance
from src.app.api.v1.services.public.license_service import LicenseManager
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
        locale = request.headers.get('Accept-Language', 'en')
        
        # Superadmin and Staff have full access
        if user_role in ['superadmin', 'staff']:
            return True, ""
        
        # User role cannot manage companies
        if user_role == 'user':
            return False, get_message('user_role_cannot_manage_companies', locale)
        
        # For create action, admin can create
        if action == 'create':
            if user_role == 'admin':
                return True, ""
            return False, get_message('only_admin_create_companies', locale)
        
        # For update/delete, check if user is directly mapped to this company
        if company is None:
            return False, get_message('company_not_found', locale)
        
        # Check if user is mapped to this company in tb_user_company (direct ownership)
        user_company = TbUserCompany.query.filter_by(
            id_user=current_user.id_user,
            id_company=company.id_company
        ).first()
        
        if user_company:
            # User is directly mapped to this company
            return True, ""
        
        # Admin can only manage companies they are directly mapped to
        return False, get_message('manage_own_companies_only', locale, action=action)
    
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
            is_competitor = bool(company_data.get('is_competitor', False))
            parent_company_id = company_data.get('parent_company_id', None)
            locale = request.headers.get('Accept-Language', 'en')
            if parent_company_id and is_competitor:
                parent_company = KbaiCompany.query.filter_by(id_company=parent_company_id, is_deleted=False,is_competitor=False).first()
                if not parent_company:
                    return {
                        'error': get_message('parent_company_not_found', locale),
                        'message': get_message('parent_company_not_found_msg', locale, id=parent_company_id)
                    }, 404
            if is_competitor:
                licence_id = LicenseManager.create_competitor_licence()
            else:
                if not current_user_id:
                    return {
                        'error': get_message('user_required_title', locale),
                        'message': get_message('user_login_required', locale)
                        }, 400
                if current_user_id:
                    current_user = TbUser.findOne(id_user=current_user_id)
                    if not current_user:
                        return {
                            'error': get_message('user_not_found', locale),
                            'message': get_message('current_user_not_exist', locale)
                        }, 404
                    
                    # Check if user can create companies
                    has_permission, error_msg = self.check_company_permission(
                        current_user=current_user,
                        company=None,  # No company yet for create
                        action='create'
                    )
                    
                    if not has_permission:
                        return {
                            'error': get_message('permission_denied', locale),
                            'message': error_msg
                        }, 403
                    
                    # LICENSE VALIDATION: Check if user has available licenses
                    is_valid, error_msg, stats = LicenseManager.validate_license_availability_for_company(current_user_id)
                    
                    if not is_valid:
                        return {
                            'error': get_message('no_licenses_title', locale),
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
                            'error': get_message('no_licenses_title', locale),
                            'message': get_message('no_licenses_create_company_msg', locale),
                            'license_stats': stats
                        }, 400
                    
                    # Set the auto-selected license
                    licence_id = available_license[0]
                    current_app.logger.info(f"Auto-selected license ID {licence_id} for company creation by user {current_user_id}")
                    # Add license to company data
            company_data['id_licence'] = licence_id

            # VALIDATION: Check region and ateco existence in KbaiSector
            region_val = company_data.get('region', '').strip() if company_data.get('region') else None
            ateco_val = company_data.get('ateco', '').strip() if company_data.get('ateco') else None
            
            if not region_val or not ateco_val:
                return {
                    'message': get_message('region_and_ateco_required', locale),
                    'success': False
                }, 400
                
            from src.app.database.models.kbai import KbaiSector
            from sqlalchemy import func
            
            division = ateco_val[:2] if len(ateco_val) >= 2 else ateco_val
            sector_exists = db.session.query(KbaiSector).filter(
                KbaiSector.division == division,
                func.upper(KbaiSector.region) == func.upper(region_val)
            ).first()
            
            if not sector_exists:
                return {
                    'message': get_message('invalid_region_or_ateco', locale),
                    'success': False
                }, 400

            # Use model function to create company
            company, error = KbaiCompany.create(company_data)
            
            if error:
                if "required" in error.lower():
                    return {
                        'error': get_message('validation_error', locale),
                        'message': error
                    }, 400
                elif "already exists" in error.lower():
                    return {
                        'error': get_message('validation_error', locale),
                        'message': error
                    }, 400
                else:
                    msg = f"Database error creating company: {error}"
                    print(msg)
                    current_app.logger.error(msg)
                    return {
                        'error': get_message('database_error', locale),
                        'message': get_message('company_create_failed', locale)
                    }, 500
            
            current_app.logger.info(f"KBAI company created: {company.id_company}")
            
            # Process region and ateco if provided (using validated/stripped values)
            region_value = region_val
            ateco_value = ateco_val
            
            # Handle region -> create/link zone
            if region_value:
                try:
                    from src.app.database.models.kbai import KbaiZone, KbaiCompanyZone
                    
                    # Create a zone with the region
                    zone_data = {
                        'region': region_value,
                        'country': 'Italy'  # Default to Italy as per CreditSafe integration
                    }
                    new_zone, zone_error = KbaiZone.create(zone_data)
                    
                    if zone_error:
                        current_app.logger.warning(f"Error creating zone for company {company.id_company}: {zone_error}")
                    else:
                        # Link company to zone
                        company_zone, cz_error = KbaiCompanyZone.create({
                            'id_company': company.id_company,
                            'id_zone': new_zone.id_zone,
                            'primary_flag': True
                        })
                        if cz_error:
                            current_app.logger.warning(f"Error linking company to zone: {cz_error}")
                        else:
                            current_app.logger.info(f"Company {company.id_company} linked to zone {new_zone.id_zone}")
                except Exception as e:
                    current_app.logger.error(f"Error processing region for company {company.id_company}: {str(e)}")
                    # Don't fail company creation if region processing fails
            
            # Handle ateco -> lookup and link sector
            if ateco_value and region_value:
                try:
                    from src.app.database.models.kbai import KbaiSector, KbaiCompanySector
                    from sqlalchemy import func
                    
                    # Extract division (first 2 digits of ateco)
                    division = ateco_value[:2] if len(ateco_value) >= 2 else ateco_value
                    
                    # Lookup sector by division and region
                    sector = db.session.query(KbaiSector).filter(
                        KbaiSector.division == division,
                        func.upper(KbaiSector.region) == func.upper(region_value)
                    ).first()
                    
                    if sector:
                        # Link company to sector
                        company_sector, cs_error = KbaiCompanySector.create({
                            'id_company': company.id_company,
                            'id_sector': sector.id_sector,
                            'primary_flag': True
                        })
                        if cs_error:
                            current_app.logger.warning(f"Error linking company to sector: {cs_error}")
                        else:
                            current_app.logger.info(f"Company {company.id_company} linked to sector {sector.id_sector}")
                    else:
                        current_app.logger.warning(f"No sector found for division={division} and region={region_value}")
                except Exception as e:
                    current_app.logger.error(f"Error processing ateco for company {company.id_company}: {str(e)}")
                    # Don't fail company creation if ateco processing fails
            elif ateco_value and not region_value:
                current_app.logger.warning(f"Ateco provided without region for company {company.id_company}, cannot link sector")
            
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

            # Trigger CreditSafe balance import
            try:
                from src.app.api.v1.services.common.company_import_service import CompanyImportService
                CompanyImportService.import_company_balances(company.id_company, company.vat)
            except Exception as e:
                msg = f"Error triggering balance import for company {company.id_company}: {str(e)}"
                print(msg)
                current_app.logger.error(msg)
            
            return {
                'message': get_message('company_created_success', locale),
                'data': company.to_dict(),
                'success': True
            }, 201
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error creating company: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('company_create_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': get_message('company_not_found', locale)
                }, 404
            
            # Fetch region and ateco details
            company_data = company.to_dict()
            
            # 1. Get region from Primary Zone
            from src.app.database.models.kbai import KbaiCompanyZone, KbaiZone
            zone_mapping = KbaiCompanyZone.query.filter_by(
                id_company=company.id_company, 
                primary_flag=True
            ).first()
            
            if zone_mapping:
                zone = KbaiZone.query.get(zone_mapping.id_zone)
                if zone:
                    company_data['region'] = zone.region
            
            # 2. Get ateco from Primary Sector
            from src.app.database.models.kbai import KbaiCompanySector, KbaiSector
            sector_mapping = KbaiCompanySector.query.filter_by(
                id_company=company.id_company, 
                primary_flag=True
            ).first()
            
            if sector_mapping:
                sector = KbaiSector.query.get(sector_mapping.id_sector)
                if sector:
                    company_data['ateco'] = sector.division

            return {
                'message': get_message('company_retrieved_success', locale),
                'data': company_data,
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error retrieving company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('company_retrieve_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': get_message('company_not_found', locale)
                }, 404
            
            # Check permissions
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                if not current_user:
                    return {
                        'error': get_message('user_not_found', locale),
                        'message': get_message('current_user_not_exist', locale)
                    }, 404
                
                has_permission, error_msg = self.check_company_permission(
                    current_user=current_user,
                    company=company,
                    action='update'
                )
                
                if not has_permission:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
            
            # Use model function to update company
            # Extract region and ateco from update_data to handle separately
            region_value = update_data.pop('region', None)
            ateco_value = update_data.pop('ateco', None)
            
            # Store current values for potential sector re-mapping
            current_region = None
            current_ateco = None
            
            from src.app.database.models.kbai import KbaiCompanyZone, KbaiZone, KbaiCompanySector, KbaiSector
            
            # Get current region mapping
            zone_mapping = KbaiCompanyZone.query.filter_by(
                id_company=company.id_company, 
                primary_flag=True
            ).first()
            if zone_mapping:
                zone = KbaiZone.query.get(zone_mapping.id_zone)
                if zone:
                    current_region = zone.region
            
            # Get current ateco mapping
            sector_mapping = KbaiCompanySector.query.filter_by(
                id_company=company.id_company, 
                primary_flag=True
            ).first()
            if sector_mapping:
                sector = KbaiSector.query.get(sector_mapping.id_sector)
                if sector:
                    current_ateco = sector.division

            # VALIDATION: Check region and ateco combination if being updated
            new_region = (region_value.strip() if region_value else None) or current_region
            new_ateco = (ateco_value.strip() if ateco_value else None) or current_ateco
            
            if region_value or ateco_value:
                if not new_region or not new_ateco:
                    return {
                        'message': get_message('region_and_ateco_required', locale),
                        'success': False
                    }, 400
                
                from sqlalchemy import func
                div = new_ateco[:2] if len(new_ateco) >= 2 else new_ateco
                s_exists = db.session.query(KbaiSector).filter(
                    KbaiSector.division == div,
                    func.upper(KbaiSector.region) == func.upper(new_region)
                ).first()
                
                if not s_exists:
                    return {
                        'message': get_message('invalid_region_or_ateco', locale),
                        'success': False
                    }, 400

            success, error = company.update(update_data)
            
            if not success:
                current_app.logger.error(f"Error updating company {company_id}: {error}")
                return {
                    'error': get_message('database_error', locale),
                    'message': get_message('company_update_failed', locale)
                }, 500
            
            if success:
                # 1. Update Region if provided
                if region_value:
                    try:
                        # Create/Find zone entry
                        zone_data = {
                            'region': region_value,
                            'country': 'Italy'
                        }
                        new_zone, zone_error = KbaiZone.create(zone_data)
                        
                        if not zone_error:
                            # Update or create link
                            if zone_mapping:
                                zone_mapping.id_zone = new_zone.id_zone
                            else:
                                KbaiCompanyZone.create({
                                    'id_company': company.id_company,
                                    'id_zone': new_zone.id_zone,
                                    'primary_flag': True
                                })
                            db.session.commit()
                            current_region = region_value
                            current_app.logger.info(f"Updated region to {region_value} for company {company_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error updating region for company {company_id}: {str(e)}")

                # 2. Update Sector if ateco or region changed
                a_val = new_ateco
                r_val = new_region
                
                if (ateco_value or region_value) and a_val and r_val:
                    try:
                        from sqlalchemy import func
                        division = a_val[:2] if len(a_val) >= 2 else a_val
                        sector = db.session.query(KbaiSector).filter(
                            KbaiSector.division == division,
                            func.upper(KbaiSector.region) == func.upper(r_val)
                        ).first()
                        
                        if sector:
                            if sector_mapping:
                                sector_mapping.id_sector = sector.id_sector
                            else:
                                KbaiCompanySector.create({
                                    'id_company': company.id_company,
                                    'id_sector': sector.id_sector,
                                    'primary_flag': True
                                })
                            db.session.commit()
                            current_app.logger.info(f"Updated sector mapping to division {division} for company {company_id}")
                        else:
                            current_app.logger.warning(f"No sector found for division {division} and region {r_val}")
                    except Exception as e:
                        current_app.logger.error(f"Error updating sector for company {company_id}: {str(e)}")

            current_app.logger.info(f"KBAI company updated: {company_id}")
            
            # Refetch fully updated company data including region and ateco
            fetch_response, _ = self.findOne(company_id)
            company_data = fetch_response.get('data', company.to_dict())
            
            return {
                'message': get_message('company_updated_success', locale),
                'data': company_data,
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error updating company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('company_update_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
            # Use flexible model method with is_deleted filter
            company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
            
            if not company:
                return {
                    'error': 'Not found',
                    'message': get_message('company_not_found', locale)
                }, 404
            
            # Check permissions
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                if not current_user:
                    return {
                        'error': get_message('user_not_found', locale),
                        'message': get_message('current_user_not_exist', locale)
                    }, 404
                
                has_permission, error_msg = self.check_company_permission(
                    current_user=current_user,
                    company=company,
                    action='delete'
                )
                
                if not has_permission:
                    return {
                        'error': get_message('permission_denied', locale),
                        'message': error_msg
                    }, 403
            
            # Use model function to delete company
            success, error = company.delete()
            
            if not success:
                current_app.logger.error(f"Error deleting company {company_id}: {error}")
                return {
                    'error': get_message('database_error', locale),
                    'message': get_message('company_delete_failed', locale)
                }, 500
            
            current_app.logger.info(f"KBAI company deleted: {company_id}")
            
            return {
                'message': get_message('company_deleted_success', locale),
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error deleting company {company_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('company_delete_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
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
                is_competitor=False,
                **filters
            )
            
            if error:
                current_app.logger.error(f"Error finding companies: {error}")
                return {
                    'error': f'Internal server error: {error}',
                    'message': get_message('companies_retrieve_failed', locale)
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
                'message': get_message('companies_retrieved_success', locale),
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
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error finding companies: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('companies_retrieve_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
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
                    'message': get_message('balance_sheets_required_2', locale),
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
                    'message': get_message('no_comparison_found', locale),
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
                    'message': get_message('incomplete_comparison_data', locale),
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
                    'message': get_message('comparison_deleted_balances', locale),
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
                    'message': get_message('ebitda_values_not_found', locale),
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
                    'message': get_message('ebitda_zero_error', locale),
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
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error calculating EBITDA status for company {company_id}: {str(e)}")
            return {
                'status': None,
                'message': get_message('status_calculation_error', locale, error=str(e)),
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
            locale = request.headers.get('Accept-Language', 'en')
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
                    'message': get_message('no_companies_assigned', locale, user=tb_user_id),
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
                KbaiCompany.is_deleted == False,
                KbaiCompany.is_competitor == False
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
                'message': get_message('user_companies_retrieved_success', locale, user=tb_user_id),
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
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error finding companies for user {tb_user_id}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('user_companies_retrieve_failed', locale)
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
            locale = request.headers.get('Accept-Language', 'en')
            # Get all company IDs assigned to this user
            user_company_mappings = TbUserCompany.query.filter_by(
                id_user=tb_user_id
            ).all()
            company_ids = [mapping.id_company for mapping in user_company_mappings]
            
            current_app.logger.info(f"User {tb_user_id} has {len(company_ids)} companies mapped: {company_ids}")
            
            if not company_ids:
                return {
                    'message': get_message('no_companies_assigned', locale, user=tb_user_id),
                    'data': {
                        'companies' : [],
                    },
                    'success': True
                }, 200

            # Get companies using filter and fetchall
            companies = db.session.query(KbaiCompany).filter(
                KbaiCompany.id_company.in_(company_ids),
                KbaiCompany.is_deleted == False,
                KbaiCompany.is_competitor == False
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
    
        # -----------------------------------------------------------------------
    # FIND COMPETITOR COMPANIES - Get competitor companies (with pagination)
    # -----------------------------------------------------------------------
    def find_competitor_companies(self, id_company: int, search: str = None, status: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Get competitor companies
        
        Args:
            id_company: Parent company ID
            search: Search term
            status: Status filter
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            if not id_company:
                return {
                    'error': get_message('parent_company_id_required', locale),
                    'message': get_message('parent_company_id_required', locale)
                }, 400
                
            # Build query for companies
            from sqlalchemy import or_
            query = KbaiCompany.query.filter(
                KbaiCompany.is_deleted == False,
                KbaiCompany.is_competitor == True,
                KbaiCompany.parent_company_id == id_company
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
            
            # Get all companies
            companies = query.order_by(KbaiCompany.created_at.desc()).all()
            
            # Extract company name and ID
            competitor_companies_data = [{'company_name': company.company_name, 'id_company': company.id_company} for company in companies]
            
            return {
                'message': get_message('competitor_companies_retrieved_success', locale),
                'data': {
                    "competitor_companies" : competitor_companies_data
                },
                'success': True
            }, 200
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            current_app.logger.error(f"Error finding competitor companies for parent company {id_company}: {str(e)}")
            return {
                'error': 'Internal server error',
                'message': get_message('competitor_companies_retrieve_failed', locale, id_company=id_company)
            }, 500

# Create service instance
kbai_companies_service = KbaiCompaniesService()