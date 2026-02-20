"""
KBAI State Model

Tracks various states or statuses related to companies.
Each company can have multiple states with different actions, points, and crisis probabilities.
"""

from sqlalchemy import Column, BigInteger, String, SmallInteger, Numeric, DateTime, ForeignKey, Index, or_, desc, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Company States
# --------------------------------------------------------------------------
class KbaiState(Base):
    __tablename__ = 'kbai_state'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_state_company', 'id_company'),
        Index('idx_kbai_state_status', 'status_flag'),
        Index('idx_kbai_state_created_by', 'created_by'),
        # Composite index for company-status lookups
        Index('idx_kbai_state_company_status', 'id_company', 'status_flag'),
        {'schema': 'kbai'}
    )

    # Primary Key
    id_state = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), nullable=False)
    created_by = Column(BigInteger, ForeignKey('public.tb_user.id_user'), nullable=True)
    
    # State Information
    state = Column(String, nullable=True)  # State name/description
    actions = Column(String, nullable=True)  # Actions taken
    points = Column(SmallInteger, nullable=True)  # Points assigned
    crisis_probability = Column(Numeric, nullable=True)  # Crisis probability percentage
    status_flag = Column(String, nullable=True)  # Status flag (ACTIVE, INACTIVE, etc.)
    
    # Timestamps
    time = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship('KbaiCompany', back_populates='company_states')
    creator = relationship('TbUser', backref='created_states')
    
    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_state': self.id_state,
            'id_company': self.id_company,
            'created_by': self.created_by,
            'state': self.state,
            'actions': self.actions,
            'points': self.points,
            'crisis_probability': float(self.crisis_probability) if self.crisis_probability else None,
            'status_flag': self.status_flag,
            'time': self.time.isoformat() if self.time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    # --------------------------------------------------------------------------
    # Create a new state
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, state_data: Dict[str, Any]) -> Tuple[Optional['KbaiState'], str]:
        """
        Create a new state
        
        Args:
            state_data: Dictionary containing state information
            
        Returns:
            Tuple of (created_state, error_message)
        """
        try:
            # Create new state
            now = datetime.utcnow()
            state = cls(
                id_company=state_data['id_company'],
                created_by=state_data.get('created_by'),
                state=state_data.get('state'),
                actions=state_data.get('actions'),
                points=state_data.get('points'),
                crisis_probability=state_data.get('crisis_probability'),
                status_flag=state_data.get('status_flag', 'ACTIVE'),
                time=now,
                created_at=now,
                updated_at=now
            )
            
            db.session.add(state)
            db.session.commit()
            
            return state, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating state: {str(e)}"
    
    # ------------------------------------------------------------------------------
    # Get state by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiState']:
        """
        Find one state by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_state=1, id_company=1, etc.
            
        Returns:
            State instance or None
            
        Examples:
            KbaiState.findOne(id_state=1)
            KbaiState.findOne(select_columns=['id_state', 'state', 'points'], id_company=1)
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
    # Update state information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update state information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided
            if 'state' in update_data:
                self.state = update_data['state']
            if 'actions' in update_data:
                self.actions = update_data['actions']
            if 'points' in update_data:
                self.points = update_data['points']
            if 'crisis_probability' in update_data:
                self.crisis_probability = update_data['crisis_probability']
            if 'status_flag' in update_data:
                self.status_flag = update_data['status_flag']
            
            # Update timestamps
            now = datetime.utcnow()
            self.time = now
            self.updated_at = now
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating state: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Delete state
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete state (hard delete)
        
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
            return False, f"Error deleting state: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Find states with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, 
             search: str = None, select_columns=None, **filters) -> Tuple[List['KbaiState'], int, str]:
        """
        Find states with filtering and pagination (sorted by latest first)
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for state name or actions
            select_columns: List of column names to select (optional)
            **filters: Field filters like id_company=1, status_flag='ACTIVE', etc.
            
        Returns:
            Tuple of (states_list, total_count, error_message)
            
        Examples:
            KbaiState.find()
            KbaiState.find(select_columns=['id_state', 'state', 'points'], id_company=1)
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
                    or_(
                        cls.state.ilike(f'%{search}%'),
                        cls.actions.ilike(f'%{search}%')
                    )
                )
            
            # Sort by latest first
            stmt = stmt.order_by(desc(cls.time))
            
            # Get total count (without column selection for accurate count)
            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            if search:
                count_stmt = count_stmt.where(
                    or_(
                        cls.state.ilike(f'%{search}%'),
                        cls.actions.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).rowcount
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing states: {str(e)}"
