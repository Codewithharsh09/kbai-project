"""
Flask Enterprise Backend Template - Legacy Application Factory

This module provides backward compatibility for the old app.py structure.
The new application factory is now in src/app/__init__.py

Author: Flask Enterprise Template
License: MIT
"""

import os
from src.app import create_app as new_create_app
from src.config import get_config


def create_app(env_name=None):
    """
    Legacy Flask application factory for backward compatibility.
    
    Args:
        env_name (str): Environment name (development, testing, production)

    Returns:
        Flask: Configured Flask application instance
    """
    # Load configuration
    if env_name is None:
        env_name = os.getenv('FLASK_ENV', 'development')

    config_class = get_config(env_name)
    
    # Use the new application factory
    return new_create_app(config_class)


# All functionality has been moved to src/app/__init__.py
# This file now only provides backward compatibility