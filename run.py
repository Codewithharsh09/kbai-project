# !/usr/bin/env python3
"""
Flask Enterprise Backend Template - Development Entry Point

This file is used to run the application in development mode.
For production deployment, use wsgi.py with gunicorn.

Usage:
    python run.py

Author: Flask Enterprise Template
License: MIT
"""

import os
import logging
from src.app import create_app
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())


def setup_development_logging():
    """Configure logging for development environment"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('development.log')
        ]
    )


if __name__ == '__main__':
    # Setup development logging
    # setup_development_logging()

    # Get configuration from environment
    env_name = os.getenv('FLASK_ENV', 'development')
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')

    # Create Flask application
    app = create_app(env_name)

    # Set security settings for development
    app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in development

    # Log startup information
    app.logger.info(f"Starting Flask Enterprise Backend Template")
    app.logger.info(f"Environment: {env_name}")
    app.logger.info(f"Debug mode: {debug}")
    app.logger.info(f"Running on: http://{host}:{port}")

    # Run development server
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        app.logger.info("Application stopped by user")
    except Exception as e:
        app.logger.error(f"Application failed to start: {str(e)}")
        raise