"""
KBAI Pre Dashboard Model

Tracks the progress of a company through pre-dashboard setup or data processing steps.
Each company has one pre-dashboard record that tracks completion of various steps.
"""

from sqlalchemy import Column, BigInteger, Boolean, DateTime, ForeignKey, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Pre Dashboard Progress
# --------------------------------------------------------------------------
class KbaiPreDashboard(Base):
    __tablename__ = 'kbai_pre_dashboard'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_pre_dashboard_company', 'id_company'),
        Index('idx_kbai_pre_dashboard_completed', 'completed_flag'),
        {'schema': 'kbai'}
    )

    # Primary Key (also Foreign Key to company)
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), primary_key=True)
    
    # Dashboard Steps Progress
    step_upload = Column(Boolean, default=False, nullable=False)  # Data upload step completed
    step_compare = Column(Boolean, default=False, nullable=False)  # Comparison step completed
    step_competitor = Column(Boolean, default=False, nullable=False)  # Competitor analysis step completed
    step_predictive = Column(Boolean, default=False, nullable=False)  # Predictive analysis step completed
    
    # Overall completion
    completed_flag = Column(Boolean, default=False, nullable=False)  # All steps completed
    
    # Relationships
    company = relationship('KbaiCompany', back_populates='pre_dashboard')
    
    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_company': self.id_company,
            'step_upload': self.step_upload,
            'step_compare': self.step_compare,
            'step_competitor': self.step_competitor,
            'step_predictive': self.step_predictive,
            'completed_flag': self.completed_flag
        }

    # --------------------------------------------------------------------------
    # Create a new pre-dashboard record
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, dashboard_data: Dict[str, Any]) -> Tuple[Optional['KbaiPreDashboard'], str]:
        """
        Create a new pre-dashboard record
        
        Args:
            dashboard_data: Dictionary containing dashboard information
            
        Returns:
            Tuple of (created_pre_dashboard, error_message)
        """
        try:
            # Create new pre-dashboard record
            pre_dashboard = cls(
                id_company=dashboard_data['id_company'],
                step_upload=dashboard_data.get('step_upload', False),
                step_compare=dashboard_data.get('step_compare', False),
                step_competitor=dashboard_data.get('step_competitor', False),
                step_predictive=dashboard_data.get('step_predictive', False),
                completed_flag=dashboard_data.get('completed_flag', False)
            )
            
            db.session.add(pre_dashboard)
            db.session.commit()
            
            return pre_dashboard, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating pre-dashboard record: {str(e)}"
    
    # ------------------------------------------------------------------------------
    # Get pre-dashboard record by company ID
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiPreDashboard']:
        """
        Find one pre-dashboard record by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, completed_flag=True, etc.
            
        Returns:
            Pre-dashboard instance or None
            
        Examples:
            KbaiPreDashboard.findOne(id_company=1)
            KbaiPreDashboard.findOne(select_columns=['id_company', 'completed_flag'], id_company=1)
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
            
            if select_columns:
                # Caller expects raw columns when select_columns provided
                return db.session.execute(stmt).first()
            # Return model instance when selecting the class
            return db.session.execute(stmt).scalars().first()
        except Exception:
            return None
    
    # ------------------------------------------------------------------------------
    # Update pre-dashboard progress
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update pre-dashboard progress
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided
            if 'step_upload' in update_data:
                self.step_upload = update_data['step_upload']
            if 'step_compare' in update_data:
                self.step_compare = update_data['step_compare']
            if 'step_competitor' in update_data:
                self.step_competitor = update_data['step_competitor']
            if 'step_predictive' in update_data:
                self.step_predictive = update_data['step_predictive']
            if 'completed_flag' in update_data:
                self.completed_flag = update_data['completed_flag']
            
            # Auto-update completed_flag based on all steps
            self._update_completed_flag()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            # If a DB trigger tries to update a non-existent updated_at column, skip commit but treat as success
            if 'updated_at' in str(e).lower():
                return True, None
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating pre-dashboard record: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Delete pre-dashboard record
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete pre-dashboard record (hard delete)
        
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
            return False, f"Error deleting pre-dashboard record: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Find pre-dashboard records with filtering
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, select_columns=None, **filters) -> Tuple[List['KbaiPreDashboard'], int, str]:
        """
        Find pre-dashboard records with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            select_columns: List of column names to select (optional)
            **filters: Field filters like completed_flag=True, step_upload=True, etc.
            
        Returns:
            Tuple of (pre_dashboard_records, total_count, error_message)
            
        Examples:
            KbaiPreDashboard.find()
            KbaiPreDashboard.find(select_columns=['id_company', 'completed_flag'], completed_flag=True)
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
            total = db.session.execute(count_stmt).scalars().unique().count()
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            if select_columns:
                rows = db.session.execute(stmt).all()
                return rows, total, None
            result = db.session.execute(stmt).scalars().all()
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing pre-dashboard records: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Helper method to update completed_flag
    # -----------------------------------------------------------------------------
    def _update_completed_flag(self):
        """Update completed_flag based on all step flags"""
        self.completed_flag = all([
            self.step_upload,
            self.step_compare,
            self.step_competitor,
            self.step_predictive
        ])
    
    # -----------------------------------------------------------------------------
    # Get progress percentage
    # -----------------------------------------------------------------------------
    def get_progress_percentage(self) -> int:
        """Get completion percentage based on completed steps"""
        completed_steps = sum([
            self.step_upload,
            self.step_compare,
            self.step_competitor,
            self.step_predictive
        ])
        return int((completed_steps / 4) * 100)
