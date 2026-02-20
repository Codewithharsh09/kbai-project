"""
Auth User Service - User Management Business Logic

Clean service with only used methods:
- get_users_list()
- get_user_details()
- update_user()
- delete_user()
- change_user_password()
- create_user_in_auth0() - NEW for create API

Author: Flask Enterprise Template
License: MIT
"""

from typing import Dict, Tuple, Any
from sqlalchemy import or_, func
from flask import current_app, request
from marshmallow import ValidationError
from src.common.localization import get_message

from src.app.database.models import TbUser, UserTempData, TbUserCompany, KbaiCompany, TbOtp, LicenceAdmin
from src.app.api.schemas.public.auth_schemas import (
    UpdateUserSchema,
    ChangePasswordSchema
)
from src.extensions import db


# ----------------------------------------------------------------------------
# Auth User Services
# ----------------------------------------------------------------------------
class UserService:
    """User Service with essential business logic"""
    
    def __init__(self):
        self.update_schema = UpdateUserSchema()
        self.password_schema = ChangePasswordSchema()
    
    # =============================================================================
    # HIERARCHY PERMISSION HELPER
    # =============================================================================
    
    def check_hierarchy_permission(
        self, 
        current_user: 'TbUser', 
        target_user: 'TbUser', 
        action: str = 'manage'
    ) -> Tuple[bool, str]:
        """
        Check if current user has permission to perform action on target user
        based on simplified hierarchy rules.
        
        Args:
            current_user: User performing the action
            target_user: User being acted upon
            action: Type of action ('list', 'update', 'delete')
            
        Returns:
            Tuple of (has_permission, error_message)
            
        Hierarchy Rules:
        - superadmin: Can manage ALL users (full access)
        - staff: Can manage ALL users EXCEPT superadmin (platform manager)
        - admin: Can manage ONLY users they directly created (id_admin = their id)
        - user role: Special rules per action
        """
        user_role = current_user.role.lower()
        target_role = target_user.role.lower()
        locale = request.headers.get('Accept-Language', 'en')
        
        # Superadmin has full access to everyone
        if user_role == 'superadmin':
            return True, ""
        
        # Staff has full access EXCEPT to superadmin
        if user_role == 'staff':
            if target_role == 'superadmin':
                return False, get_message('hierarchy_staff_cannot_manage_superadmin', locale)
            return True, ""  # Can manage everyone else
        
        # User role has limited permissions
        if user_role == 'user':
            if action == 'list':
                return False, get_message('hierarchy_user_cannot_action', locale, action=action)
            elif action in ['update', 'delete']:
                # User can only act on themselves
                if current_user.id_user != target_user.id_user:
                    return False, get_message('hierarchy_user_action_self_only', locale, action=action)
                return True, ""
            else:
                return False, get_message('hierarchy_user_cannot_action', locale, action=action)
        
        # Admin - can manage only users they directly created OR themselves
        if user_role == 'admin':
            # Allow if admin is updating himself
            if current_user.id_user == target_user.id_user:
                return True, ""
            # Allow if target user was directly created by this admin
            elif target_user.id_admin == current_user.id_user:
                return True, ""
            else:
                return False, get_message('hierarchy_admin_action_created_only', locale, action=action)
        # Other roles (manager, etc.) - no permissions
        return False, get_message('hierarchy_role_action_denied', locale, user_role=user_role, action=action)
    
    # ------------------------------------------------------------------------
    # Create a new role
    # ------------------------------------------------------------------------
    def create(self, validated_data: Dict[str, Any], current_user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Create user in Auth0 and save temp data.
        
        Complete flow for user creation:
        1. Validate unique constraints (email)
        2. Validate license availability (for admin/superadmin roles)
        3. Create user in Auth0 via Management API
        4. Transfer licenses (if applicable)
        5. Save temp data for first login
        
        Args:
            validated_data: Validated user data from schema
            current_user_id: ID of authenticated user creating
            
        Returns:
            Tuple of (response_data, status_code)
        """
        try:
            from src.app.api.v1.services import auth0_service
            from src.app.api.v1.services.public.license_service import LicenseManager
            
            # Extract fields
            email = validated_data['email']
            password = validated_data['password']
            role = validated_data['role']
            language = validated_data.get('language', 'en')
            first_name = validated_data['first_name']
            last_name = validated_data['last_name']
            company_name = validated_data.get('company_name')
            number_licences = validated_data.get('number_licences', 0)
            premium_1 = validated_data.get('premium_licenses_1', 0)
            premium_2 = validated_data.get('premium_licenses_2', 0)
            phone = validated_data.get('phone')
            companies = validated_data.get('companies', [])
            
            locale = request.headers.get('Accept-Language', 'en')

            # Get current user for validation
            current_user = TbUser.findOne(id_user=current_user_id)
            if not current_user:
                return {
                    'error': 'Current user not found',
                    'message': get_message('creator_user_not_found', locale)
                }, 404
            
            # Check unique constraints in both tb_user and user_temp_data
            if TbUser.findOne(email=email):
                return {
                    'error': 'Email already exists',
                    'message': get_message('user_email_exists', locale, email=email)
                }, 409
            
            # Check if email exists in temp data (pending user creation)
            if UserTempData.findOne(email=email):
                return {
                    'error': 'Email already exists',
                    'message': get_message('user_email_processing', locale, email=email)
                }, 409
            
            # # LICENSE VALIDATION: Updated flow based on role hierarchy
            transferred_licenses = []
            creator_remaining_stats = None
            
            # Rule 1: If creating superadmin, no license should be allocated
            if role.lower() in ['super_admin', 'superadmin']:
                if number_licences > 0:
                    current_app.logger.warning(f"Cannot allocate licenses to superadmin role")
                # No license validation for superadmin
                current_app.logger.info(f"Creating superadmin - no license validation required")
            
            # Rule 2: If creating admin
            elif role.lower() == 'admin':
                current_user_role = current_user.role.lower()
                
                # Rule 2a: If superadmin or staff creates admin, no validation (unlimited licenses)
                if current_user_role in ['superadmin', 'staff']:
                    current_app.logger.info(f"{current_user_role.capitalize()} creating parent admin - no license validation required")
                    # Superadmin/Staff can allocate any number of licenses to parent admin
                
                # Rule 2b: If admin creates another admin, validate license availability
                elif current_user_role == 'admin':
                    if number_licences > 0:
                        # Validate if creator admin has enough licenses
                        is_valid, error_msg, stats = LicenseManager.validate_license_availability_for_admin(
                            current_user_id, 
                            number_licences
                        )
                        
                        if not is_valid:
                            current_app.logger.warning(f"License validation failed for {email}: {error_msg}")
                            return {
                                'error': 'Insufficient licenses',
                                'message': error_msg,
                                'license_stats': stats
                            }, 400
                        
                        current_app.logger.info(f"Admin creating sub-admin - License validation passed: {number_licences} licenses available for transfer")
                else:
                    # Other roles (user, manager, etc.) cannot create admins
                    return {
                        'error': 'Permission denied',
                        'message': get_message('role_cannot_create_admin', locale, role=current_user_role)
                    }, 403
            
            # # Rule 3: Non-admin roles cannot receive licenses
            elif number_licences > 0:
                current_app.logger.warning(f"Cannot allocate licenses to non-admin role: {role}")
                return {
                    'error': 'Invalid license allocation',
                    'message': get_message('license_allocation_admin_only', locale, role=role)
                }, 400
            
            # Normalize role for Auth0 (admin -> admin, superadmin -> superadmin)
            role_normalized = role.lower().replace('_', '')
            
            # Create user in Auth0
            try:
                auth0_user = auth0_service.create_auth0_user(
                    email=email,
                    password=password,
                    name=f"{first_name} {last_name}",
                    role=role_normalized,
                    language=language
                )
                auth0_user_id = auth0_user.get('user_id')
                current_app.logger.info(f"User created in Auth0: {auth0_user_id}")
                
                # NOTE: License transfer will happen in trigger after first login
                # when tb_user record is created with id_user
                
            except ValueError as e:
                # Auth0 specific errors (user exists, invalid data, etc.)
                error_msg = str(e)
                current_app.logger.error(f"Auth0 user creation failed: {error_msg}")
                
                # Determine status code based on error
                if 'already exists' in error_msg.lower() or 'user already exists' in error_msg.lower():
                    status_code = 409  # Conflict
                elif 'invalid' in error_msg.lower() or 'validation' in error_msg.lower():
                    status_code = 400  # Bad Request
                else:
                    status_code = 500  # Internal Server Error
                
                return {
                    'error': 'Auth0 user creation failed',
                    'message': error_msg
                }, status_code
            except Exception as e:
                current_app.logger.error(f"Unexpected error creating Auth0 user: {str(e)}")
                return {
                    'error': 'Failed to create user in Auth0',
                    'message': str(e)
                }, 500
            
            # Get creator's remaining license stats for response
            # Only calculate if admin created another admin (license validation was performed)
            if role.lower() == 'admin' and current_user.role.lower() == 'admin' and number_licences > 0:
                creator_remaining_stats = LicenseManager.calculate_license_stats(current_user_id)
            
            # Save temp data using model
            temp_data_dict = {
                'email': email,
                'name': first_name,
                'surname': last_name,
                'number_licences': number_licences,
                'premium_licenses_1': premium_1,
                'premium_licenses_2': premium_2,
                'company_name': company_name,
                'phone': phone,
                'language': language,
                'role': role,  # Save role for hierarchy filtering
                'id_user': current_user_id,
                'companies': companies if companies else None
            }
            
            temp_data, error = UserTempData.create_or_update(temp_data_dict)
            
            if error:
                current_app.logger.warning(f"Temp data save failed: {error}")
            else:
                current_app.logger.info(f"Temp data saved for {email}")
            
            # Prepare response
            response_data = {
                'message': get_message('user_created_success', locale),
                'data': {
                    'auth0_user_id': auth0_user_id,
                    'email': email,
                    'role': role,
                    'temp_data_saved': temp_data is not None,
                    'licenses_to_be_allocated': number_licences if number_licences > 0 else None
                }
            }
            
            # Add role-specific notes
            if role.lower() in ['super_admin', 'superadmin']:
                response_data['note'] = 'Superadmin role does not require licenses'
            elif role.lower() == 'admin' and number_licences > 0:
                if current_user.role.lower() in ['superadmin', 'staff']:
                    response_data['note'] = f'Parent admin will receive {number_licences} licenses upon first login (no validation applied for {current_user.role.lower()})'
                elif current_user.role.lower() == 'admin':
                    response_data['note'] = f'Sub-admin will receive {number_licences} licenses from your available licenses upon first login'
            
            # Add license stats if licenses were validated (admin creating another admin)
            if creator_remaining_stats:
                response_data['creator_license_stats'] = {
                    'total_licenses': creator_remaining_stats['total_licenses'],
                    'used_by_companies': creator_remaining_stats['used_by_companies'],
                    'available': creator_remaining_stats['available'] - number_licences,
                    'can_transfer': creator_remaining_stats['can_transfer'] - number_licences
                }
            
            return response_data, 201
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create user error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': 'Failed to create user',
                'message': str(e)
            }, 500
    
    # ------------------------------------------------------------------------
    # Get all records with hierarchy filtering
    # ------------------------------------------------------------------------
    def find(self, **filters) -> Tuple[Dict[str, Any], int]:
        """
        Get paginated list of users with filtering and simplified hierarchy support.
        Searches both TbUser and UserTempData tables.
        
        Hierarchy Rules:
        - superadmin: Sees ALL users in the system (no filter)
        - staff: Sees ALL users in the system (platform manager, same as superadmin)
        - admin: Sees ONLY users they directly created (id_admin = their id)
        - user role: Returns 403 error (not allowed to list users)
        """
        try:
            page = filters.get('page', 1)
            per_page = min(filters.get('per_page', 10), 100)
            search = filters.get('search', '')
            role_filter = filters.get('role', '')
            status_filter = filters.get('status', '')
            current_user_id = filters.get('current_user_id')
            
            # Build filter dict for model method
            model_filters = {}
            temp_filters = {}  # Separate filters for UserTempData
            
            if role_filter:
                # Support comma-separated roles: role=staff,admin,user
                if isinstance(role_filter, str) and ',' in role_filter:
                    parsed_roles = [r.strip().lower() for r in role_filter.split(',') if r.strip()]
                    if parsed_roles:
                        model_filters['role'] = parsed_roles
                        temp_filters['role'] = parsed_roles
                else:
                    model_filters['role'] = role_filter
                    temp_filters['role'] = role_filter
            if status_filter:
                model_filters['status'] = status_filter
                # Note: UserTempData doesn't have status field, so we don't filter by it
            
            # Apply hierarchy filtering based on role
            excluded_roles = []
            included_roles = []
            user_role = None
            
            if current_user_id:
                current_user = TbUser.findOne(id_user=current_user_id)
                
                if not current_user:
                    return {
                        'error': 'User not found',
                        'message': get_message('current_user_not_found', request.headers.get('Accept-Language', 'en'))
                    }, 404
                
                user_role = current_user.role.lower()
                if user_role == 'user':
                    return {
                        'error': 'Permission denied',
                        'message': get_message('hierarchy_user_cannot_action', request.headers.get('Accept-Language', 'en'), action='list')
                    }, 403

                # Superadmin: sees all users except itself
                if user_role == 'superadmin':
                    model_filters['exclude_id_user'] = current_user_id  # We'll filter out current user after fetch

                # Staff: sees only admin & user, exclude itself and any superadmin
                elif user_role == 'staff':
                    included_roles = ['admin', 'user']
                    model_filters['exclude_id_user'] = current_user_id  # will filter after fetch
                    model_filters['exclude_role'] = 'superadmin'  # will filter after fetch
                    # For temp users, filter by role
                    if not role_filter:  # Only set if not already filtered
                        temp_filters['role'] = ['admin', 'user']

                # Admin: can only see users they directly created
                elif user_role == 'admin':
                    model_filters['id_admin'] = current_user_id
                    temp_filters['id_user'] = current_user_id  # id_user in UserTempData is the creator
                    current_app.logger.info(f"Admin {current_user.email} (id={current_user_id}) listing their direct creations only")
            
            # =================================================================
            # QUERY TbUser TABLE
            # =================================================================
            users, tb_total, error = TbUser.find(
                page=1,  # Get all matching records first for merging
                per_page=1000,  # Large limit to get all users
                search=search if search else None,
                **{k: v for k, v in model_filters.items() if k not in ['exclude_id_user', 'exclude_role']}
            )
            
            if error:
                current_app.logger.error(f"List users failed: {error}")
                return {
                    'error': 'Failed to retrieve users',
                    'message': error
                }, 500

            # =================================================================
            # QUERY UserTempData TABLE
            # =================================================================
            temp_users, temp_total, temp_error = UserTempData.find(
                page=1,  # Get all matching records first for merging
                per_page=1000,  # Large limit to get all temp users
                search=search if search else None,
                **temp_filters
            )
            
            if temp_error:
                current_app.logger.warning(f"List temp users failed: {temp_error}")
                # Continue with just TbUser results, don't fail the entire request
                temp_users = []
                temp_total = 0

            # =================================================================
            # MERGE AND FILTER RESULTS
            # =================================================================
            users_data = []
            
            # Process TbUser records
            for user in users:
                if current_user_id:
                    # Exclude itself for superadmin/staff
                    if hasattr(user, "id_user") and user.id_user == current_user_id:
                        continue
                    # For staff: Exclude any superadmin and only include admin/user
                    if user_role == 'staff':
                        if hasattr(user, "role") and user.role and user.role.lower() == 'superadmin':
                            continue
                        if hasattr(user, "role") and user.role.lower() not in included_roles:
                            continue
                
                # Get user dict
                user_dict = user.to_dict()
                
                # Add number_licences for admin/superadmin users
                if user.role and user.role.lower() in ['admin']:
                    try:
                        from src.app.database.models.public.licence_admin import LicenceAdmin
                        
                        # Count total licenses assigned to this user
                        total_licenses = db.session.query(LicenceAdmin).filter(
                            LicenceAdmin.id_user == user.id_user
                        ).count()
                        
                        user_dict['number_licences'] = total_licenses
                        
                    except Exception as e:
                        current_app.logger.warning(f"Failed to count licenses for user {user.email}: {str(e)}")
                        user_dict['number_licences'] = 0
                else:
                    # Non-admin users don't have licenses
                    user_dict['number_licences'] = 0
                
                users_data.append(user_dict)
            
            # Process UserTempData records
            for temp_user in temp_users:
                # For staff: Exclude any superadmin and only include admin/user
                if user_role == 'staff':
                    if hasattr(temp_user, "role") and temp_user.role and temp_user.role.lower() == 'superadmin':
                        continue
                    if hasattr(temp_user, "role") and temp_user.role and temp_user.role.lower() not in included_roles:
                        continue
                
                # Get temp user dict
                temp_user_dict = temp_user.to_dict()                
                users_data.append(temp_user_dict)
            
            # Sort combined results by created_at (latest first)
            # Both models now provide ISO format or datetime objects, string sort works for ISO
            users_data.sort(key=lambda x: x.get('created_at') or '', reverse=True)
            
            # Apply pagination to merged results
            combined_total = len(users_data)

            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_users = users_data[start_idx:end_idx]
            
            total_pages = (combined_total + per_page - 1) // per_page if combined_total > 0 else 0
            
            return {
                'data': {
                    'users': paginated_users,
                    'pagination': {
                        'total': combined_total,
                        'page': page,
                        'per_page': per_page,
                        'total_pages': total_pages,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    },
                },
                'success': True,
                'message': get_message('users_fetched_success', request.headers.get('Accept-Language', 'en'))
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"List users error: {str(e)}")
            return {
                'error': 'Failed to get users list',
                'message': str(e)
            }, 500
    
    # -----------------------------------------------------------------------------
    # USER DETAILS
    # -----------------------------------------------------------------------------
    def findOne(self, user_id: int, current_user_id: int, email_id: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Get user details by ID with license count for admins.
        If user not found in TbUser, searches UserTempData by email_id.
        
        Args:
            user_id: ID of the user to find (for TbUser)
            current_user_id: ID of the requesting user
            email_id: Optional email to search in UserTempData if user not found in TbUser
        
        Returns:
            - User details
            - number_licences: Total licenses assigned (only for admin/superadmin roles)
        """
        try:  
            if email_id:
                temp_user_result = UserTempData.findOne(email=email_id)
                locale = request.headers.get('Accept-Language', 'en')
                if not temp_user_result:
                    return {
                        'success': False,
                        'message': get_message('user_not_found', locale)
                    }, 404
                if temp_user_result:
                    # Handle tuple result from findOne with select
                    if hasattr(temp_user_result, 'to_dict'):
                        temp_user = temp_user_result
                    else:
                        # It's a tuple/Row, get the first element
                        temp_user = temp_user_result[0] if temp_user_result else None
                
                    if temp_user:
                        # Return basic temp user data without license/company calculations
                        user_data = temp_user.to_dict()
                        user_data['number_licences'] = temp_user.number_licences or 0
                        
                        current_app.logger.info(f"Temp user found: {email_id}")
                            
                        return {
                                'message': get_message('user_details_success', locale),
                                'data': {'user': user_data},
                                'success': True
                            }, 200
            
            target_user = TbUser.findOne(id_user=user_id)  
           
            locale = request.headers.get('Accept-Language', 'en')
            if not target_user:
                # User not found in either table
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('user_does_not_exist', locale)
                }, 404
            
            # Get user dict from TbUser
            user_data = target_user.to_dict()
            
            # Calculate number_licences for admin/superadmin users
            if target_user.role and target_user.role.lower() in ['admin', 'superadmin']:
                try:
                    from src.app.database.models.public.licence_admin import LicenceAdmin
                    
                    # Count total licenses assigned to this user
                    total_licenses = db.session.query(LicenceAdmin).filter(
                        LicenceAdmin.id_user == target_user.id_user
                    ).count()
                    
                    user_data['number_licences'] = total_licenses
                    current_app.logger.info(f"User {target_user.email} has {total_licenses} licenses")
                    
                except Exception as e:
                    current_app.logger.warning(f"Failed to count licenses for user {target_user.email}: {str(e)}")
                    user_data['number_licences'] = 0
            else:
                # Non-admin users don't have licenses
                user_data['number_licences'] = 0
            
            # Add companies array ONLY for USER role
            if target_user.role and target_user.role.lower() == 'user':
                try:
                    user_company_mappings = TbUserCompany.query.filter_by(id_user=user_id).all()
                    
                    if user_company_mappings:
                        company_ids = [mapping.id_company for mapping in user_company_mappings]
                        
                        # Get company details
                        companies = KbaiCompany.query.filter(
                            KbaiCompany.id_company.in_(company_ids),
                            KbaiCompany.is_deleted == False
                        ).order_by(KbaiCompany.company_name.asc()).all()
                        
                        user_data['companies'] = [
                            {
                                'id_company': company.id_company,
                                'company_name': company.company_name
                            }
                            for company in companies
                        ]
                    else:
                        user_data['companies'] = []
                        
                    current_app.logger.info(f"User {target_user.email} has {len(user_data['companies'])} companies assigned")
                    
                except Exception as e:
                    current_app.logger.warning(f"Failed to get companies for user {target_user.email}: {str(e)}")
                    user_data['companies'] = []
            
            return {
                'message': 'User details retrieved successfully',
                'data': {'user': user_data},
                'success': True
            }, 200
            
        except Exception as e:
            current_app.logger.error(f"Get user detail error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'success': False,
                'error': 'Failed to get user details',
                'message': str(e)
            }, 500
    
    # -----------------------------------------------------------------------------
    # USER UPDATE
    # -----------------------------------------------------------------------------
    def update(self, user_id: int, update_data: Dict[str, Any], current_user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Update user information with simplified role-based hierarchy validation
        
        Hierarchy Rules:
        - superadmin: Can update ALL users
        - staff: Can update ALL users except superadmin
        - admin: Can update ONLY users they directly created
        - user role: Can only update themselves
        
        License Update Logic:
        - If updating admin's licenses:
          - Same count: no change
          - Decreased count: delete excess licenses
          - Increased count: create new licenses (with parent validation if needed)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Get current user
            current_user = TbUser.findOne(id_user=current_user_id)
            if not current_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('current_user_not_found', locale)
                }, 404
            
            # Get target user
            target_user = TbUser.findOne(id_user=user_id)
            if not target_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('user_does_not_exist', locale)
                }, 404
            
            # Check hierarchy permissions using helper function
            has_permission, error_msg = self.check_hierarchy_permission(
                current_user=current_user,
                target_user=target_user,
                action='update'
            )
            
            if not has_permission:
                return {
                    'error': 'Permission denied',
                    'message': error_msg
                }, 403
            
            # Validate request data
            try:
                validated_data = self.update_schema.load(update_data)
            except ValidationError as err:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'message': err.messages
                }, 400
            
            # ===================================================================
            # LICENSE UPDATE LOGIC - Call License Service
            # ===================================================================
            license_update_info = None
            
            # Check if updating licenses for an admin user
            if 'number_licences' in validated_data:
                from src.app.api.v1.services.public.license_service import LicenseManager
                
                new_license_count = validated_data['number_licences']
                
                # Call license service to handle update logic
                success, error_msg, license_info = LicenseManager.update_user_licenses(
                    target_user=target_user,
                    current_user=current_user,
                    new_license_count=new_license_count
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': 'License update failed',
                        'message': error_msg
                    }, 400
                
                license_update_info = license_info
                
                # Remove number_licences from validated_data as it's not a direct field on TbUser
                del validated_data['number_licences']
            
            # ===================================================================
            # COMPANY MAPPING UPDATE - Only for USER role
            # ===================================================================
            company_update_info = None
            
            if 'companies' in validated_data and target_user.role.lower() == 'user':
                new_company_ids = validated_data['companies']
                
                # Call tb_user_company_service to handle mapping updates
                from src.app.api.v1.services.public.tb_user_company_service import tb_user_company_service
                
                success, error_msg, update_info = tb_user_company_service.update_user_companies(
                    user_id=user_id,
                    new_company_ids=new_company_ids
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': 'Company mapping update failed',
                        'message': error_msg
                    }, 500
                
                company_update_info = update_info
                
                # Remove companies from validated_data as it's handled
                del validated_data['companies']
            
            # Update using model method (for other fields)
            if validated_data:  # Only update if there are fields to update
                success, error = target_user.update(validated_data)
                
                if not success:
                    return {
                        'success': False,
                        'error': 'Update failed',
                        'message': error
                    }, 500
            
            current_app.logger.info(f"User updated: {target_user.email} by {current_user.email}")
            
            # Prepare response
            response_data = {
                'message': get_message('user_updated_success', locale),
                'data': target_user.to_dict(),
                'success': True
            }
            
            # Add license update info if applicable
            if license_update_info:
                response_data['license_update'] = license_update_info
            
            # Add company update info if applicable
            if company_update_info:
                response_data['company_update'] = company_update_info
            
            return response_data, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Update user error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to update user',
                'message': str(e)
            }, 500
    
    # -----------------------------------------------------------------------------
    # USER DELETION
    # ----------------------------------------------------------------------------
    def delete(self, user_id: int, current_user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Delete user (soft delete) with simplified role-based hierarchy validation
        
        Hierarchy Rules:
        - superadmin: Can delete ALL users (except themselves)
        - staff: Can delete ALL users except superadmin
        - admin: Can delete ONLY users they directly created
        - user role: Cannot delete anyone (403 error)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Get current user
            current_user = TbUser.findOne(id_user=current_user_id)
            if not current_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('current_user_not_found', locale)
                }, 404
            
            # Get target user
            target_user = TbUser.findOne(id_user=user_id)
            if not target_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('user_does_not_exist', locale)
                }, 404
            
            # Prevent self-deletion
            if current_user_id == user_id:
                return {
                    'error': get_message('self_deletion_not_allowed', locale),
                    'message': get_message('cannot_delete_own_account', locale)
                }, 403
            
            # Check hierarchy permissions using helper function
            has_permission, error_msg = self.check_hierarchy_permission(
                current_user=current_user,
                target_user=target_user,
                action='delete'
            )
            
            if not has_permission:
                return {
                    'error': 'Permission denied',
                    'message': error_msg
                }, 403
            
            # If already inactive, treat as idempotent success
            if target_user.status == 'DELETE':
                current_app.logger.info(f"User already inactive (idempotent delete): {target_user.email}")
                return {
                    'success': True,
                    'message': get_message('user_deleted_success', locale),
                    'data': {
                        'id_user': target_user.id_user,
                        'status': target_user.status
                    }
                }, 200

            # Cache primitives before commit to avoid attribute reload edge cases
            cached_id = target_user.id_user
            cached_email = target_user.email

            # Soft delete using model method
            success, error = target_user.delete()
            
            if not success:
                return {
                    'success': False,
                    'error': 'Delete failed',
                    'message': error
                }, 500
            
            current_app.logger.info(f"User deleted: {cached_email}")
            
            return {
                'success': True,
                'message': get_message('user_deleted_success', locale),
                'data': {
                    'id_user': cached_id,
                    'status': 'DELETE'
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Delete user error: {str(e)}")
            return {
                'error': 'Failed to delete user',
                'message': str(e)
            }, 500
    
    # -----------------------------------------------------------------------------
    # HARD DELETE USER
    # ----------------------------------------------------------------------------
    def hard_delete(self, user_id: int, current_user_id: int) -> Tuple[Dict[str, Any], int]:
        """
        Hard delete user - completely remove user and all related data from database
        
        Hierarchy Rules:
        - superadmin: Can hard delete ALL users (except themselves)
        - staff: Can hard delete ALL users except superadmin
        - admin: Can hard delete ONLY users they directly created
        - user role: Cannot delete anyone (403 error)
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Get current user
            current_user = TbUser.findOne(id_user=current_user_id)
            if not current_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('current_user_not_found', locale)
                }, 404
            
            # Get target user
            target_user = TbUser.findOne(id_user=user_id)
            if not target_user:
                return {
                    'success': False,
                    'error': 'User not found',
                    'message': get_message('user_does_not_exist', locale)
                }, 404
            
            # Prevent self-deletion
            if current_user_id == user_id:
                return {
                    'success': False,
                    'error': get_message('self_deletion_not_allowed', locale),
                    'message': get_message('cannot_delete_yourself', locale)
                }, 403
            
            # Check permissions (same as soft delete)
            user_role = current_user.role.lower()
            target_role = target_user.role.lower()
            
            # Superadmin can delete anyone except themselves
            if user_role == 'superadmin':
                pass  # Allow deletion
            # Staff can delete anyone except superadmin
            elif user_role == 'staff':
                if target_role == 'superadmin':
                    return {
                        'success': False,
                        'error': 'Permission denied',
                        'message': get_message('hierarchy_staff_cannot_delete_superadmin', locale)
                    }, 403
            # Admin can only delete users they created
            elif user_role == 'admin':
                if target_user.id_admin != current_user_id:
                    return {
                        'success': False,
                        'error': 'Permission denied',
                        'message': get_message('hierarchy_admin_delete_created_only', locale)
                    }, 403
            # User role cannot delete anyone
            else:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'message': get_message('hierarchy_user_cannot_delete_others', locale)
                }, 403
            
            # Hard delete user and all related data
            try:
                # Cache primitive fields before ORM deletion to avoid accessing a deleted instance
                deleted_user_id = target_user.id_user
                deleted_user_email = target_user.email

                # Delete user temp data
                UserTempData.query.filter_by(id_user=user_id).delete()
                
                # Delete user-company mappings
                TbUserCompany.query.filter_by(id_user=user_id).delete()
                
                # Delete license admin mappings
                LicenceAdmin.query.filter_by(id_user=user_id).delete()
                
                # Delete OTP records (using email instead of id_user)
                TbOtp.query.filter_by(email=deleted_user_email).delete()
                
                # Finally delete the user
                db.session.delete(target_user)
                db.session.commit()
                
                current_app.logger.info(f"User hard deleted: {deleted_user_email} (ID: {deleted_user_id})")
                
                return {
                    'success': True,
                    'message': get_message('user_permanently_deleted_success', locale),
                    'data': {
                        'deleted_user_id': deleted_user_id,
                        'deleted_user_email': deleted_user_email
                    }
                }, 200
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Hard delete user error: {str(e)}")
                return {
                    'success': False,
                    'error': 'Failed to delete user',
                    'message': str(e)
                }, 500
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Hard delete user error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to delete user',
                'message': str(e)
            }, 500
    
    # =============================================================================
    # PASSWORD MANAGEMENT
    # ============================================================================= 
    def change_user_password(self, user_id: int, password_data: Dict[str, Any], current_user_id: int) -> Tuple[Dict[str, Any], int]:
        """Change user password"""
        try:
            locale = request.headers.get('Accept-Language', 'en')
            target_user = TbUser.findOne(id_user=user_id)
            
            if not target_user:
                return {
                    'error': 'User not found',
                    'message': get_message('user_does_not_exist', locale)
                }, 404
            
            # Validate request data
            try:
                validated_data = self.password_schema.load(password_data)
            except ValidationError as err:
                return {
                    'error': 'Validation failed',
                    'message': err.messages
                }, 400
            
            # Update password using model method
            success, error = target_user.update({'password': validated_data['new_password']})
            
            if not success:
                return {
                    'error': get_message('password_change_failed_msg', locale),
                    'message': error
                }, 500
            
            current_app.logger.info(f"Password changed for user: {target_user.email}")
            
            return {
                'message': get_message('password_changed_success', locale),
                'success': True
            }, 200
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Change password error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'error': 'Failed to change password',
                'message': str(e)
            }, 500


# Create service instance
user_service = UserService()
