"""
KBAI Employee Company Map Model

Junction table for many-to-many relationship between employees and companies.
Each employee can be associated with multiple companies.
"""

from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Employee Company Map
# --------------------------------------------------------------------------
class KbaiEmployeeCompanyMap(Base):
    __tablename__ = 'kbai_employee_company_map'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_employee_company_map_id_company', 'id_company'),
        Index('idx_kbai_employee_company_map_id_evaluation', 'id_evaluation'),
        # Composite index for unique constraint
        Index('idx_kbai_employee_company_map_unique', 'id_company', 'id_evaluation', unique=True),
        {'schema': 'kbai_employee'}
    )

    # Primary Key (composite)
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), primary_key=True)
    id_evaluation = Column(BigInteger, ForeignKey('kbai_employee.kbai_employees.id_evaluation'), primary_key=True)

    # Relationships
    company = relationship('KbaiCompany', back_populates='employee_company_map')
    employee = relationship('KbaiEmployee', back_populates='employee_company_map')

    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_company': self.id_company,
            'id_evaluation': self.id_evaluation,
        }

    # --------------------------------------------------------------------------
    # Create a new employee-company mapping
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, mapping_data: Dict[str, Any]) -> Tuple[Optional['KbaiEmployeeCompanyMap'], str]:
        """
        Create a new employee-company mapping
        
        Args:
            mapping_data: Dictionary containing mapping information
            
        Returns:
            Tuple of (created_mapping, error_message)
        """
        try:
            # Check if mapping already exists
            existing_mapping = cls.query.filter_by(
                id_company=mapping_data['id_company'],
                id_evaluation=mapping_data['id_evaluation']
            ).first()
            if existing_mapping:
                return None, "Employee-company mapping already exists"
            
            # Create new mapping
            now = datetime.utcnow()
            mapping = cls(
                id_company=mapping_data['id_company'],
                id_evaluation=mapping_data['id_evaluation'],
            )
            
            db.session.add(mapping)
            db.session.commit()
            db.session.refresh(mapping)
            
            return mapping, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating employee-company mapping: {str(e)}"

    # ------------------------------------------------------------------------------
    # Get a mapping by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiEmployeeCompanyMap']:
        """
        Find one employee-company mapping by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_evaluation=1, etc.
            
        Returns:
            Mapping instance or None
            
        Examples:
            KbaiEmployeeCompanyMap.findOne(id_company=1, id_evaluation=1)
            KbaiEmployeeCompanyMap.findOne(select_columns=['id_company'], id_evaluation=1)
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

    # -----------------------------------------------------------------------------
    # Delete employee-company mapping
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete employee-company mapping (hard delete)
        
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
            return False, f"Error deleting employee-company mapping: {str(e)}"

    # -----------------------------------------------------------------------------
    # Find mappings with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, select_columns=None, **filters) -> Tuple[List['KbaiEmployeeCompanyMap'], int, str]:
        """
        Find employee-company mappings with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, id_evaluation=1, etc.
            
        Returns:
            Tuple of (mappings_list, total_count, error_message)
            
        Examples:
            KbaiEmployeeCompanyMap.find()  # Get all mappings
            KbaiEmployeeCompanyMap.find(id_company=1)  # Filter by company
            KbaiEmployeeCompanyMap.find(id_evaluation=1)  # Filter by employee
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
            
            # Sort by latest created first
            # stmt = stmt.order_by(cls.created_at.desc())
            
            # Get total count
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
            return [], 0, f"Error listing employee-company mappings: {str(e)}"


__all__ = ['KbaiEmployeeCompanyMap']
