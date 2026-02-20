from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey, or_, desc, Index, select
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

Base = db.Model

# --------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------
class KbaiCompany(Base):
    __tablename__ = 'kbai_companies'
    __table_args__ = (
        # Performance indexes for fast queries
        Index('idx_kbai_companies_company_name', 'company_name'),
        Index('idx_kbai_companies_email', 'email'),
        # Soft delete index for fast filtering
        Index('idx_kbai_companies_is_deleted', 'is_deleted'),
        # Composite index for common queries
        Index('idx_kbai_companies_active_created', 'is_deleted', 'created_at'),
        {'schema': 'kbai'}
    )

    # Primary Key
    id_company = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign Key to tb_licences (unique)
    id_licence = Column(BigInteger, ForeignKey('public.tb_licences.id_licence'), unique=True, nullable=False)
    
    # Company Information
    company_name = Column(String, nullable=True)
    vat = Column(String, nullable=True)
    fiscal_code = Column(String, nullable=True)
    sdi = Column(String, nullable=True)
    logo = Column(String, nullable=True)  # Text field for logo URL/path
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    status_flag = Column(String, nullable=True,default="ACTIVE")
    is_competitor = Column(Boolean, default=False)
    parent_company_id = Column(BigInteger, ForeignKey('kbai.kbai_companies.id_company'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Soft delete fields
    is_deleted = Column(Boolean, default=False, nullable=False)  # Fast query filtering
    deleted_at = Column(DateTime, nullable=True)  # Audit trail and recovery

    # Relationships
    licence = relationship('TbLicences', backref='kbai_company')
    # KBAI Schema Relationships
    company_zones = relationship('KbaiCompanyZone', back_populates='company')
    company_sectors = relationship('KbaiCompanySector', back_populates='company')
    company_states = relationship('KbaiState', back_populates='company')
    pre_dashboard = relationship('KbaiPreDashboard', back_populates='company', uselist=False)
    
    # --------------------------------------------------------------------------
    # Convert to json format
    # --------------------------------------------------------------------------
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id_company': self.id_company,
            'id_licence': self.id_licence,
            'company_name': self.company_name,
            'vat': self.vat,
            'fiscal_code': self.fiscal_code,
            'sdi': self.sdi,
            'logo': self.logo,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'status_flag': self.status_flag,
            'is_competitor': self.is_competitor,
            'parent_company_id': self.parent_company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    # --------------------------------------------------------------------------
    # Create a new company
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, company_data: Dict[str, Any]) -> Tuple[Optional['KbaiCompany'], str]:
        """
        Create a new company
        
        Args:
            company_data: Dictionary containing company information
            
        Returns:
            Tuple of (created_company, error_message)
        """
        try:
            # Create new company
            now = datetime.utcnow()
            company = cls(
                id_licence=company_data['id_licence'],
                company_name=company_data['company_name'],
                vat=company_data.get('vat'),
                fiscal_code=company_data.get('fiscal_code'),
                sdi=company_data.get('sdi'),
                logo=company_data.get('logo'),
                contact_person=company_data.get('contact_person'),
                phone=company_data.get('phone'),
                email=company_data.get('email'),
                website=company_data.get('website'),
                status_flag=company_data.get('status_flag', 'ACTIVE'),
                is_competitor=bool(company_data.get('is_competitor', False)),
                parent_company_id=company_data.get('parent_company_id'),
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            
            db.session.add(company)
            db.session.commit()  # Get the company ID before committing
            
            # Auto-create pre_dashboard record for the new company using the create method
            if not company_data.get('is_competitor', False):
                from .kbai_pre_dashboard import KbaiPreDashboard
                pre_dashboard, error = KbaiPreDashboard.create({
                    'id_company': company.id_company
                })
                if error:
                    return None, f"Error creating pre-dashboard: {error}"
            return company, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating company: {str(e)}"
    
    # ------------------------------------------------------------------------------
    # Get a company by any field
    # ------------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['KbaiCompany']:
        """
        Find one company by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com', id_company=1, etc.
            
        Returns:
            Company instance or None
            
        Examples:
            KbaiCompany.findOne(email='test@example.com')
            KbaiCompany.findOne(select_columns=['id_company', 'company_name', 'email'], id_company=1)
            KbaiCompany.findOne(id_licence=1, status_flag='ACTIVE')
        """
        try:
            if select_columns:
                # Convert column names to actual column objects
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
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)
            
            result = db.session.execute(stmt).scalars().first()
            return result
        except Exception:
            return None
    
    # ------------------------------------------------------------------------------
    # Update company information
    # ------------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update company information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided
            if 'company_name' in update_data:
                self.company_name = update_data['company_name']
            if 'vat' in update_data:
                self.vat = update_data['vat']
            if 'fiscal_code' in update_data:
                self.fiscal_code = update_data['fiscal_code']
            if 'sdi' in update_data:
                self.sdi = update_data['sdi']
            if 'logo' in update_data:
                self.logo = update_data['logo']
            if 'contact_person' in update_data:
                self.contact_person = update_data['contact_person']
            if 'phone' in update_data:
                self.phone = update_data['phone']
            if 'email' in update_data:
                self.email = update_data['email']
            if 'website' in update_data:
                self.website = update_data['website']
            if 'status_flag' in update_data:
                self.status_flag = update_data['status_flag']
            if 'is_competitor' in update_data:
                self.is_competitor = update_data['is_competitor']
            
            # Update timestamp
            self.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating company: {str(e)}"
    
    # -----------------------------------------------------------------------------
    # Delete company information
    # -----------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Soft delete company (set deleted_at timestamp)
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Soft delete - set both fields for fast queries and audit trail
            now = datetime.utcnow()
            self.is_deleted = True
            self.deleted_at = now
            self.updated_at = now
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting company: {str(e)}"
    
    
    # -----------------------------------------------------------------------------
    # Find companies with filtering and pagination
    # -----------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, select_columns=None, **filters) -> Tuple[List['KbaiCompany'], int, str]:
        """
        Find companies with filtering and pagination (always sorted by latest first)
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for company name, contact person, or email
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com', id_licence=1, status_flag='ACTIVE', etc.
            
        Returns:
            Tuple of (companies_list, total_count, error_message)
            
        Examples:
            KbaiCompany.find()  # Get all companies (latest first)
            KbaiCompany.find(select_columns=['id_company', 'company_name', 'email'], page=1, per_page=20)
            KbaiCompany.find(email='test@example.com')  # Filter by email
            KbaiCompany.find(id_licence=1, status_flag='ACTIVE')  # Multiple filters
            KbaiCompany.find(search='Tech')  # Search in company name
        """
        try:
            # Build select statement
            if select_columns:
                # Convert column names to actual column objects
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
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)
            
            # Apply search filter if provided
            if search:
                # Use indexed columns for faster search
                stmt = stmt.where(
                    or_(
                        cls.company_name.ilike(f'%{search}%'),
                        cls.contact_person.ilike(f'%{search}%'),
                        cls.email.ilike(f'%{search}%')
                    )
                )
            
            # Always sort by latest created first (created_at desc)
            stmt = stmt.order_by(desc(cls.created_at))
            
            # Get total count (without column selection for accurate count)
            from sqlalchemy import func
            count_stmt = select(func.count(cls.id_company))
            for key, value in filters.items():
                if hasattr(cls, key):
                    count_stmt = count_stmt.where(getattr(cls, key) == value)
            if search:
                count_stmt = count_stmt.where(
                    or_(
                        cls.company_name.ilike(f'%{search}%'),
                        cls.contact_person.ilike(f'%{search}%'),
                        cls.email.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).scalar()
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            
            if select_columns:
                # When using select_columns, we get Row objects
                result = db.session.execute(stmt).all()
            else:
                # When selecting full objects, use scalars() to get KbaiCompany objects
                result = db.session.scalars(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing companies: {str(e)}"
    
    