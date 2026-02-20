from sqlalchemy import Column, BigInteger, Text, ForeignKey, DateTime, String, func
from sqlalchemy.orm import relationship
from datetime import datetime

from src.extensions import db

Base = db.Model


class AnalysisKpiInfo(Base):
    """
    Analysis KPI Info model for storing KPI analysis information
    """
    __tablename__ = 'analysis_kpi_info'
    __table_args__ = {'schema': 'kbai_balance'}

    id_analysis = Column(BigInteger, ForeignKey('kbai_balance.kbai_analysis.id_analysis'), primary_key=True)
    id_kpi = Column(BigInteger, ForeignKey('kbai_balance.kbai_kpi_values.id_kpi'), primary_key=True)
    synthesis = Column(Text)
    suggestion = Column(Text)
    note = Column(Text)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    analysis = relationship('KbaiAnalysis', back_populates='analysis_kpi_infos')
    kpi_value = relationship('KbaiKpiValue', back_populates='analysis_kpi_infos')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_analysis': self.id_analysis,
            'id_kpi': self.id_kpi,
            'synthesis': self.synthesis,
            'suggestion': self.suggestion,
            'note': self.note,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, analysis_kpi_info_data: dict):
        """Create a new analysis KPI info record"""
        try:
            analysis_kpi_info = cls(**analysis_kpi_info_data)
            from src.extensions import db
            db.session.add(analysis_kpi_info)
            db.session.commit()
            return analysis_kpi_info, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one analysis KPI info record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find analysis KPI info records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.synthesis.ilike(f'%{search}%') |
                cls.suggestion.ilike(f'%{search}%') |
                cls.note.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update analysis KPI info record"""
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
