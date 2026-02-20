"""
KBAI Sector Model

Represents business sectors/industries.
Each sector has section and division information and can be associated with multiple companies.
"""

from sqlalchemy import Column, BigInteger, String, Text, DateTime, SmallInteger, Index, select, or_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Sectors
# --------------------------------------------------------------------------
class KbaiSector(Base):
    __tablename__ = 'kbai_sectors'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_sectors_section', 'section'),
        Index('idx_kbai_sectors_division', 'division'),
        Index('idx_kbai_sectors_region', 'region'),
        {'schema': 'kbai'}
    )
    # Primary Key
    id_sector = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Relationship to KbaiThreshold (one sector can have many thresholds)
    thresholds = relationship('KbaiThreshold', back_populates='sector')

    # Sector Information
    section = Column(String, nullable=True)
    section_description = Column(Text, nullable=True)
    division = Column(String, nullable=True)
    region = Column(String, nullable=True)
    year = Column(SmallInteger, nullable=True)
    geographic_area = Column(SmallInteger, nullable=True)

    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_sector': self.id_sector,
            'section': self.section,
            'section_description': self.section_description,
            'division': self.division,
            'region': self.region,
            'year': self.year,
            'geographic_area': self.geographic_area,
        }

    # --------------------------------------------------------------------------
    # Create a new sector
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, sector_data: Dict[str, Any]) -> Tuple[Optional['KbaiSector'], str]:
        """
        Create a new sector

        Args:
            sector_data: Dictionary containing sector information

        Returns:
            Tuple of (created_sector, error_message)
        """
        try:
            now = datetime.utcnow()
            sector = cls(
                section=sector_data.get('section'),
                section_description=sector_data.get('section_description'),
                    division=sector_data.get('division'),
                    region=sector_data.get('region'),
                    year=sector_data.get('year'),
                    geographic_area=sector_data.get('geographic_area'),
                created_at=now,
                updated_at=now
            )

            db.session.add(sector)
            db.session.commit()

            return sector, None

        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating sector: {str(e)}"

    # ------------------------------------------------------------------------------
    # Get a sector by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiSector']:
        """
        Find one sector by any field(s)

        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like section='A', id_sector=1, etc.

        Returns:
            Sector instance or None
        """
        try:
            if select_columns:
                columns = []
                for col_name in select_columns:
                    if hasattr(cls, col_name):
                        columns.append(getattr(cls, col_name))
                if columns:
                    stmt = select(*columns)
                else:
                    stmt = select(cls)
            else:
                stmt = select(cls)

            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)

            result = db.session.execute(stmt).first()
            return result
        except Exception:
            return None

    # ------------------------------------------------------------------------------
    # Update sector information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update sector information

        Args:
            update_data: Dictionary containing fields to update

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if 'section' in update_data:
                self.section = update_data['section']
            if 'section_description' in update_data:
                self.section_description = update_data['section_description']
            if 'division' in update_data:
                self.division = update_data['division']
            if 'region' in update_data:
                self.region = update_data['region']
            if 'year' in update_data:
                self.year = update_data['year']
            if 'geographic_area' in update_data:
                self.geographic_area = update_data['geographic_area']

            self.updated_at = datetime.utcnow()

            db.session.commit()
            return True, None

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating sector: {str(e)}"

    # -----------------------------------------------------------------------------
    # Delete sector
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete sector (hard delete)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True, None

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting sector: {str(e)}"

    # -----------------------------------------------------------------------------
    # Find sectors with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None,
             select_columns=None, **filters) -> Tuple[List['KbaiSector'], int, str]:
        """
        Find sectors with filtering and pagination

        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for section or division
            select_columns: List of column names to select (optional)
            **filters: Field filters

        Returns:
            Tuple of (sectors_list, total_count, error_message)
        """
        try:
            if select_columns:
                columns = []
                for col_name in select_columns:
                    if hasattr(cls, col_name):
                        columns.append(getattr(cls, col_name))
                if columns:
                    stmt = select(*columns)
                else:
                    stmt = select(cls)
            else:
                stmt = select(cls)

            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)

            if search:
                stmt = stmt.where(
                    or_(
                        cls.section.ilike(f'%{search}%'),
                        cls.division.ilike(f'%{search}%'),
                        cls.section_description.ilike(f'%{search}%')
                    )
                )

            stmt = stmt.order_by(desc(cls.created_at))

            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            if search:
                count_stmt = count_stmt.where(
                    or_(
                        cls.section.ilike(f'%{search}%'),
                        cls.division.ilike(f'%{search}%'),
                        cls.section_description.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).rowcount

            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()

            return result, total, None

        except Exception as e:
            return [], 0, f"Error listing sectors: {str(e)}"