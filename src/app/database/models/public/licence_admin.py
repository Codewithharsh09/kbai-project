from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship
from src.extensions import db

Base = db.Model


class LicenceAdmin(Base):
    __tablename__ = 'licence_admin'
    __table_args__ = {'schema': 'public'}

    id_licence = Column(BigInteger, ForeignKey('public.tb_licences.id_licence'), primary_key=True)
    id_user = Column(BigInteger, ForeignKey('public.tb_user.id_user'), primary_key=True)
    licence_code = Column(String(50))

    # Relationships
    user = relationship('TbUser', backref='licence_admins')
