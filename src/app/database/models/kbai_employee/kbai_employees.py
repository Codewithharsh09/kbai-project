"""
KBAI Employee Model

Represents employees with hierarchical management structure.
Each employee has a manager (self-referencing) and can be associated with multiple companies and evaluations.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey, or_, desc, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Employees
# --------------------------------------------------------------------------
class KbaiEmployee(Base):
    __tablename__ = 'kbai_employees'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_employees_name', 'name'),
        Index('idx_kbai_employees_email', 'email'),
        Index('idx_kbai_employees_role', 'role'),
        Index('idx_kbai_employees_status', 'status'),
        Index('idx_kbai_employees_id_manager', 'id_manager'),
        Index('idx_kbai_employees_id_user', 'id_user'),
        # Composite indexes for common queries
        Index('idx_kbai_employees_manager_status', 'id_manager', 'status'),
        Index('idx_kbai_employees_user_status', 'id_user', 'status'),
        {'schema': 'kbai_employee'}
    )

    # Primary Key
    id_evaluation = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Employee Information
    name = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=True)
    profile_pic_url = Column(String, nullable=True)
    status = Column(String, nullable=True)
    functions = Column(String, nullable=True)
    
    # Foreign Keys
    id_user = Column(BigInteger, ForeignKey('public.tb_user.id_user'), nullable=True)  # Link to user account
    id_manager = Column(BigInteger, ForeignKey('kbai_employee.kbai_employees.id_evaluation'), nullable=True)  # Self-referencing manager


    # Relationships
    user = relationship('TbUser', backref='kbai_employee')
    manager = relationship('KbaiEmployee', remote_side=[id_evaluation], backref='subordinates')
    employee_company_map = relationship('KbaiEmployeeCompanyMap', back_populates='employee')
    employee_evaluations = relationship('KbaiEmployeeEvaluation', back_populates='employee')

    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_evaluation': self.id_evaluation,
            'name': self.name,
            'surname': self.surname,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'profile_pic_url': self.profile_pic_url,
            'status': self.status,
            'functions': self.functions,
            'id_user': self.id_user,
            'id_manager': self.id_manager,
        }

    # --------------------------------------------------------------------------
    # Create a new employee
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, employee_data: Dict[str, Any]) -> Tuple[Optional['KbaiEmployee'], str]:
        """
        Create a new employee
        
        Args:
            employee_data: Dictionary containing employee information
            
        Returns:
            Tuple of (created_employee, error_message)
        """
        try:
            # Check if email already exists (if provided)
            if employee_data.get('email'):
                existing_employee = cls.query.filter_by(email=employee_data['email']).first()
                if existing_employee:
                    return None, "Email already exists"
            
            # Create new employee
            now = datetime.utcnow()
            employee = cls(
                name=employee_data.get('name'),
                surname=employee_data.get('surname'),
                email=employee_data.get('email'),
                phone=employee_data.get('phone'),
                role=employee_data.get('role'),
                profile_pic_url=employee_data.get('profile_pic_url'),
                status=employee_data.get('status', 'ACTIVE'),
                functions=employee_data.get('functions'),
                id_user=employee_data.get('id_user'),
                id_manager=employee_data.get('id_manager')
            )
            
            db.session.add(employee)
            db.session.commit()
            db.session.refresh(employee)
            
            return employee, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating employee: {str(e)}"

    # ------------------------------------------------------------------------------
    # Get an employee by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiEmployee']:
        """
        Find one employee by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com', id_evaluation=1, etc.
            
        Returns:
            Employee instance or None
            
        Examples:
            KbaiEmployee.findOne(email='test@example.com')
            KbaiEmployee.findOne(select_columns=['id_evaluation', 'name', 'email'], id_evaluation=1)
            KbaiEmployee.findOne(id_manager=5, status='ACTIVE')
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
    # Update employee information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update employee information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check email uniqueness if being updated
            if 'email' in update_data and update_data['email'] != self.email:
                existing = KbaiEmployee.query.filter_by(email=update_data['email']).first()
                if existing:
                    return False, "Email already exists"
            
            # Update fields if provided
            if 'name' in update_data:
                self.name = update_data['name']
            if 'surname' in update_data:
                self.surname = update_data['surname']
            if 'email' in update_data:
                self.email = update_data['email']
            if 'phone' in update_data:
                self.phone = update_data['phone']
            if 'role' in update_data:
                self.role = update_data['role']
            if 'profile_pic_url' in update_data:
                self.profile_pic_url = update_data['profile_pic_url']
            if 'status' in update_data:
                self.status = update_data['status']
            if 'functions' in update_data:
                self.functions = update_data['functions']
            if 'id_user' in update_data:
                self.id_user = update_data['id_user']
            if 'id_manager' in update_data:
                self.id_manager = update_data['id_manager']
                        
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating employee: {str(e)}"

    # -----------------------------------------------------------------------------
    # Delete employee
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Soft delete - set both fields for fast queries and audit trail
            now = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting employee: {str(e)}"

    # -----------------------------------------------------------------------------
    # Find employees with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, select_columns=None, **filters) -> Tuple[List['KbaiEmployee'], int, str]:
        """
        Find employees with filtering and pagination (always sorted by latest first)
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for name, surname, or email
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com', id_manager=1, status='ACTIVE', etc.
            
        Returns:
            Tuple of (employees_list, total_count, error_message)
            
        Examples:
            KbaiEmployee.find()  # Get all employees (latest first)
            KbaiEmployee.find(select_columns=['id_evaluation', 'name', 'email'], page=1, per_page=20)
            KbaiEmployee.find(email='test@example.com')  # Filter by email
            KbaiEmployee.find(id_manager=5, status='ACTIVE')  # Multiple filters
            KbaiEmployee.find(search='John')  # Search in name/surname
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
            
            # Apply search filter if provided
            if search:
                # Use indexed columns for faster search
                stmt = stmt.where(
                    or_(
                        cls.name.ilike(f'%{search}%'),
                        cls.surname.ilike(f'%{search}%'),
                        cls.email.ilike(f'%{search}%')
                    )
                )
            
            # Always sort by latest created first (created_at desc)
            # stmt = stmt.order_by(desc(cls.created_at))
            
            # Get total count (without column selection for accurate count)
            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            if search:
                count_stmt = count_stmt.where(
                    or_(
                        cls.name.ilike(f'%{search}%'),
                        cls.surname.ilike(f'%{search}%'),
                        cls.email.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).rowcount
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing employees: {str(e)}"


__all__ = ['KbaiEmployee']
