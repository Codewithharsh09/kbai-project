from sqlalchemy import Column, BigInteger, Numeric, Date, String, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiGoalObjective(Base):
    """
    KBAI Goal Objectives model for storing goal and objective data
    """
    __tablename__ = 'kbai_goal_objectives'
    __table_args__ = {'schema': 'kbai_balance'}

    id_objectives = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(BigInteger, nullable=False)
    kpi_id = Column(BigInteger, nullable=False)
    target_value = Column(Numeric, nullable=False)
    due_date = Column(Date, nullable=False)
    created_by = Column(BigInteger, nullable=False)
    status = Column(String(50), default='ACTIVE', nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    goal_progresses = relationship('KbaiGoalProgress', back_populates='goal_objective')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_objectives': self.id_objectives,
            'company_id': self.company_id,
            'kpi_id': self.kpi_id,
            'target_value': float(self.target_value) if self.target_value else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_by': self.created_by,
            'status': self.status,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, goal_objective_data: dict):
        """Create a new goal objective record"""
        try:
            goal_objective = cls(**goal_objective_data)
            from src.extensions import db
            db.session.add(goal_objective)
            db.session.commit()
            return goal_objective, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one goal objective record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find goal objective records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.status.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update goal objective record"""
        try:
            for key, value in update_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            from src.extensions import db
            db.session.commit()
            return True, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return False, str(e)

    def delete(self):
        """Hard delete analysis record"""
        try:
            from src.extensions import db
            db.session.delete(self)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)
