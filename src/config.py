"""
Advanced Flask Enterprise Backend Template - Configuration Management

This module handles environment-based configuration for development,
testing, and production environments with advanced features including:
- Database connection pooling
- Advanced security settings
- Performance monitoring
- Health monitoring
- Rate limiting
- Caching configuration

Author: Flask Enterprise Template
License: MIT
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class with advanced settings"""

    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'

    # Advanced Database Configuration with Connection Pooling
    DATABASE_URL = os.environ.get('DATABASE_URL_DB') or os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DB') or os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Database Performance Optimization
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 20)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 30)),
        'pool_pre_ping': True,
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
    }

    # Advanced JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-dev-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 30)))  # 30 days
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # Email Configuration
    GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS')
    GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    MAIL_FROM_NAME = os.environ.get('MAIL_FROM_NAME', 'KBAI Platform')
    MAIL_CC_EMAIL = os.environ.get('MAIL_CC_EMAIL')
    
    #file upload config
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    AWS_S3_BUCKET_NAME = os.environ.get('AWS_S3_BUCKET_NAME')
    
    # Frontend URL Configuration
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

    # AI Services Configuration (Optional)
    OPENAI_KEY = os.environ.get('OPENAI_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4')

    # Auth0 Configuration
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')
    AUTH0_REDIRECT_URI = os.environ.get('AUTH0_REDIRECT_URI', 'http://localhost:3000/callback')

    # Advanced CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',') if os.environ.get('CORS_ORIGINS', '*') != '*' else '*'
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken']
    CORS_EXPOSE_HEADERS = ['Authorization', 'Set-Cookie']
    CORS_SUPPORTS_CREDENTIALS = True

    # Advanced Security Settings
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'flask_enterprise_session'
    SESSION_COOKIE_MAX_AGE = int(os.environ.get('SESSION_COOKIE_MAX_AGE', 3600))  # 1 hour
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }

    # Advanced Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))

    # Advanced Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True
    
    # Health Monitoring Configuration
    HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', 30))  # seconds
    HEALTH_CHECK_TIMEOUT = int(os.environ.get('HEALTH_CHECK_TIMEOUT', 5))  # seconds
    
    # Performance Monitoring
    ENABLE_PERFORMANCE_MONITORING = os.environ.get('ENABLE_PERFORMANCE_MONITORING', 'True').lower() == 'true'
    PERFORMANCE_LOG_THRESHOLD = float(os.environ.get('PERFORMANCE_LOG_THRESHOLD', 1.0))  # seconds
    
    # Cache Configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
    CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', 'flask_template_')
    
    # API Configuration
    API_TITLE = 'Flask Enterprise Template API'
    API_VERSION = 'v1'
    API_DESCRIPTION = 'Advanced Flask REST API with JWT authentication'
    API_DOC_URL = '/docs/'
    
    # Pagination Configuration
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', 20))
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE', 100))
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    
    # Background Tasks Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # Add your custom configuration variables here
    # CUSTOM_API_KEY = os.environ.get('CUSTOM_API_KEY')
    # CUSTOM_SERVICE_URL = os.environ.get('CUSTOM_SERVICE_URL')

    @staticmethod
    def validate_required_config():
        """Validate that all required configuration is present"""
        required_vars = ['SECRET_KEY']
        missing_vars = []

        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        # Special check for database URL (accept either DATABASE_URL_DB or DATABASE_URL)
        if not os.environ.get('DATABASE_URL_DB') and not os.environ.get('DATABASE_URL'):
            missing_vars.append('DATABASE_URL_DB or DATABASE_URL')

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        return True

    @staticmethod
    def validate_email_config():
        """Validate email configuration if email features are used"""
        if not Config.GMAIL_ADDRESS or not Config.GMAIL_PASSWORD:
            return False, "Email configuration missing. Set GMAIL_ADDRESS and GMAIL_PASSWORD"
        return True, "Email configuration valid"

    @staticmethod
    def validate_ai_config():
        """Validate AI service configuration if AI features are used"""
        if not Config.OPENAI_KEY and not Config.GEMINI_API_KEY:
            return False, "No AI service configured. Set OPENAI_KEY or GEMINI_API_KEY"
        return True, "AI configuration valid"


class DevelopmentConfig(Config):
    """Development environment configuration with advanced features"""

    DEBUG = True
    TESTING = False

    # Development-specific database settings
    SQLALCHEMY_ECHO = False  # Log SQL queries in development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DB', 'sqlite:///flask_template_dev.db')

    # Less strict security for development
    SESSION_COOKIE_SECURE = False  # Allow HTTP cookies
    
    # Relaxed CORS for development
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5000', 'http://127.0.0.1:5000']

    # Development logging
    LOG_LEVEL = 'DEBUG'
    
    # Development performance monitoring
    ENABLE_PERFORMANCE_MONITORING = True
    PERFORMANCE_LOG_THRESHOLD = 0.5  # Log requests taking more than 0.5 seconds
    
    # Development cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 60  # 1 minute


