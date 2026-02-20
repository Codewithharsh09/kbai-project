from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiKpiValue(Base):
    """
    KBAI KPI Values model for storing KPI data
    """
    __tablename__ = 'kbai_kpi_values'
    __table_args__ = {'schema': 'kbai_balance'}

    id_kpi = Column(BigInteger, primary_key=True, autoincrement=True)
    id_balance = Column(BigInteger, ForeignKey('kbai_balance.kbai_balances.id_balance'), nullable=False)
    kpi_code = Column(String(255), nullable=False)
    kpi_name = Column(String(255), nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(100))
    source = Column(String(255))
    time = Column(DateTime, default=datetime.utcnow, nullable=False)
    deviation = Column(Numeric(3, 2))
    severity = Column(String(50))
    ai_suggestions = Column(String(1000))
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    balance = relationship('KbaiBalance', back_populates='kpi_values')
    analysis_kpi_infos = relationship('AnalysisKpiInfo', back_populates='kpi_value')
    kpi_logics = relationship('KpiLogic', back_populates='kpi_value')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_kpi': self.id_kpi,
            'id_balance': self.id_balance,
            'kpi_code': self.kpi_code,
            'kpi_name': self.kpi_name,
            'value': float(self.value) if self.value else None,
            'unit': self.unit,
            'source': self.source,
            'time': self.time.isoformat() if self.time else None,
            'deviation': float(self.deviation) if self.deviation else None,
            'severity': self.severity,
            'ai_suggestions': self.ai_suggestions,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, kpi_data: dict):
        """Create a new KPI value record"""
        try:
            kpi_value = cls(**kpi_data)
            from src.extensions import db
            db.session.add(kpi_value)
            db.session.commit()
            return kpi_value, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one KPI value record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find KPI value records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.kpi_name.ilike(f'%{search}%') |
                cls.kpi_code.ilike(f'%{search}%') |
                cls.source.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update KPI value record"""
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
