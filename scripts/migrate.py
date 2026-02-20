#!/usr/bin/env python3
"""
Database Migration Script for KBAI Backend

This script handles database migrations using Flask-Migrate.
It can initialize, create, and apply migrations.

Usage:
    python scripts/migrate.py init                    # Initialize migrations
    python scripts/migrate.py create "message"       # Create new migration
    python scripts/migrate.py upgrade               # Apply migrations
    python scripts/migrate.py downgrade             # Rollback migration
    python scripts/migrate.py current               # Show current revision
    python scripts/migrate.py history               # Show migration history

Author: Flask Enterprise Template
License: MIT
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from src.config import get_config
from src.extensions import db
from src.app.database.models import *  # Import all models

def create_app():
    """Create Flask application for migrations"""
    app = Flask(__name__)
    
    # Get configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    return app

def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Database migration commands')
    parser.add_argument('command', choices=['init', 'create', 'upgrade', 'downgrade', 'current', 'history'], 
                       help='Migration command to run')
    parser.add_argument('message', nargs='?', help='Migration message (for create command)')
    
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        # Initialize Flask-Migrate
        migrate = Migrate(app, db)
        manager = Manager(app)
        manager.add_command('db', MigrateCommand)
        
        if args.command == 'init':
            print("Initializing database migrations...")
            os.system("flask db init")
            print("✅ Migrations initialized successfully!")
            
        elif args.command == 'create':
            if not args.message:
                print("❌ Error: Migration message is required for create command")
                print("Usage: python scripts/migrate.py create 'Your migration message'")
                sys.exit(1)
            print(f"Creating migration: {args.message}")
            os.system(f'flask db migrate -m "{args.message}"')
            print("✅ Migration created successfully!")
            
        elif args.command == 'upgrade':
            print("Applying migrations...")
            os.system("flask db upgrade")
            print("✅ Migrations applied successfully!")
            
        elif args.command == 'downgrade':
            print("Rolling back migration...")
            os.system("flask db downgrade")
            print("✅ Migration rolled back successfully!")
            
        elif args.command == 'current':
            print("Current migration status:")
            os.system("flask db current")
            
        elif args.command == 'history':
            print("Migration history:")
            os.system("flask db history")

if __name__ == '__main__':
    main()
