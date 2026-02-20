from sqlalchemy import Column, BigInteger, Boolean, DateTime, ForeignKey, Index, select, String
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

class ProvinceRegion(Base):
    __tablename__ = "province_region"
    __table_args__ = (  
        Index("idx_province_region_province", "province"),
        Index("idx_province_region_region", "region"),
        {"schema": "kbai"}
    )

    province = Column(String(100), nullable=False, primary_key=True)
    region = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<ProvinceRegion(province='{self.province}', region='{self.region}')>"