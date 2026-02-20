from sqlalchemy import Column, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.extensions import db
from datetime import datetime

Base = db.Model


class TbUserCompany(Base):
    __tablename__ = 'tb_user_company'
    __table_args__ = {'schema': 'public'}

    id_user = Column(BigInteger, ForeignKey('public.tb_user.id_user'), primary_key=True)
    id_company = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), primary_key=True)
    date_assigned = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('TbUser', back_populates='user_companies')
    company = relationship('KbaiCompany', backref='users_assigned')
