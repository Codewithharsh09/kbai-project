"""
Flask Enterprise Backend Template - Application Factory

This module implements the Flask application factory pattern with
modular configuration, blueprint registration, and error handling.

Features:
- Environment-based configuration
- CORS support for cross-origin requests
- Modular blueprint registration
- Centralized error handling
- Database session management
- Security headers
- Request/response logging

Author: Flask Enterprise Template
License: MIT
"""

from flask import Flask
from dotenv import load_dotenv
from ..config import get_config, validate_config
from ..extensions import db, ma, jwt, migrate, cors, limiter, api as restx_api, init_extensions
from .api.v1 import register_all_namespaces
from .api.v1.routes import api_v1
from ..common.exceptions import register_error_handlers
import os
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Initialize the Flask application
# -----------------------------------------------------------------------
def create_app(config_class=None):
    """
    Flask application factory.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask: Configured Flask application instance
    """
    import os
    # Get the project root directory (where templates folder is)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_dir = os.path.join(root_dir, 'templates')
    static_dir = os.path.join(root_dir, 'static')
    
    # Create Flask application with template and static folders
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Load configuration
    if config_class is None:
        env_name = os.getenv('FLASK_ENV', 'development')
        config_class = get_config(env_name)
    elif isinstance(config_class, str):
        # If config_class is a string (environment name), get the actual config class
        config_class = get_config(config_class)
    
    app.config.from_object(config_class)
    
    # Validate configuration
    env_name = os.getenv('FLASK_ENV', 'development')
    config_valid, config_message = validate_config(env_name)
    if not config_valid:
        raise ValueError(f"Configuration validation failed: {config_message}")
    
    
    # Register template routes FIRST (main landing page and health page)
    register_template_routes(app)
    
    # Initialize extensions
    init_extensions(app)
    
    # Setup advanced error handlers
    register_error_handlers(app)
    
    # Add global security headers BEFORE API initialization
    # This ensures CSP headers are applied to all responses
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        # Content Security Policy - Using external CSS (more secure, no unsafe-inline needed)
        # This overrides any default CSP set by Flask-RESTX or other middleware
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self';"
        )
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    
    # Register main API v1 blueprint (which contains all route blueprints)
    app.register_blueprint(api_v1, url_prefix="/api/v1")
    
    # Register all namespaces for Swagger documentation
    register_all_namespaces(restx_api)
    
    # Log application startup
    app.logger.info(f"Flask Enterprise Backend Template started in {env_name} mode")
    
    return app


def register_template_routes(app):
    """Register routes for HTML template pages"""
    from flask import render_template
    import os
    
    @app.route('/')
    def index():
        """Main landing page"""
        env = os.getenv('FLASK_ENV', 'production')
        version = '1.0.0'
        # CSP headers are added globally via after_request handler
        return render_template('index.html', env=env, version=version)
    
    @app.route('/health')
    def health_page():
        """Health check page"""
        # CSP headers are added globally via after_request handler
        env = os.getenv('FLASK_ENV', 'production')
        return render_template('health.html', 
                             status='Operational', 
                             environment=env, 
                             version='1.0.0')


