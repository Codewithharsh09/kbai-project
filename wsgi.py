#!/usr/bin/env python3
"""
Flask Enterprise Backend Template - Production WSGI Entry Point

This file is used by production WSGI servers like gunicorn.

Usage with gunicorn:
    gunicorn --bind 0.0.0.0:5000 wsgi:application
    gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class sync wsgi:application

Environment Variables Required:
    - FLASK_ENV=production
    - SECRET_KEY (secure random key)
    - DATABASE_URL_DB (production database)
    - All other production configurations in .env

Author: Flask Enterprise Template
License: MIT
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from src.app import create_app
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())


def setup_production_logging(app):
    """Configure production logging with rotation"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # Setup rotating file handler
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=int(os.getenv('LOG_MAX_BYTES', 10485760)),  # 10MB default
            backupCount=int(os.getenv('LOG_BACKUP_COUNT', 5))
        )

        # Set log format
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        # Set log level
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
        file_handler.setLevel(log_level)

        # Add handler to app logger
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)

        # Log application startup
        app.logger.info('Flask Enterprise Backend Template startup')


def configure_production_settings(app):
    """Configure production-specific settings"""
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

    # Disable Flask debug toolbar in production
    app.config['DEBUG_TB_ENABLED'] = False

    # Additional security headers can be added here
    # or use flask-talisman for comprehensive security headers


# Create application instance
env_name = os.getenv('FLASK_ENV', 'production')
application = create_app(env_name)

# Configure production settings
if env_name == 'production':
    configure_production_settings(application)
    setup_production_logging(application)

# For compatibility with some WSGI servers
app = application

if __name__ == "__main__":
    # This should not be used in production
    # Use gunicorn instead: gunicorn wsgi:application
    application.run(host='0.0.0.0', port=5000)