class TestingConfig(Config):
    """Testing environment configuration with advanced features"""

    DEBUG = False
    TESTING = True

    # Use same database as environment (PostgreSQL)
    # Tests will use actual database but with transactions rolled back
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DB')

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Fast password hashing for tests
    BCRYPT_LOG_ROUNDS = 1

    # Disable email during tests
    GMAIL_ADDRESS = None
    GMAIL_PASSWORD = None
    
    # Disable performance monitoring for tests
    ENABLE_PERFORMANCE_MONITORING = False
    
    # Test-specific rate limiting
    RATE_LIMIT_DEFAULT = '1000 per hour'
    
    # Test cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 1  # 1 second for tests


class ProductionConfig(Config):
    """Production environment configuration with advanced features"""

    DEBUG = False
    TESTING = False

    # Production database settings
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DB')

    # Strict security for production
    SESSION_COOKIE_SECURE = True  # Require HTTPS
    
    # Production CORS (should be restricted to actual domains)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://yourdomain.com').split(',')

    # Production logging
    LOG_LEVEL = 'WARNING'
    
    # Production performance monitoring
    ENABLE_PERFORMANCE_MONITORING = True
    PERFORMANCE_LOG_THRESHOLD = 2.0  # Log requests taking more than 2 seconds
    
    # Production cache settings
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 600  # 10 minutes
    
    # Production file upload settings
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB

    @staticmethod
    def validate_production_config():
        """Additional validation for production environment"""
        # Ensure secure secret key
        if Config.SECRET_KEY == 'dev-key-change-in-production':
            raise ValueError("You must set a secure SECRET_KEY for production!")

        # Ensure secure JWT key
        if Config.JWT_SECRET_KEY == 'jwt-dev-key-change-in-production':
            raise ValueError("You must set a secure JWT_SECRET_KEY for production!")

        # Validate database URL exists
        if not Config.DATABASE_URL:
            raise ValueError("Production requires DATABASE_URL_DB or DATABASE_URL to be set!")

        return True


class StagingConfig(ProductionConfig):
    """Staging environment configuration (inherits from Production)"""

    DEBUG = False
    TESTING = False

    # Slightly more verbose logging for staging
    LOG_LEVEL = 'INFO'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}


def get_config(env_name=None):
    """Get configuration class for specified environment"""
    if env_name is None:
        env_name = os.getenv('FLASK_ENV', 'development')

    return config.get(env_name, config['default'])


def validate_config(env_name=None):
    """Validate configuration for specified environment"""
    config_class = get_config(env_name)

    try:
        # Basic validation
        Config.validate_required_config()

        # Production-specific validation
        if env_name == 'production':
            ProductionConfig.validate_production_config()

        return True, "Configuration valid"

    except ValueError as e:
        return False, str(e)


def get_database_config():
    """
    Get database configuration for the current environment.
    
    Returns:
        dict: Database configuration dictionary
    """
    config_class = get_config()
    return {
        'database_uri': config_class.SQLALCHEMY_DATABASE_URI,
        'engine_options': config_class.SQLALCHEMY_ENGINE_OPTIONS,
        'track_modifications': config_class.SQLALCHEMY_TRACK_MODIFICATIONS
    }


def get_security_config():
    """
    Get security configuration for the current environment.
    
    Returns:
        dict: Security configuration dictionary
    """
    config_class = get_config()
    return {
        'secret_key': config_class.SECRET_KEY,
        'jwt_secret_key': config_class.JWT_SECRET_KEY,
        'jwt_access_token_expires': config_class.JWT_ACCESS_TOKEN_EXPIRES,
        'jwt_refresh_token_expires': config_class.JWT_REFRESH_TOKEN_EXPIRES,
        'jwt_blacklist_enabled': config_class.JWT_BLACKLIST_ENABLED,
        'session_cookie_secure': config_class.SESSION_COOKIE_SECURE,
        'security_headers': config_class.SECURITY_HEADERS
    }


def get_performance_config():
    """
    Get performance monitoring configuration for the current environment.
    
    Returns:
        dict: Performance configuration dictionary
    """
    config_class = get_config()
    return {
        'enable_monitoring': config_class.ENABLE_PERFORMANCE_MONITORING,
        'log_threshold': config_class.PERFORMANCE_LOG_THRESHOLD,
        'health_check_interval': config_class.HEALTH_CHECK_INTERVAL,
        'health_check_timeout': config_class.HEALTH_CHECK_TIMEOUT
    }


def get_cache_config():
    """
    Get cache configuration for the current environment.
    
    Returns:
        dict: Cache configuration dictionary
    """
    config_class = get_config()
    return {
        'cache_type': config_class.CACHE_TYPE,
        'default_timeout': config_class.CACHE_DEFAULT_TIMEOUT,
        'key_prefix': config_class.CACHE_KEY_PREFIX
    }