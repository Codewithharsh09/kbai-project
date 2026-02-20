"""
Flask Enterprise Backend Template - Main Package

This package provides a complete enterprise-ready Flask backend template
with authentication, user management, email services, and deployment automation.

Author: Flask Enterprise Template
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Flask Enterprise Template"
__email__ = "admin@flask-enterprise.com"

# Package metadata
__title__ = "Flask Enterprise Backend Template"
__description__ = "Enterprise-ready Flask backend with JWT auth, user management, and deployment automation"
__url__ = "https://github.com/your-org/flask-enterprise-template"
__license__ = "MIT"

# Import main application factory
from src.app import create_app

# Export public API
__all__ = [
    'create_app',
    '__version__',
    '__author__',
    '__title__',
    '__description__',
]


# Development helper
def get_version():
    """Get package version"""
    return __version__


def get_info():
    """Get package information"""
    return {
        'name': __title__,
        'version': __version__,
        'description': __description__,
        'author': __author__,
        'license': __license__,
        'url': __url__,
    }
