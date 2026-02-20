"""
OTP Model for 2-Step Verification and Password Reset
Stores temporary OTPs and password reset tokens with auto-expiry
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Index
from src.extensions import db
from datetime import datetime, timedelta
import secrets
import hashlib

Base = db.Model


class TbOtp(Base):
    """OTP table for 2-step verification and password reset"""
    __tablename__ = 'tb_otp'
    __table_args__ = {'schema': 'public'}

    id_otp = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    otp = Column(String(6), nullable=True)  # 6-digit OTP (nullable for password reset)
    token_hash = Column(String(255), nullable=True, index=True)  # For password reset tokens
    expires_at = Column(DateTime, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, email: str, otp: str = None, token_hash: str = None, expires_in_minutes: int = 10):
        """Initialize OTP or password reset token with auto-expiry"""
        self.email = email
        self.otp = otp
        self.token_hash = token_hash
        self.expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        self.is_used = False
    
    def is_expired(self) -> bool:
        """Check if OTP is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if OTP is valid (not expired and not used)"""
        return not self.is_expired() and not self.is_used
    
    def mark_as_used(self):
        """Mark OTP as used"""
        self.is_used = True
    
    def to_dict(self):
        """Convert to dictionary (excluding sensitive data)"""
        return {
            'id_otp': self.id_otp,
            'email': self.email,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_used': self.is_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_valid': self.is_valid()
        }
    
    @classmethod
    def cleanup_expired(cls):
        """Clean up expired OTPs"""
        try:
            # Use bulk delete for performance; avoids per-row DELETE overhead
            delete_query = cls.query.filter(cls.expires_at < datetime.utcnow())
            deleted_count = delete_query.delete(synchronize_session=False)
            db.session.commit()
            return int(deleted_count)
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def get_valid_otp(cls, email: str, otp: str):
        """Get valid OTP for email and code"""
        return cls.query.filter(
            cls.email == email,
            cls.otp == otp,
            cls.is_used == False,
            cls.expires_at > datetime.utcnow()
        ).first()
    
    @classmethod
    def get_valid_token(cls, token_hash: str):
        """Get valid password reset token"""
        return cls.query.filter(
            cls.token_hash == token_hash,
            cls.is_used == False,
            cls.expires_at > datetime.utcnow()
        ).first()
    
    @staticmethod
    def generate_secure_token(length: int = 64) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token using SHA-256"""
        return hashlib.sha256(token.encode()).hexdigest()


__all__ = ['TbOtp']
