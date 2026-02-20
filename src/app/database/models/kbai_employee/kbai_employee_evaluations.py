"""
KBAI Employee Evaluation Model

Stores employee evaluation records with scores, dates, and evaluator information.
Each evaluation is linked to an employee and contains KPI information.
"""

from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Date, Text, ForeignKey, Index, select, desc
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Employee Evaluations
# --------------------------------------------------------------------------
class KbaiEmployeeEvaluation(Base):
    __tablename__ = 'kbai_employee_evaluations'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_employee_evaluations_employee_id', 'employee_id'),
        Index('idx_kbai_employee_evaluations_evaluator_id', 'evaluator_id'),
        Index('idx_kbai_employee_evaluations_evaluation_date', 'evaluation_date'),
        Index('idx_kbai_employee_evaluations_score', 'score_1_10'),
        Index('idx_kbai_employee_evaluations_kpi', 'kpi'),
        # Composite indexes for common queries
        Index('idx_kbai_employee_evaluations_employee_date', 'employee_id', 'evaluation_date'),
        Index('idx_kbai_employee_evaluations_evaluator_date', 'evaluator_id', 'evaluation_date'),
        {'schema': 'kbai_employee'}
    )

    # Primary Key
    id_evaluation = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    employee_id = Column(BigInteger, ForeignKey('kbai_employee.kbai_employees.id_evaluation'), nullable=False)
    evaluator_id = Column(BigInteger, nullable=False)  # ID of person who performed evaluation
    
    # Evaluation Information
    score_1_10 = Column(Integer, nullable=True)  # Score from 1 to 10
    evaluation_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    kpi = Column(String(50), nullable=True)  # Key Performance Indicator

    # Relationships
    employee = relationship('KbaiEmployee', back_populates='employee_evaluations')

    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_evaluation': self.id_evaluation,
            'employee_id': self.employee_id,
            'evaluator_id': self.evaluator_id,
            'score_1_10': self.score_1_10,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
            'notes': self.notes,
            'kpi': self.kpi
        }

    # --------------------------------------------------------------------------
    # Create a new employee evaluation
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, evaluation_data: Dict[str, Any]) -> Tuple[Optional['KbaiEmployeeEvaluation'], str]:
        """
        Create a new employee evaluation
        
        Args:
            evaluation_data: Dictionary containing evaluation information
            
        Returns:
            Tuple of (created_evaluation, error_message)
        """
        try:
            # Create new evaluation
            now = datetime.utcnow()
            evaluation = cls(
                employee_id=evaluation_data['employee_id'],
                evaluator_id=evaluation_data['evaluator_id'],
                score_1_10=evaluation_data.get('score_1_10'),
                evaluation_date=evaluation_data.get('evaluation_date'),
                notes=evaluation_data.get('notes'),
                kpi=evaluation_data.get('kpi'),
            )
            
            db.session.add(evaluation)
            db.session.commit()
            db.session.refresh(evaluation)
            
            return evaluation, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating employee evaluation: {str(e)}"

    # ------------------------------------------------------------------------------
    # Get an evaluation by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiEmployeeEvaluation']:
        """
        Find one employee evaluation by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like employee_id=1, id_evaluation=1, etc.
            
        Returns:
            Evaluation instance or None
            
        Examples:
            KbaiEmployeeEvaluation.findOne(employee_id=1)
            KbaiEmployeeEvaluation.findOne(select_columns=['id_evaluation', 'score_1_10'], id_evaluation=1)
            KbaiEmployeeEvaluation.findOne(evaluator_id=5, kpi='SALES')
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
    # Update evaluation information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update evaluation information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided
            if 'employee_id' in update_data:
                self.employee_id = update_data['employee_id']
            if 'evaluator_id' in update_data:
                self.evaluator_id = update_data['evaluator_id']
            if 'score_1_10' in update_data:
                self.score_1_10 = update_data['score_1_10']
            if 'evaluation_date' in update_data:
                self.evaluation_date = update_data['evaluation_date']
            if 'notes' in update_data:
                self.notes = update_data['notes']
            if 'kpi' in update_data:
                self.kpi = update_data['kpi']
                        
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating employee evaluation: {str(e)}"

    # -----------------------------------------------------------------------------
    # Delete evaluation
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete employee evaluation (hard delete)
        
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
            return False, f"Error deleting employee evaluation: {str(e)}"

    # -----------------------------------------------------------------------------
    # Find evaluations with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, select_columns=None, **filters) -> Tuple[List['KbaiEmployeeEvaluation'], int, str]:
        """
        Find employee evaluations with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for notes or kpi
            select_columns: List of column names to select (optional)
            **filters: Field filters like employee_id=1, evaluator_id=5, kpi='SALES', etc.
            
        Returns:
            Tuple of (evaluations_list, total_count, error_message)
            
        Examples:
            KbaiEmployeeEvaluation.find()  # Get all evaluations (latest first)
            KbaiEmployeeEvaluation.find(employee_id=1)  # Filter by employee
            KbaiEmployeeEvaluation.find(evaluator_id=5, kpi='SALES')  # Multiple filters
            KbaiEmployeeEvaluation.find(search='excellent')  # Search in notes
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
                stmt = stmt.where(
                    cls.notes.ilike(f'%{search}%') | cls.kpi.ilike(f'%{search}%')
                )
                        
            # Get total count
            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            if search:
                count_stmt = count_stmt.where(
                    cls.notes.ilike(f'%{search}%') | cls.kpi.ilike(f'%{search}%')
                )
            total = db.session.execute(count_stmt).rowcount
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing employee evaluations: {str(e)}"


__all__ = ['KbaiEmployeeEvaluation']
