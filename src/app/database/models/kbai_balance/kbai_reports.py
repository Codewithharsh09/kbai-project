from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from datetime import datetime

from src.extensions import db

Base = db.Model


class KbaiReport(Base):
    """
    KBAI Reports model for storing report data
    """
    __tablename__ = 'kbai_reports'
    __table_args__ = {'schema': 'kbai_balance'}

    id_report = Column(BigInteger, primary_key=True, autoincrement=True)
    id_analysis = Column(BigInteger, ForeignKey('kbai_balance.kbai_analysis.id_analysis'), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    time = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_path = Column(Text)
    export_format = Column(String(100))
    parent_report_id = Column(BigInteger, ForeignKey('kbai_balance.kbai_reports.id_report'), nullable=True)
    # created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # is_deleted = Column(String(1), default='N', nullable=False)
    # deleted_at = Column(DateTime)

    # Relationships
    analysis = relationship('KbaiAnalysis', back_populates='reports')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id_report': self.id_report,
            'id_analysis': self.id_analysis,
            'name': self.name,
            'type': self.type,
            'time': self.time.isoformat() if self.time else None,
            'file_path': self.file_path,
            'export_format': self.export_format,
            'parent_report_id': self.parent_report_id,
            # 'created_at': self.created_at.isoformat() if self.created_at else None,
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # 'is_deleted': self.is_deleted,
            # 'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    @classmethod
    def create(cls, report_data: dict):
        """Create a new report record"""
        try:
            report = cls(**report_data)
            from src.extensions import db
            db.session.add(report)
            db.session.commit()
            return report, None
        except Exception as e:
            from src.extensions import db
            db.session.rollback()
            return None, str(e)

    @classmethod
    def findOne(cls, **filters):
        """Find one report record by filters"""
        return cls.query.filter_by(**filters).first()

    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, **filters):
        """Find report records with pagination"""
        query = cls.query.filter_by()
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        
        # Apply search
        if search:
            query = query.filter(
                cls.name.ilike(f'%{search}%') |
                cls.type.ilike(f'%{search}%') |
                cls.export_format.ilike(f'%{search}%')
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()
        
        return records, total, None

    def update(self, update_data: dict):
        """Update report record"""
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
