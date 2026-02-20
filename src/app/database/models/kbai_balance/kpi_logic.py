from sqlalchemy import Column, BigInteger, Numeric, ForeignKey, DateTime, String, func
from sqlalchemy.orm import relationship
from datetime import datetime

from src.extensions import db

Base = db.Model


class KpiLogic(Base):
    """
    KPI Logic model for storing KPI logic rules
    """
    __tablename__ = 'kpi_logic'
    __table_args__ = {'schema': 'kbai_balance'}

    id_kpi = Column(BigInteger, ForeignKey('kbai_balance.kbai_kpi_values.id_kpi'), primary_key=True)
    # Use generic NUMERIC without precision/scale so large percentages can be stored
    critical_percentage = Column(Numeric)
    acceptable_percentage = Column(Numeric)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    kpi_value = relationship('KbaiKpiValue', back_populates='kpi_logics')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_kpi': self.id_kpi,
            'critical_percentage': float(self.critical_percentage) if self.critical_percentage else None,
            'acceptable_percentage': float(self.acceptable_percentage) if self.acceptable_percentage else None,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, kpi_logic_data: dict):
        """Create a new KPI logic record"""
        try:
            kpi_logic = cls(**kpi_logic_data)
            from src.extensions import db
            db.session.add(kpi_logic)
            db.session.commit()
            return kpi_logic, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one KPI logic record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, **filters):
        """Find KPI logic records with pagination"""
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
        """Update KPI logic record"""
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
