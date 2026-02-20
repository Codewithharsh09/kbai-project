"""
KBAI Company Zone Model

Linking table for many-to-many relationship between companies and zones.
Each company can be associated with multiple zones, and each zone can have multiple companies.
"""

from sqlalchemy import Column, BigInteger, Boolean, DateTime, ForeignKey, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Company Zone Linking Table
# --------------------------------------------------------------------------
class KbaiCompanyZone(Base):
    __tablename__ = 'kbai_company_zone'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_company_zone_company', 'id_company'),
        Index('idx_kbai_company_zone_zone', 'id_zone'),
        # Composite index for company-zone lookups
        Index('idx_kbai_company_zone_lookup', 'id_company', 'id_zone'),
        {'schema': 'kbai'}
    )

    # Foreign Keys
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), primary_key=True)
    id_zone = Column(BigInteger, ForeignKey('kbai.kbai_zone.id_zone'), primary_key=True)
    
    # Zone Information
    primary_flag = Column(Boolean, default=False, nullable=False)  # Primary zone for company
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship('KbaiCompany', back_populates='company_zones')
    zone = relationship('KbaiZone', backref='zone_companies')
    
    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_company': self.id_company,
            'id_zone': self.id_zone,
            'primary_flag': self.primary_flag,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    # --------------------------------------------------------------------------
    # Create a new company-zone association
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, company_zone_data: Dict[str, Any]) -> Tuple[Optional['KbaiCompanyZone'], str]:
        """
        Create a new company-zone association
        
        Args:
            company_zone_data: Dictionary containing company-zone information
            
        Returns:
            Tuple of (created_company_zone, error_message)
        """
        try:
            # Create new company-zone association
            now = datetime.utcnow()
            company_zone = cls(
                id_company=company_zone_data['id_company'],
                id_zone=company_zone_data['id_zone'],
                primary_flag=company_zone_data.get('primary_flag', False),
                created_at=now,
                updated_at=now
            )
            
            db.session.add(company_zone)
            db.session.commit()
            
            return company_zone, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating company-zone association: {str(e)}"
    
    # ------------------------------------------------------------------------------
    # Get company-zone association by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiCompanyZone']:
        """
        Find one company-zone association by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_zone=2, etc.
            
        Returns:
            Company-zone association instance or None
            
        Examples:
            KbaiCompanyZone.findOne(id_company=1)
            KbaiCompanyZone.findOne(select_columns=['id_company', 'primary_flag'], id_company=1)
        """
        try:
            if select_columns:
                # Convert column names to actual column objects
                columns = []
                for col_name in select_columns:
                    if hasattr(cls, col_name):
                        columns.append(getattr(cls, col_name))
                if columns:
                    stmt = select(*columns)
                else:
                    stmt = select(cls)
            else:
                stmt = select(cls)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)
            
            result = db.session.execute(stmt).first()
            return result
        except Exception:
            return None
    
    # ------------------------------------------------------------------------------
    # Update company-zone association
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update company-zone association information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided
            if 'primary_flag' in update_data:
                self.primary_flag = update_data['primary_flag']
            
            # Update timestamp
            self.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating company-zone association: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Delete company-zone association
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete company-zone association (hard delete)
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting company-zone association: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Find company-zone associations with filtering
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, select_columns=None, **filters) -> Tuple[List['KbaiCompanyZone'], int, str]:
        """
        Find company-zone associations with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_zone=2, primary_flag=True, etc.
            
        Returns:
            Tuple of (company_zone_associations, total_count, error_message)
            
        Examples:
            KbaiCompanyZone.find()
            KbaiCompanyZone.find(select_columns=['id_company', 'primary_flag'], id_company=1)
        """
        try:
            # Build select statement
            if select_columns:
                # Convert column names to actual column objects
                columns = []
                for col_name in select_columns:
                    if hasattr(cls, col_name):
                        columns.append(getattr(cls, col_name))
                if columns:
                    stmt = select(*columns)
                else:
                    stmt = select(cls)
            else:
                stmt = select(cls)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)
            
            # Get total count (without column selection for accurate count)
            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            total = db.session.execute(count_stmt).rowcount
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing company-zone associations: {str(e)}"
