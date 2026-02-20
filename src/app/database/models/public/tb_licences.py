from sqlalchemy import Column, BigInteger, String, DateTime, Date
from sqlalchemy.orm import relationship
from src.extensions import db
from datetime import datetime

Base = db.Model


class TbLicences(Base):
    __tablename__ = 'tb_licences'
    __table_args__ = {'schema': 'public'}

    id_licence = Column(BigInteger, primary_key=True, autoincrement=True)
    licence_token = Column(String(255), nullable=False)
    time = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(Date)
    type = Column(String(50))

    # Relationships
    licence_admins = relationship('LicenceAdmin', backref='licence')
