from sqlalchemy import Column, BigInteger, String, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiAnalysis(Base):
    """
    KBAI Analysis model for storing analysis data
    """
    __tablename__ = 'kbai_analysis'
    __table_args__ = {'schema': 'kbai_balance'}

    id_analysis = Column(BigInteger, primary_key=True, autoincrement=True)
    analysis_name = Column(String(255), nullable=False)
    analysis_type = Column(String(255), nullable=False)
    time = Column(DateTime, default=datetime.utcnow, nullable=False)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    analysis_kpis = relationship('KbaiAnalysisKpi', back_populates='analysis')
    analysis_kpi_infos = relationship('AnalysisKpiInfo', back_populates='analysis')
    reports = relationship('KbaiReport', back_populates='analysis')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_analysis': self.id_analysis,
            'analysis_name': self.analysis_name,
            'analysis_type': self.analysis_type,
            'time': self.time.isoformat() if self.time else None,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, analysis_data: dict):
        """Create a new analysis record"""
        try:
            analysis = cls(**analysis_data)
            from src.extensions import db
            db.session.add(analysis)
            db.session.commit()
            return analysis, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one analysis record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find analysis records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.analysis_name.ilike(f'%{search}%') |
                cls.analysis_type.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update analysis record"""
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
