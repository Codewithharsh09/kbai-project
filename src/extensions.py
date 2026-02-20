"""
Advanced Flask Extensions Configuration

This module initializes all Flask extensions with advanced configuration
for better performance, security, and functionality.

Features:
- Database with connection pooling
- JWT authentication with blacklist support
- CORS configuration
- Rate limiting
- API documentation with Flask-RESTX
- Marshmallow for serialization
- Database migrations

Author: Flask Enterprise Template
License: MIT
"""

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from flask_caching import Cache

# Database with optimized connection pooling
db = SQLAlchemy(
    engine_options={
        'pool_size': 20,                    # Maximum connections in pool
        'max_overflow': 30,                 # Additional connections
        'pool_pre_ping': True,              # Validate connections
        'pool_recycle': 3600,               # Recycle connections hourly
        'pool_timeout': 30,                 # Connection timeout
    },
    session_options={
        'expire_on_commit': False
    }
)

# Marshmallow for serialization
ma = Marshmallow()

# JWT Manager for authentication
jwt = JWTManager()

# Database migrations
migrate = Migrate()

# CORS for cross-origin requests
cors = CORS()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Cache for performance optimization
cache = Cache()

# Flask-RESTX API with Swagger documentation
api = Api(
    title='Flask Enterprise Template API',
    version='1.0',
    description='Advanced Flask REST API with JWT authentication',
    doc='/docs/',
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT Authorization header'
        }
    },
    security='Bearer Auth',
    # Disable default security headers - we set them manually
    default_mediatype='application/json',
    catch_all_404s=True
)


def init_extensions(app):
    """
    Initialize all Flask extensions with the application.
    
    Args:
        app: Flask application instance
    """
    # Initialize database
    db.init_app(app)
    
    # Initialize Marshmallow
    ma.init_app(app)
    
    # Initialize JWT
    jwt.init_app(app)
    
    # Initialize migrations
    migrate.init_app(app, db)
    
    # Initialize CORS
    cors.init_app(
        app,
        origins=app.config.get('CORS_ORIGINS', '*'),
        methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
        allow_headers=app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization']),
        expose_headers=app.config.get('CORS_EXPOSE_HEADERS', ['Authorization']),
        supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True)
    )
    
    # Initialize rate limiting
    limiter.init_app(app)
    
    # Initialize cache
    cache.init_app(app, config={
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
        'CACHE_KEY_PREFIX': app.config.get('CACHE_KEY_PREFIX', 'flask_template_')
    })
    
    # Initialize API
    api.init_app(app)
    
    # Setup JWT error handlers
    setup_jwt_error_handlers()
    
    # Setup JWT blacklist
    setup_jwt_blacklist()


def setup_jwt_error_handlers():
    """Setup JWT error handlers for better error responses"""
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'success': False,
            'message': 'Token has expired',
            'error_code': 'TOKEN_EXPIRED',
            'status_code': 401
        }, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {
            'success': False,
            'message': 'Invalid token',
            'error_code': 'INVALID_TOKEN',
            'status_code': 401
        }, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {
            'success': False,
            'message': 'Authorization header is missing or invalid',
            'error_code': 'MISSING_TOKEN',
            'status_code': 401
        }, 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return {
            'success': False,
            'message': 'Fresh token required',
            'error_code': 'FRESH_TOKEN_REQUIRED',
            'status_code': 401
        }, 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {
            'success': False,
            'message': 'Token has been revoked',
            'error_code': 'TOKEN_REVOKED',
            'status_code': 401
        }, 401


def setup_jwt_blacklist():
    """Setup JWT blacklist for token revocation"""
    
    # In a real application, you would use Redis or a database
    # For now, we'll use a simple in-memory set
    blacklisted_tokens = set()
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return jti in blacklisted_tokens
    
    def revoke_token(jti):
        """Revoke a token by adding it to the blacklist"""
        blacklisted_tokens.add(jti)
    
    def unrevoke_token(jti):
        """Remove a token from the blacklist"""
        blacklisted_tokens.discard(jti)
    
    # Make these functions available globally
    jwt.revoke_token = revoke_token
    jwt.unrevoke_token = unrevoke_token


def get_db_session():
    """
    Get a database session for manual database operations.
    
    Returns:
        SQLAlchemy session
    """
    return db.session


def get_cache_instance():
    """
    Get the cache instance for caching operations.
    
    Returns:
        Cache instance
    """
    return cache


def get_api_instance():
    """
    Get the Flask-RESTX API instance for namespace registration.
    
    Returns:
        API instance
    """
    return api


def get_limiter_instance():
    """
    Get the rate limiter instance for rate limiting operations.
    
    Returns:
        Limiter instance
    """
    return limiter
