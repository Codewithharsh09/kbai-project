"""
License Management Service
Handles license allocation, validation, and transfer logic
"""
from sqlalchemy import and_, func
from src.extensions import db
from src.app.database.models.public.licence_admin import LicenceAdmin
from src.app.database.models.public.tb_licences import TbLicences
from src.app.database.models.kbai.kbai_companies import KbaiCompany
from src.app.database.models.public.tb_user import TbUser
from typing import Dict, Tuple, List, Optional
from src.app.database.models.public.tb_licences import TbLicences
from datetime import date, datetime
import uuid
from flask import request
from src.common.localization import get_message


class LicenseManager:
    """Centralized license management for validation and transfers"""
    
    @staticmethod
    def calculate_license_stats(user_id: int) -> Dict:
        """
        Calculate comprehensive license statistics for a user
        
        Args:
            user_id: User ID to calculate stats for
            
        Returns:
            Dictionary with license statistics
        """
        try:
            # Get total licenses owned by user
            # Use ORM count() to ensure compatibility with active test transactions
            total_licenses = db.session.query(LicenceAdmin)\
                .filter(LicenceAdmin.id_user == user_id)\
                .count()
            
            # Get user's license IDs
            user_license_ids = db.session.query(LicenceAdmin.id_licence)\
                .filter(LicenceAdmin.id_user == user_id)\
                .all()
            user_license_ids = [lid[0] for lid in user_license_ids]
            
            # Count companies created using user's licenses
            used_by_companies = 0
            if user_license_ids:
                used_by_companies = db.session.query(KbaiCompany)\
                    .filter(
                        and_(
                            KbaiCompany.id_licence.in_(user_license_ids),
                            KbaiCompany.is_deleted == False
                        )
                    )\
                    .count()
            
            # Calculate available licenses
            # NOTE: No need to subtract given_to_subadmins because transferred licenses
            # are already NOT in this user's licence_admin records (ownership transferred)
            available = total_licenses - used_by_companies
            
            # Calculate transferable licenses
            can_transfer = available
            reserved_reason = None
            
            return {
                'total_licenses': total_licenses,
                'used_by_companies': used_by_companies,
                'available': available,
                'can_transfer': can_transfer,
                'reserved_reason': reserved_reason,
                'has_company': used_by_companies > 0
            }
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'total_licenses': 0,
                'used_by_companies': 0,
                'available': 0,
                'can_transfer': 0,
                'reserved_reason': get_message('error_calculating_stats', locale, error=str(e)),
                'has_company': False,
                'error': str(e)
            }
    
    @staticmethod
    def validate_license_availability_for_admin(creator_id: int, requested_licenses: int) -> Tuple[bool, Optional[str], Dict]:
        """
        Validate if creator has enough licenses to give to a new admin
        
        Args:
            creator_id: User creating the new admin
            requested_licenses: Number of licenses requested for new admin
            
        Returns:
            Tuple of (is_valid, error_message, stats_dict)
        """
        stats = LicenseManager.calculate_license_stats(creator_id)
        locale = request.headers.get('Accept-Language', 'en')
        
        # Check if there's an error in stats calculation
        if 'error' in stats:
            return False, get_message('unable_validate_licenses', locale, error=stats['error']), stats
        
        # Check if user has any licenses at all
        if stats['total_licenses'] == 0:
            return False, get_message('no_licenses_to_allocate', locale), stats
        
        # Check if requested licenses exceed what can be transferred
        if requested_licenses > stats['can_transfer']:
            if stats['reserved_reason']:
                error_msg = get_message('allocate_reserved_limit', locale, requested=requested_licenses, reason=stats['reserved_reason'], max=stats['can_transfer'])
            else:
                error_msg = get_message('allocate_transfer_limit', locale, requested=requested_licenses, max=stats['can_transfer'])
            
            return False, error_msg, stats
        
        # Validation passed
        return True, None, stats
    
    @staticmethod
    def validate_license_availability_for_company(creator_id: int) -> Tuple[bool, Optional[str], Dict]:
        """
        Validate if user has an available license to create a company
        
        Args:
            creator_id: User creating the company
            
        Returns:
            Tuple of (is_valid, error_message, stats_dict)
        """
        stats = LicenseManager.calculate_license_stats(creator_id)
        locale = request.headers.get('Accept-Language', 'en')
        
        # Check if there's an error in stats calculation
        if 'error' in stats:
            return False, get_message('unable_validate_licenses', locale, error=stats['error']), stats
        
        # Check if user has any available licenses
        if stats['available'] == 0:
            error_msg = get_message('no_licenses_create_company', locale)
            if stats['total_licenses'] == 0:
                error_msg += get_message('no_licenses_owned', locale)
            else:
                error_msg += get_message('all_licenses_in_use', locale, count=stats['total_licenses'])
            
            return False, error_msg, stats
        
        # Validation passed
        return True, None, stats
    
    @staticmethod
    def create_competitor_licence():

        licence = TbLicences(
            licence_token=f"COMP-{uuid.uuid4().hex[:16]}",
            expiry_date=date(2099, 12, 31),
            type='COMPETITOR',
            time=datetime.utcnow()
        )

        db.session.add(licence)
        db.session.flush()  # IMPORTANT: get id without commit

        return licence.id_licence

    @staticmethod
    def get_available_licenses_for_transfer(user_id: int, count: int) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Get specific number of available licenses that can be transferred
        
        Args:
            user_id: User ID to get licenses from
            count: Number of licenses to retrieve
            
        Returns:
            Tuple of (license_list, error_message)
            license_list contains dicts with id_licence and licence_code
        """
        try:
            locale = request.headers.get('Accept-Language', 'en')
            # Get all license IDs owned by user
            user_licenses = db.session.query(
                LicenceAdmin.id_licence,
                LicenceAdmin.licence_code
            ).filter(LicenceAdmin.id_user == user_id).all()
            
            if not user_licenses:
                return None, get_message('no_licenses_found_user', locale)
            
            user_license_ids = [lic[0] for lic in user_licenses]
            
            # Get licenses that are NOT used by companies
            used_license_ids = db.session.query(KbaiCompany.id_licence)\
                .filter(
                    and_(
                        KbaiCompany.id_licence.in_(user_license_ids),
                        KbaiCompany.is_deleted == False
                    )
                )\
                .all()
            used_license_ids = [lid[0] for lid in used_license_ids]
            
            # Filter out used licenses
            available_licenses = [
                {'id_licence': lic[0], 'licence_code': lic[1]}
                for lic in user_licenses
                if lic[0] not in used_license_ids
            ]
            
            # Check if we have enough available licenses
            if len(available_licenses) < count:
                return None, get_message('insufficient_licenses_available', locale, available=len(available_licenses), requested=count)
            
            # Return requested number of licenses
            return available_licenses[:count], None
            
        except Exception as e:
            locale = request.headers.get('Accept-Language', 'en')
            return None, get_message('error_retrieving_licenses', locale, error=str(e))
    
    @staticmethod
    def transfer_licenses(from_user_id: int, to_user_id: int, count: int) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """
        Transfer licenses from one user to another
        
        Args:
            from_user_id: User giving licenses
            to_user_id: User receiving licenses
            count: Number of licenses to transfer
            
        Returns:
            Tuple of (success, error_message, transferred_license_codes)
        """
        try:
            # Get available licenses
            available_licenses, error = LicenseManager.get_available_licenses_for_transfer(from_user_id, count)
            
            if error:
                return False, error, None
            
            transferred_codes = []
            
            # Transfer each license
            for license_info in available_licenses:
                # Remove from old user
                db.session.query(LicenceAdmin)\
                    .filter(
                        and_(
                            LicenceAdmin.id_licence == license_info['id_licence'],
                            LicenceAdmin.id_user == from_user_id
                        )
                    )\
                    .delete()
                
                # Add to new user
                new_assignment = LicenceAdmin(
                    id_licence=license_info['id_licence'],
                    id_user=to_user_id,
                    licence_code=license_info['licence_code']
                )
                db.session.add(new_assignment)
                
                transferred_codes.append(license_info['licence_code'])
            
            db.session.commit()
            
            return True, None, transferred_codes
            
        except Exception as e:
            db.session.rollback()
            locale = request.headers.get('Accept-Language', 'en')
            return False, get_message('error_transferring_licenses', locale, error=str(e)), None
    
    @staticmethod
    def get_license_hierarchy(user_id: int, depth: int = 2) -> Dict:
        """
        Get hierarchical view of license distribution
        
        Args:
            user_id: Root user ID
            depth: How many levels deep to traverse
            
        Returns:
            Dictionary with license hierarchy
        """
        try:
            stats = LicenseManager.calculate_license_stats(user_id)
            
            # Get user info
            user = TbUser.query.filter_by(id_user=user_id).first()
            if not user:
                return {}
            
            result = {
                'user_id': user_id,
                'email': user.email,
                'name': f"{user.name or ''} {user.surname or ''}".strip(),
                'role': user.role,
                'stats': stats,
                'companies': [],
                'sub_admins': []
            }
            
            # Get companies created with user's licenses
            user_license_ids = db.session.query(LicenceAdmin.id_licence)\
                .filter(LicenceAdmin.id_user == user_id)\
                .all()
            user_license_ids = [lid[0] for lid in user_license_ids]
            
            if user_license_ids:
                companies = KbaiCompany.query.filter(
                    and_(
                        KbaiCompany.id_licence.in_(user_license_ids),
                        KbaiCompany.is_deleted == False
                    )
                ).all()
                
                result['companies'] = [
                    {
                        'id_company': c.id_company,
                        'company_name': c.company_name,
                        'id_licence': c.id_licence
                    }
                    for c in companies
                ]
            
            # Get sub-admins (if depth allows)
            if depth > 0:
                sub_admins = TbUser.query.filter(
                    and_(
                        TbUser.id_admin == user_id,
                        TbUser.id_user != user_id
                    )
                ).all()
                
                for sub_admin in sub_admins:
                    sub_admin_data = LicenseManager.get_license_hierarchy(sub_admin.id_user, depth - 1)
                    result['sub_admins'].append(sub_admin_data)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def update_user_licenses(
        target_user: 'TbUser',
        current_user: 'TbUser', 
        new_license_count: int
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Update licenses for a user (admin only)
        
        Handles:
        - License increase (with validation)
        - License decrease (delete excess)
        - No change
        
        Args:
            target_user: User whose licenses are being updated
            current_user: User performing the update
            new_license_count: New license count to set
            
        Returns:
            Tuple of (success, error_message, license_update_info)
        """
        from flask import current_app
        import uuid
        
        try:
            # Only admin users can have licenses
            if target_user.role.lower() != 'admin':
                return True, None, None  # Skip license update for non-admin
            
            # Get current license count
            current_license_count = db.session.query(LicenceAdmin).filter(
                LicenceAdmin.id_user == target_user.id_user
            ).count()
            
            current_app.logger.info(
                f"License update requested: {current_license_count} → {new_license_count} "
                f"for user {target_user.email}"
            )
            
            # Calculate difference
            license_difference = new_license_count - current_license_count
            
            # =================================================================
            # CASE 1: No Change
            # =================================================================
            if license_difference == 0:
                current_app.logger.info(f"No change in license count for user {target_user.email}")
                return True, None, {
                    'action': 'no_change',
                    'current_count': current_license_count,
                    'new_count': new_license_count
                }
            
            # =================================================================
            # CASE 2: DECREASE - Delete or Transfer back excess licenses
            # =================================================================
            elif license_difference < 0:
                licenses_to_remove = abs(license_difference)
                current_app.logger.info(
                    f"Removing {licenses_to_remove} licenses for user {target_user.email}"
                )
                
                # First, check how many companies the target admin has created
                target_license_ids = db.session.query(LicenceAdmin.id_licence)\
                    .filter(LicenceAdmin.id_user == target_user.id_user)\
                    .all()
                target_license_ids = [lid[0] for lid in target_license_ids]
                
                companies_count = 0
                if target_license_ids:
                    companies_count = db.session.query(func.count(KbaiCompany.id_company))\
                        .filter(
                            and_(
                                KbaiCompany.id_licence.in_(target_license_ids),
                                KbaiCompany.is_deleted == False
                            )
                        )\
                        .scalar() or 0
                
                current_app.logger.info(
                    f"Target admin {target_user.email} has created {companies_count} companies"
                )
                
                # Check if target admin has enough UNUSED licenses to remove
                unused_licenses_count = current_license_count - companies_count
                
                if unused_licenses_count < licenses_to_remove:
                    locale = request.headers.get('Accept-Language', 'en')
                    return False, get_message('cannot_decrease_licenses_used', locale, amount=licenses_to_remove, total=current_license_count, used=companies_count, unused=unused_licenses_count), None
                
                # Get available (unused) licenses to remove
                available_licenses, error = LicenseManager.get_available_licenses_for_transfer(
                    target_user.id_user, 
                    licenses_to_remove
                )
                
                if error:
                    locale = request.headers.get('Accept-Language', 'en')
                    return False, get_message('unable_remove_licenses', locale, amount=licenses_to_remove, error=error), None
                
                # Determine action based on WHO is updating and target admin's parent
                current_user_role = current_user.role.lower()
                parent_admin_id = target_user.id_admin
                
                # ---------------------------------------------------------------
                # CASE 2A: Target admin HAS a parent (id_admin is NOT NULL)
                # ---------------------------------------------------------------
                if parent_admin_id is not None:
                    # Get parent admin details
                    parent_admin = TbUser.query.filter_by(id_user=parent_admin_id).first()
                    
                    if not parent_admin:
                        locale = request.headers.get('Accept-Language', 'en')
                        return False, get_message('parent_admin_not_found', locale), None
                    
                    parent_role = parent_admin.role.lower()
                    
                    # Check if parent is ADMIN (not superadmin/staff)
                    if parent_role == 'admin':
                        # Transfer licenses BACK to parent admin
                        current_app.logger.info(
                            f"Target admin's parent (id={parent_admin_id}) is ADMIN. "
                            f"Transferring {licenses_to_remove} licenses back to parent."
                        )
                        
                        transferred_codes = []
                        for license_info in available_licenses:
                            # Update licence_admin to change ownership back to parent
                            db.session.query(LicenceAdmin).filter(
                                and_(
                                    LicenceAdmin.id_licence == license_info['id_licence'],
                                    LicenceAdmin.id_user == target_user.id_user
                                )
                            ).update({'id_user': parent_admin_id})
                            
                            transferred_codes.append(license_info['licence_code'])
                        
                        db.session.commit()
                        
                        current_app.logger.info(
                            f"Successfully transferred {licenses_to_remove} licenses back to "
                            f"parent admin (id={parent_admin_id})"
                        )
                        
                        return True, None, {
                            'action': 'transferred_back_to_parent',
                            'count': licenses_to_remove,
                            'license_codes': transferred_codes,
                            'previous_count': current_license_count,
                            'new_count': new_license_count,
                            'parent_admin_id': parent_admin_id,
                            'parent_email': parent_admin.email,
                            'note': f'Licenses transferred back to parent admin {parent_admin.email}'
                        }
                    
                    elif parent_role in ['superadmin', 'staff']:
                        # Parent is SUPERADMIN/STAFF → DELETE licenses (they have unlimited)
                        current_app.logger.info(
                            f"Target admin's parent (id={parent_admin_id}) is {parent_role.upper()}. "
                            f"Deleting {licenses_to_remove} licenses (parent has unlimited)."
                        )
                        
                        deleted_codes = []
                        for license_info in available_licenses:
                            # Delete from licence_admin
                            db.session.query(LicenceAdmin).filter(
                                and_(
                                    LicenceAdmin.id_licence == license_info['id_licence'],
                                    LicenceAdmin.id_user == target_user.id_user
                                )
                            ).delete()
                            
                            # Also delete from tb_licences
                            db.session.query(TbLicences).filter(
                                TbLicences.id_licence == license_info['id_licence']
                            ).delete()
                            
                            deleted_codes.append(license_info['licence_code'])
                        
                        db.session.commit()
                        
                        current_app.logger.info(
                            f"Successfully deleted {licenses_to_remove} licenses "
                            f"(parent is {parent_role} with unlimited licenses)"
                        )
                        
                        return True, None, {
                            'action': 'deleted_parent_unlimited',
                            'count': licenses_to_remove,
                            'license_codes': deleted_codes,
                            'previous_count': current_license_count,
                            'new_count': new_license_count,
                            'parent_admin_id': parent_admin_id,
                            'parent_role': parent_role,
                            'note': f'Licenses deleted because parent {parent_role} has unlimited licenses'
                        }
                
                # ---------------------------------------------------------------
                # CASE 2B: Target admin is PARENT (id_admin is NULL)
                # ---------------------------------------------------------------
                else:
                    # No parent → DELETE licenses
                    current_app.logger.info(
                        f"Target admin {target_user.email} is a parent admin (id_admin=NULL). "
                        f"Deleting {licenses_to_remove} licenses."
                    )
                    
                    deleted_codes = []
                    for license_info in available_licenses:
                        # Delete from licence_admin
                        db.session.query(LicenceAdmin).filter(
                            and_(
                                LicenceAdmin.id_licence == license_info['id_licence'],
                                LicenceAdmin.id_user == target_user.id_user
                            )
                        ).delete()
                        
                        # Also delete from tb_licences
                        db.session.query(TbLicences).filter(
                            TbLicences.id_licence == license_info['id_licence']
                        ).delete()
                        
                        deleted_codes.append(license_info['licence_code'])
                    
                    db.session.commit()
                    
                    current_app.logger.info(
                        f"Successfully deleted {licenses_to_remove} licenses for parent admin"
                    )
                    
                    return True, None, {
                        'action': 'deleted_parent_admin',
                        'count': licenses_to_remove,
                        'license_codes': deleted_codes,
                        'previous_count': current_license_count,
                        'new_count': new_license_count,
                        'note': 'Parent admin - licenses deleted'
                    }
            
            # =================================================================
            # CASE 3: INCREASE - Create/Transfer new licenses
            # =================================================================
            else:
                licenses_to_create = license_difference
                current_app.logger.info(
                    f"Creating {licenses_to_create} new licenses for user {target_user.email}"
                )
                
                current_user_role = current_user.role.lower()
                
                # -------------------------------------------------------------
                # Rule 1: Superadmin or Staff updating
                # -------------------------------------------------------------
                if current_user_role in ['superadmin', 'staff']:
                    
                    # Check if target admin has a parent (id_admin is not null)
                    if target_user.id_admin is not None:
                        parent_admin_id = target_user.id_admin
                        
                        # Get parent admin details
                        parent_admin = TbUser.query.filter_by(id_user=parent_admin_id).first()
                        
                        if not parent_admin:
                            locale = request.headers.get('Accept-Language', 'en')
                            return False, get_message('parent_admin_not_found', locale), None
                        
                        parent_role = parent_admin.role.lower()
                        
                        # Check if parent is superadmin or staff - they have unlimited licenses
                        if parent_role in ['superadmin', 'staff']:
                            current_app.logger.info(
                                f"Parent admin (id={parent_admin_id}) is {parent_role}. "
                                f"Creating {licenses_to_create} new licenses without validation."
                            )
                            
                            # Create new licenses directly (parent has unlimited)
                            created_codes = []
                            for i in range(licenses_to_create):
                                license_code = f"LIC-{uuid.uuid4().hex[:12].upper()}"
                                
                                new_license = TbLicences(licence_token=license_code)
                                db.session.add(new_license)
                                db.session.flush()  # Get id_licence
                                
                                # Assign to target user
                                license_assignment = LicenceAdmin(
                                    id_licence=new_license.id_licence,
                                    id_user=target_user.id_user,
                                    licence_code=license_code
                                )
                                db.session.add(license_assignment)
                                created_codes.append(license_code)
                            
                            db.session.commit()
                            
                            current_app.logger.info(
                                f"Successfully created {licenses_to_create} new licenses for "
                                f"{target_user.email} (parent is {parent_role})"
                            )
                            
                            return True, None, {
                                'action': 'created_new_parent_unlimited',
                                'count': licenses_to_create,
                                'license_codes': created_codes,
                                'previous_count': current_license_count,
                                'new_count': new_license_count,
                                'parent_admin_id': parent_admin_id,
                                'parent_role': parent_role,
                                'note': f'Parent {parent_role} has unlimited licenses - created new licenses'
                            }
                        
                        else:
                            # Parent is regular admin - must check parent's licenses
                            current_app.logger.info(
                                f"Target admin {target_user.email} has parent admin (id={parent_admin_id}, role={parent_role}). "
                                f"Validating parent's licenses."
                            )
                            
                            # Validate parent has enough licenses
                            is_valid, error_msg, parent_stats = LicenseManager.validate_license_availability_for_admin(
                                parent_admin_id,
                                licenses_to_create
                            )
                            
                            if not is_valid:
                                locale = request.headers.get('Accept-Language', 'en')
                                return False, get_message('parent_not_enough_licenses', locale, error=error_msg), None
                            
                            # Transfer licenses from parent to target admin
                            success, error, transferred_codes = LicenseManager.transfer_licenses(
                                from_user_id=parent_admin_id,
                                to_user_id=target_user.id_user,
                                count=licenses_to_create
                            )
                            
                            if not success:
                                return False, error, None
                            
                            current_app.logger.info(
                                f"Successfully transferred {licenses_to_create} licenses from "
                                f"parent admin (id={parent_admin_id}) to {target_user.email}"
                            )
                            
                            return True, None, {
                                'action': 'created_from_parent',
                                'count': licenses_to_create,
                                'license_codes': transferred_codes,
                                'previous_count': current_license_count,
                                'new_count': new_license_count,
                                'parent_admin_id': parent_admin_id
                            }
                    
                    else:
                        # Target admin is a parent (id_admin is null) - unlimited licenses allowed
                        current_app.logger.info(
                            f"Target admin {target_user.email} is a parent admin (id_admin=NULL). "
                            f"Creating {licenses_to_create} new licenses without validation."
                        )
                        
                        # Create new licenses directly
                        created_codes = []
                        for i in range(licenses_to_create):
                            license_code = f"LIC-{uuid.uuid4().hex[:12].upper()}"
                            
                            new_license = TbLicences(licence_token=license_code)
                            db.session.add(new_license)
                            db.session.flush()  # Get id_licence
                            
                            # Assign to user in licence_admin
                            license_assignment = LicenceAdmin(
                                id_licence=new_license.id_licence,
                                id_user=target_user.id_user,
                                licence_code=license_code
                            )
                            db.session.add(license_assignment)
                            created_codes.append(license_code)
                        
                        db.session.commit()
                        
                        current_app.logger.info(
                            f"Successfully created {licenses_to_create} new licenses for "
                            f"parent admin {target_user.email}"
                        )
                        
                        return True, None, {
                            'action': 'created_new',
                            'count': licenses_to_create,
                            'license_codes': created_codes,
                            'previous_count': current_license_count,
                            'new_count': new_license_count,
                            'note': 'Parent admin - created new licenses without parent validation'
                        }
                
                # -------------------------------------------------------------
                # Rule 2: Admin updating their sub-admin
                # -------------------------------------------------------------
                elif current_user_role == 'admin':
                    current_app.logger.info(
                        f"Admin {current_user.email} updating sub-admin {target_user.email}. "
                        f"Validating admin's licenses."
                    )
                    
                    # Validate current admin has enough licenses
                    is_valid, error_msg, admin_stats = LicenseManager.validate_license_availability_for_admin(
                        current_user.id_user,
                        licenses_to_create
                    )
                    
                    if not is_valid:
                        return False, error_msg, None
                    
                    # Transfer licenses from current admin to target user
                    success, error, transferred_codes = LicenseManager.transfer_licenses(
                        from_user_id=current_user.id_user,
                        to_user_id=target_user.id_user,
                        count=licenses_to_create
                    )
                    
                    if not success:
                        return False, error, None
                    
                    current_app.logger.info(
                        f"Successfully transferred {licenses_to_create} licenses from "
                        f"admin {current_user.email} to {target_user.email}"
                    )
                    
                    return True, None, {
                        'action': 'created_from_admin',
                        'count': licenses_to_create,
                        'license_codes': transferred_codes,
                        'previous_count': current_license_count,
                        'new_count': new_license_count,
                        'admin_id': current_user.id_user
                    }
                
                # -------------------------------------------------------------
                # Other roles cannot update admin licenses
                # -------------------------------------------------------------
                else:
                    locale = request.headers.get('Accept-Language', 'en')
                    return False, get_message('role_cannot_update_licenses', locale, role=current_user_role), None
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"License update error: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return False, get_message('error_updating_licenses', locale, error=str(e)), None

