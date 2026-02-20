from sqlalchemy import Column, BigInteger, Numeric, ForeignKey, DateTime, String, func
from sqlalchemy.orm import relationship
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiGoalProgress(Base):
    """
    KBAI Goal Progress model for storing goal progress data
    """
    __tablename__ = 'kbai_goal_progress'
    __table_args__ = {'schema': 'kbai_balance'}

    id_progress = Column(BigInteger, primary_key=True, autoincrement=True)
    goal_id = Column(BigInteger, ForeignKey('kbai_balance.kbai_goal_objectives.id_objectives'), nullable=False)
    completion_percent = Column(Numeric, nullable=False)
    deviation = Column(Numeric)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    goal_objective = relationship('KbaiGoalObjective', back_populates='goal_progresses')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_progress': self.id_progress,
            'goal_id': self.goal_id,
            'completion_percent': float(self.completion_percent) if self.completion_percent else None,
            'deviation': float(self.deviation) if self.deviation else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, goal_progress_data: dict):
        """Create a new goal progress record"""
        try:
            goal_progress = cls(**goal_progress_data)
            from src.extensions import db
            db.session.add(goal_progress)
            db.session.commit()
            return goal_progress, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one goal progress record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, **filters):
        """Find goal progress records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update goal progress record"""
        try:
            for key, value in update_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.updated_at = datetime.utcnow()
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
