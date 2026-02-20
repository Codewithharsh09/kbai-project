"""
KBAI Zone Model

Represents geographical zones/locations for companies.
Each zone has address information and can be associated with multiple companies.
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Index, select, or_, desc
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model

# --------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------
class KbaiZone(Base):
    __tablename__ = 'kbai_zone'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_zone_city', 'city'),
        Index('idx_kbai_zone_region', 'region'),
        Index('idx_kbai_zone_country', 'country'),
        {'schema': 'kbai'}
    )

    # Primary Key
    id_zone = Column(BigInteger, primary_key=True, autoincrement=True)

    # Zone Information
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_zone': self.id_zone,
            'address': self.address,
            'city': self.city,
            'region': self.region,
            'country': self.country,
            'postal_code': self.postal_code
        }

    # --------------------------------------------------------------------------
    # Create a new zone
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, zone_data: Dict[str, Any]) -> Tuple[Optional['KbaiZone'], str]:
        """
        Create a new zone

        Args:
            zone_data: Dictionary containing zone information

        Returns:
            Tuple of (created_zone, error_message)
        """
        try:
            now = datetime.utcnow()
            zone = cls(
                address=zone_data.get('address'),
                city=zone_data.get('city'),
                region=zone_data.get('region'),
                country=zone_data.get('country'),
                postal_code=zone_data.get('postal_code'),
                # created_at=now,
                # updated_at=now
            )

            db.session.add(zone)
            db.session.commit()

            return zone, None

        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating zone: {str(e)}"

    # ------------------------------------------------------------------------------
    # Get a zone by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiZone']:
        """
        Find one zone by any field(s)

        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like city='Rome', id_zone=1, etc.

        Returns:
            Zone instance or None
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
    # Update zone information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update zone information

        Args:
            update_data: Dictionary containing fields to update

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if 'address' in update_data:
                self.address = update_data['address']
            if 'city' in update_data:
                self.city = update_data['city']
            if 'region' in update_data:
                self.region = update_data['region']
            if 'country' in update_data:
                self.country = update_data['country']
            if 'postal_code' in update_data:
                self.postal_code = update_data['postal_code']

            self.updated_at = datetime.utcnow()

            db.session.commit()
            return True, None

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating zone: {str(e)}"

    # -----------------------------------------------------------------------------
    # Delete zone
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete zone (hard delete)

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
            return False, f"Error deleting zone: {str(e)}"

    # -----------------------------------------------------------------------------
    # Find zones with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None,
             select_columns=None, **filters) -> Tuple[List['KbaiZone'], int, str]:
        """
        Find zones with filtering and pagination

        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for city, region, or country
            select_columns: List of column names to select (optional)
            **filters: Field filters

        Returns:
            Tuple of (zones_list, total_count, error_message)
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
                        cls.city.ilike(f'%{search}%'),
                        cls.region.ilike(f'%{search}%'),
                        cls.country.ilike(f'%{search}%')
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
                        cls.city.ilike(f'%{search}%'),
                        cls.region.ilike(f'%{search}%'),
                        cls.country.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).rowcount

            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()

            return result, total, None

        except Exception as e:
            return [], 0, f"Error listing zones: {str(e)}"