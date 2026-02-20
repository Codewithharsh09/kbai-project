"""
TB User Company Service

Handles user-company mapping operations
"""

import logging
from typing import List, Tuple, Optional
from datetime import datetime

from flask import current_app
from src.extensions import db
from src.app.database.models import TbUserCompany, KbaiCompany, TbUser

logger = logging.getLogger(__name__)


class TbUserCompanyService:
    """Service for managing user-company mappings"""
    
    @staticmethod
    def create_mappings(user_id: int, company_ids: List[int]) -> Tuple[bool, Optional[str], int]:
        """
        Create mappings between user and multiple companies
        
        Args:
            user_id: User ID to map
            company_ids: List of company IDs to map to user
            
        Returns:
            Tuple of (success, error_message, mapped_count)
        """
        try:
            if not company_ids:
                return True, None, 0
            
            mapped_count = 0
            skipped_companies = []
            
            for company_id in company_ids:
                # Check if company exists and is not deleted
                company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
                if not company:
                    logger.warning(f"Company {company_id} not found or deleted, skipping mapping")
                    skipped_companies.append(company_id)
                    continue
                
                # Check if mapping already exists
                existing_mapping = TbUserCompany.query.filter_by(
                    id_user=user_id,
                    id_company=company_id
                ).first()
                
                if existing_mapping:
                    logger.info(f"Mapping already exists for user {user_id} and company {company_id}")
                    mapped_count += 1
                    continue
                
                # Create new mapping
                user_company = TbUserCompany(
                    id_user=user_id,
                    id_company=company_id,
                    date_assigned=datetime.utcnow()
                )
                db.session.add(user_company)
                mapped_count += 1
                logger.info(f"Created mapping: user {user_id} -> company {company_id}")
            
            db.session.commit()
            
            logger.info(f"Successfully created {mapped_count} user-company mappings for user {user_id}")
            
            if skipped_companies:
                return True, f"Skipped {len(skipped_companies)} invalid companies", mapped_count
            
            return True, None, mapped_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user-company mappings: {str(e)}")
            return False, str(e), 0
    
    @staticmethod
    def get_user_companies(user_id: int) -> List[int]:
        """
        Get list of company IDs assigned to a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of company IDs
        """
        try:
            mappings = TbUserCompany.query.filter_by(id_user=user_id).all()
            return [mapping.id_company for mapping in mappings]
        except Exception as e:
            logger.error(f"Error getting user companies: {str(e)}")
            return []
    
    @staticmethod
    def remove_mapping(user_id: int, company_id: int) -> Tuple[bool, Optional[str]]:
        """
        Remove mapping between user and company
        
        Args:
            user_id: User ID
            company_id: Company ID
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            mapping = TbUserCompany.query.filter_by(
                id_user=user_id,
                id_company=company_id
            ).first()
            
            if not mapping:
                return False, "Mapping not found"
            
            db.session.delete(mapping)
            db.session.commit()
            
            logger.info(f"Removed mapping: user {user_id} -> company {company_id}")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing mapping: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def remove_all_user_mappings(user_id: int) -> Tuple[bool, Optional[str], int]:
        """
        Remove all company mappings for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (success, error_message, removed_count)
        """
        try:
            count = TbUserCompany.query.filter_by(id_user=user_id).delete()
            db.session.commit()
            
            logger.info(f"Removed {count} company mappings for user {user_id}")
            return True, None, count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing user mappings: {str(e)}")
            return False, str(e), 0
    
    @staticmethod
    def update_user_companies(user_id: int, new_company_ids: List[int]) -> Tuple[bool, Optional[str], dict]:
        """
        Update company mappings for a user (add/remove as needed)
        
        Args:
            user_id: User ID
            new_company_ids: New list of company IDs to assign
            
        Returns:
            Tuple of (success, error_message, update_info)
            update_info contains: companies_added, companies_removed, total_companies
        """
        try:
            # Get current company mappings
            current_mappings = TbUserCompany.query.filter_by(id_user=user_id).all()
            current_company_ids = [m.id_company for m in current_mappings]
            
            # Determine which companies to add and remove
            companies_to_add = [cid for cid in new_company_ids if cid not in current_company_ids]
            companies_to_remove = [cid for cid in current_company_ids if cid not in new_company_ids]
            
            added_count = 0
            removed_count = 0
            skipped_companies = []
            
            # Add new companies
            if companies_to_add:
                for company_id in companies_to_add:
                    # Verify company exists
                    company = KbaiCompany.findOne(id_company=company_id, is_deleted=False)
                    if company:
                        mapping = TbUserCompany(
                            id_user=user_id,
                            id_company=company_id,
                            date_assigned=datetime.utcnow()
                        )
                        db.session.add(mapping)
                        added_count += 1
                        logger.info(f"Added company {company_id} to user {user_id}")
                    else:
                        logger.warning(f"Company {company_id} not found or deleted, skipping")
                        skipped_companies.append(company_id)
            
            # Remove old companies
            if companies_to_remove:
                for company_id in companies_to_remove:
                    TbUserCompany.query.filter_by(
                        id_user=user_id,
                        id_company=company_id
                    ).delete()
                    removed_count += 1
                    logger.info(f"Removed company {company_id} from user {user_id}")
            
            db.session.commit()
            
            update_info = {
                'companies_added': added_count,
                'companies_removed': removed_count,
                'total_companies': len(new_company_ids),
                'skipped_companies': skipped_companies if skipped_companies else None
            }
            
            logger.info(f"Company mappings updated for user {user_id}: +{added_count}, -{removed_count}")
            
            return True, None, update_info
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user companies: {str(e)}")
            return False, str(e), {}


# Create service instance
tb_user_company_service = TbUserCompanyService()

