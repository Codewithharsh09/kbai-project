from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey, Boolean, SmallInteger, or_, desc, select, ARRAY, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError
from src.extensions import db
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

Base = db.Model


# ----------------------------------------------------------------------------
# Users table
# ----------------------------------------------------------------------------
class TbUser(Base):
    __tablename__ = 'tb_user'
    __table_args__ = {'schema': 'public'}

    id_user = Column(BigInteger, primary_key=True, autoincrement=True)
    id_admin = Column(BigInteger, ForeignKey('public.tb_user.id_user'), nullable=True)  # Direct creator
    password = Column(Text, nullable=True)  # Allow NULL for Auth0 users
    email = Column(String(255), unique=True, index=True)
    role = Column(String(64), default='user')  # superadmin, admin, manager, staff, user
    name = Column(String(120))
    username=Column(String(120))
    surname = Column(String(120))
    company_name = Column(String(100))
    phone = Column(String(50))
    language = Column(String(10), default='en')
    premium_licenses_1 = Column(SmallInteger, default=0)
    premium_licenses_2 = Column(SmallInteger, default=0)
    status = Column(String(32), default='ACTIVE')  # ACTIVE, INACTIVE, SUSPENDED
    is_verified = Column(Boolean, default=False)
    mfa = Column(Boolean, default=False)  # Multi-Factor Authentication enabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Auth0 integration
    auth0_user_id = Column(String(255), unique=True, nullable=True, index=True)
    auth0_metadata = Column(JSONB, nullable=True)

    # Relationships
    admin = relationship('TbUser', remote_side=[id_user], foreign_keys=[id_admin], backref='subordinates')
    user_companies = relationship('TbUserCompany', back_populates='user')

    def is_super_admin(self):
        """Check if user is super admin"""
        return self.role.lower() == 'superadmin'

    def is_admin(self):
        """Check if user is admin or super admin"""
        return self.role.lower() in ['superadmin', 'admin']

    def to_dict(self):
        """Convert to dictionary (excluding sensitive data)"""
        return {
            'id_user': self.id_user,
            'id_admin': self.id_admin,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'username':self.username,
            'surname': self.surname,
            'language': self.language,
            'status': self.status,
            'is_verified': self.is_verified,
            'mfa': self.mfa,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'auth0_user_id': self.auth0_user_id,
            'company_name': self.company_name,
            'phone': self.phone,
            'premium_licenses_1': self.premium_licenses_1,
            'premium_licenses_2': self.premium_licenses_2
        }

    # --------------------------------------------------------------------------
    # Create a user
    # --------------------------------------------------------------------------
    @classmethod
    def create(cls, user_data: Dict[str, Any]) -> Tuple[Optional['TbUser'], str]:
        """
        Create a new user
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            Tuple of (created_user, error_message)
        """
        try:
            # Check if email already exists
            existing_user = cls.query.filter_by(email=user_data['email']).first()
            if existing_user:
                return None, "Email already exists"
            
            # Create new user
            user = cls(
                email=user_data['email'],
                name=user_data.get('name'),
                surname=user_data.get('surname'),
                role=user_data.get('role', 'user'),
                company_name=user_data.get('company_name'),
                phone=user_data.get('phone'),
                language=user_data.get('language', 'en'),
                status=user_data.get('status', 'ACTIVE'),
                is_verified=user_data.get('is_verified', False),
                id_admin=user_data.get('created_by'),
                auth0_user_id=user_data.get('auth0_user_id'),
                auth0_metadata=user_data.get('auth0_metadata')
            )
            
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            
            return user, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error creating user: {str(e)}"
    
    # ---------------------------------------------------------------------------
    # Find one user
    # ---------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['TbUser']:
        """
        Find one user by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com', id_user=1, etc.
            
        Returns:
            User instance or None (full object when no select_columns)
            
        Examples:
            TbUser.findOne(email='test@example.com')
            TbUser.findOne(select_columns=['id_user', 'email', 'role'], id_user=1)
            TbUser.findOne(auth0_user_id='auth0|123')
        """
        try:
            # If no select_columns, use query (returns full TbUser object)
            if not select_columns:
                query = cls.query
                for key, value in filters.items():
                    if hasattr(cls, key):
                        query = query.filter(getattr(cls, key) == value)
                return query.first()
            
            # If select_columns provided, use select statement (returns Row/tuple)
            columns = []
            for col_name in select_columns:
                if hasattr(cls, col_name):
                    columns.append(getattr(cls, col_name))
            
            if not columns:
                return None
            
            stmt = select(*columns)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(cls, key):
                    stmt = stmt.where(getattr(cls, key) == value)
            
            result = db.session.execute(stmt).first()
            return result
        except Exception:
            return None
    
    # -------------------------------------------------------------------------
    # Update a user
    # -------------------------------------------------------------------------
    def update(self, update_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Update user information
        
        Args:
            update_data: Dictionary containing fields to update
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Update fields if provided (email is NOT allowed to be updated)
            allowed_fields = [
                'name', 'surname', 'company_name', 'phone', 'language', 'status', 'is_verified', 'mfa', 'premium_licenses_1', 'premium_licenses_2'
            ]
            
            for field in allowed_fields:
                if field in update_data:
                    setattr(self, field, update_data[field])
            
            # Update timestamp
            self.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating user: {str(e)}"
    
    # -----------------------------------------------------------------------
    # Delete a user
    # -----------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Soft delete user (set status to deleted)
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.status = 'Deleted'
            self.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting user: {str(e)}"
    
    # -------------------------------------------------------------------------
    # Find users with pagination
    # -------------------------------------------------------------------------
    @classmethod
    def find(cls, page: int = 1, per_page: int = 10, search: str = None, select_columns=None, **filters) -> Tuple[List['TbUser'], int, str]:
        """
        Find users with filtering and pagination
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for email, name, or surname
            select_columns: List of column names to select (optional)
            **filters: Field filters like role='admin', status='ACTIVE', etc.
            
        Returns:
            Tuple of (users_list, total_count, error_message)
            
        Examples:
            TbUser.find()  # Get all users (TbUser objects)
            TbUser.find(select_columns=['id_user', 'email', 'name'], page=1)  # Row objects
            TbUser.find(role='admin', status='ACTIVE')
            TbUser.find(search='john')
            TbUser.find(id_admin=5)  # All users created by admin with id=5
        """
        try:
            # If no select_columns, use query (returns TbUser objects)
            if not select_columns:
                query = cls.query
                
                # Apply standard filters (support IN when value is list/tuple/set)
                for key, value in filters.items():
                    if hasattr(cls, key):
                        column = getattr(cls, key)
                        if isinstance(value, (list, tuple, set)):
                            query = query.filter(column.in_(list(value)))
                        else:
                            query = query.filter(column == value)
                
                # Apply search filter
                if search:
                    query = query.filter(
                        or_(
                            cls.email.ilike(f'%{search}%'),
                            cls.name.ilike(f'%{search}%'),
                            cls.surname.ilike(f'%{search}%')
                        )
                    )
                
                # Sort by latest created first
                query = query.order_by(desc(cls.created_at))
                
                # Get total count
                total = query.count()
                
                # Get paginated results
                offset = (page - 1) * per_page
                users = query.offset(offset).limit(per_page).all()
                
                return users, total, None
            
            # If select_columns provided, use select statement (returns Row objects)
            columns = []
            for col_name in select_columns:
                if hasattr(cls, col_name):
                    columns.append(getattr(cls, col_name))
            
            if not columns:
                return [], 0, None
            
            stmt = select(*columns)
            
            # Apply standard filters (support IN when value is list/tuple/set)
            for key, value in filters.items():
                if hasattr(cls, key):
                    column = getattr(cls, key)
                    if isinstance(value, (list, tuple, set)):
                        stmt = stmt.where(column.in_(list(value)))
                    else:
                        stmt = stmt.where(column == value)
            
            # Apply search filter
            if search:
                stmt = stmt.where(
                    or_(
                        cls.email.ilike(f'%{search}%'),
                        cls.name.ilike(f'%{search}%'),
                        cls.surname.ilike(f'%{search}%')
                    )
                )
            
            # Sort by latest created first
            stmt = stmt.order_by(desc(cls.created_at))
            
            # Get total count
            count_stmt = select(cls)
            for key, value in filters.items():
                if hasattr(cls, key):
                    column = getattr(cls, key)
                    if isinstance(value, (list, tuple, set)):
                        count_stmt = count_stmt.where(column.in_(list(value)))
                    else:
                        count_stmt = count_stmt.where(column == value)
            if search:
                count_stmt = count_stmt.where(
                    or_(
                        cls.email.ilike(f'%{search}%'),
                        cls.name.ilike(f'%{search}%'),
                        cls.surname.ilike(f'%{search}%')
                    )
                )
            total = db.session.execute(count_stmt).scalar()
            
            # Get paginated results
            offset = (page - 1) * per_page
            stmt = stmt.offset(offset).limit(per_page)
            result = db.session.execute(stmt).all()
            
            return result, total, None
            
        except Exception as e:
            return [], 0, f"Error listing users: {str(e)}"



# ------------------------------------------------------------------------------
# Temporary user data table
# ------------------------------------------------------------------------------
class UserTempData(Base):
    """Temporary user data table for storing unverified user information"""
    __tablename__ = 'user_temp_data'
    __table_args__ = {'schema': 'public'}

    email = Column(String(255), primary_key=True)
    name = Column(String(100))
    surname = Column(String(100))
    company_name = Column(String(100))
    number_licences = Column(SmallInteger)
    premium_licenses_1 = Column(SmallInteger)
    premium_licenses_2 = Column(SmallInteger)
    phone = Column(String(50))
    language = Column(String(10))
    id_user = Column(BigInteger, ForeignKey('public.tb_user.id_user'), nullable=True)  # Direct creator (admin)
    companies = Column(ARRAY(Integer), nullable=True)  # Array of company IDs to assign

    # No relationships - UserTempData is temporary and deleted after first login

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'email': self.email,
            'name': self.name,
            'surname': self.surname,
            'company_name': self.company_name,
            'number_licences': self.number_licences,
            'premium_licenses_1': self.premium_licenses_1,
            'premium_licenses_2': self.premium_licenses_2,
            'phone': self.phone,
            'language': self.language,
            'id_user': self.id_user,
            'companies': self.companies,
        }
    
    # --------------------------------------------------------------------------
    # Create a temp data
    # --------------------------------------------------------------------------
    @classmethod
    def create_or_update(cls, temp_data: Dict[str, Any]) -> Tuple[Optional['UserTempData'], str]:
        """
        Create or update temp user data (upsert pattern)
        
        Args:
            temp_data: Dictionary containing temp user information
            
        Returns:
            Tuple of (temp_data_record, error_message)
        """
        try:
            # Check if temp data already exists
            existing = cls.query.filter_by(email=temp_data['email']).first()
            
            if existing:
                # Update existing record
                existing.name = temp_data.get('name', existing.name)
                existing.surname = temp_data.get('surname', existing.surname)
                existing.company_name = temp_data.get('company_name', existing.company_name)
                existing.number_licences = temp_data.get('number_licences', existing.number_licences)
                existing.premium_licenses_1 = temp_data.get('premium_licenses_1', existing.premium_licenses_1)
                existing.premium_licenses_2 = temp_data.get('premium_licenses_2', existing.premium_licenses_2)
                existing.phone = temp_data.get('phone', existing.phone)
                existing.language = temp_data.get('language', existing.language)
                existing.id_user = temp_data.get('id_user', existing.id_user)
                existing.companies = temp_data.get('companies', existing.companies)
                
                db.session.commit()
                return existing, None
            else:
                # Create new record
                temp_record = cls(
                    email=temp_data['email'],
                    name=temp_data.get('name'),
                    surname=temp_data.get('surname'),
                    company_name=temp_data.get('company_name'),
                    number_licences=temp_data.get('number_licences', 0),
                    premium_licenses_1=temp_data.get('premium_licenses_1', 0),
                    premium_licenses_2=temp_data.get('premium_licenses_2', 0),
                    phone=temp_data.get('phone'),
                    language=temp_data.get('language', 'en'),
                    id_user=temp_data.get('id_user'),
                    companies=temp_data.get('companies')
                )
                
                db.session.add(temp_record)
                db.session.commit()
                db.session.refresh(temp_record)
                
                return temp_record, None
                
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"Error saving temp data: {str(e)}"
    
    # --------------------------------------------------------------------------
    # Find a temp data
    # --------------------------------------------------------------------------
    @classmethod
    def findOne(cls, select_columns=None, **filters) -> Optional['UserTempData']:
        """
        Find one temp user data record by any field(s)
        
        Args:
            select_columns: List of column names to select (optional)
            **filters: Field filters like email='test@example.com'
            
        Returns:
            UserTempData instance or None
            
        Examples:
            UserTempData.findOne(email='test@example.com')
            UserTempData.findOne(select_columns=['email', 'name'], id_user=1)
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
            
            result = db.session.execute(stmt).first()
            return result
        except Exception:
            return None
    
    # ---------------------------------------------------------------------------
    # Delete a temp data
    # ---------------------------------------------------------------------------
    def delete(self) -> Tuple[bool, str]:
        """
        Delete temp user data (hard delete)
        
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
            return False, f"Error deleting temp data: {str(e)}"


__all__ = [
    'TbLicences',
    'LicenceAdmin',
    'TbUser',
    'TbUserCompany',
    'UserTempData',
]
