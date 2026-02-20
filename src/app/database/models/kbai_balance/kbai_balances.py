from sqlalchemy import JSON, Column, BigInteger, SmallInteger, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiBalance(Base):
    """
    KBAI Balance model for storing company balance data
    """
    __tablename__ = 'kbai_balances'
    __table_args__ = {'schema': 'kbai_balance'}

    id_balance = Column(BigInteger, primary_key=True, autoincrement=True)
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), nullable=False)
    year = Column(SmallInteger, nullable=False)
    month = Column(SmallInteger)
    type = Column(String(255), nullable=False)
    mode = Column(String(255), nullable=False)
    file = Column(Text)
    note = Column(Text)
    balance = Column(JSON, nullable=True)  # Store extracted JSON data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime)

    # Relationships
    company = relationship('KbaiCompany', backref='balances')
    kpi_values = relationship('KbaiKpiValue', back_populates='balance')
    analysis_kpis = relationship('KbaiAnalysisKpi', back_populates='balance')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_balance': self.id_balance,
            'id_company': self.id_company,
            'year': self.year,
            'month': self.month,
            'type': self.type,
            'mode': self.mode,
            'file': self.file,
            'note': self.note,
            'balance': self.balance,  # JSONB field
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, balance_data: dict):
        """Create a new balance record"""
        try:
            balance = cls(**balance_data)
            from src.extensions import db
            db.session.add(balance)
            db.session.commit()
            return balance, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one balance record by filters"""
        return cls.query.filter_by(**filters, is_deleted=False).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find balance records with pagination"""
        query = cls.query.filter_by(is_deleted=False)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.note.ilike(f'%{search}%') |
                cls.type.ilike(f'%{search}%') |
                cls.mode.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update balance record"""
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
        """Soft delete balance record"""
        try:
            self.is_deleted = True
            self.deleted_at = datetime.utcnow()
            from src.extensions import db
            db.session.commit()
            return True, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return False, str(e)
