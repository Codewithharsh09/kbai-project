"""
KBAI Company Sector Model

Linking table for many-to-many relationship between companies and sectors.
Each company can be associated with multiple sectors, and each sector can have multiple companies.
"""

from sqlalchemy import Column, BigInteger, Boolean, DateTime, ForeignKey, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Company Sector Linking Table
# --------------------------------------------------------------------------
class KbaiCompanySector(Base):
    __tablename__ = 'kbai_company_sector'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_company_sector_company', 'id_company'),
        Index('idx_kbai_company_sector_sector', 'id_sector'),
        # Composite index for company-sector lookups
        Index('idx_kbai_company_sector_lookup', 'id_company', 'id_sector'),
        {'schema': 'kbai'}
    )

    # Foreign Keys
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), primary_key=True)
    id_sector = Column(BigInteger, ForeignKey('kbai.kbai_sectors.id_sector'), primary_key=True)
    
    # Sector Information
    primary_flag = Column(Boolean, default=False, nullable=False)  # Primary sector for company
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship('KbaiCompany', back_populates='company_sectors')
    sector = relationship('KbaiSector', backref='sector_companies')
    
    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_company': self.id_company,
            'id_sector': self.id_sector,
            'primary_flag': self.primary_flag,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    # --------------------------------------------------------------------------
    # Create a new company-sector association
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, company_sector_data: Dict[str, Any]) -> Tuple[Optional['KbaiCompanySector'], str]:
        """
        Create a new company-sector association
        
        Args:
            company_sector_data: Dictionary containing company-sector information
            
        Returns:
            Tuple of (created_company_sector, error_message)
        """
        try:
            # Create new company-sector association
            now = datetime.utcnow()
            company_sector = cls(
                id_company=company_sector_data['id_company'],
                id_sector=company_sector_data['id_sector'],
                primary_flag=company_sector_data.get('primary_flag', False),
                created_at=now,
                updated_at=now
            )
            
            db.session.add(company_sector)
            db.session.commit()
            
            return company_sector, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating company-sector association: {str(e)}"
    
    # ------------------------------------------------------------------------------
    # Get company-sector association by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiCompanySector']:
        """
        Find one company-sector association by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_sector=2, etc.
            
        Returns:
            Company-sector association instance or None
            
        Examples:
            KbaiCompanySector.findOne(id_company=1)
            KbaiCompanySector.findOne(select_columns=['id_company', 'primary_flag'], id_company=1)
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
    # Update company-sector association
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update company-sector association information
        
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
            return False, f"Error updating company-sector association: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Delete company-sector association
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete company-sector association (hard delete)
        
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
            return False, f"Error deleting company-sector association: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Find company-sector associations with filtering
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, select_columns=None, **filters) -> Tuple[List['KbaiCompanySector'], int, str]:
        """
        Find company-sector associations with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_sector=2, primary_flag=True, etc.
            
        Returns:
            Tuple of (company_sector_associations, total_count, error_message)
            
        Examples:
            KbaiCompanySector.find()
            KbaiCompanySector.find(select_columns=['id_company', 'primary_flag'], id_company=1)
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
            return [], 0, f"Error listing company-sector associations: {str(e)}"
