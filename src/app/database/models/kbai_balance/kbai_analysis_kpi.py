from sqlalchemy import Column, BigInteger, ForeignKey, DateTime, String, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiAnalysisKpi(Base):
    """
    KBAI Analysis KPI junction model
    """
    __tablename__ = 'kbai_analysis_kpi'
    __table_args__ = {'schema': 'kbai_balance'}

    id_balance = Column(BigInteger, ForeignKey('kbai_balance.kbai_balances.id_balance'), primary_key=True)
    id_analysis = Column(BigInteger, ForeignKey('kbai_balance.kbai_analysis.id_analysis'), primary_key=True)
    kpi_list_json = Column(JSON)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    balance = relationship('KbaiBalance', back_populates='analysis_kpis')
    analysis = relationship('KbaiAnalysis', back_populates='analysis_kpis')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_balance': self.id_balance,
            'id_analysis': self.id_analysis,
            'kpi_list_json': self.kpi_list_json,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, analysis_kpi_data: dict):
        """Create a new analysis KPI record"""
        try:
            analysis_kpi = cls(**analysis_kpi_data)
            from src.extensions import db
            db.session.add(analysis_kpi)
            db.session.commit()
            return analysis_kpi, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one analysis KPI record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, **filters):
        """Find analysis KPI records with pagination"""
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
        """Update analysis KPI record"""
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
        """Soft delete analysis KPI record"""
        try:
            self.deleted_at = datetime.utcnow()
            from src.extensions import db
            db.session.commit()
            return True, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return False, str(e)
