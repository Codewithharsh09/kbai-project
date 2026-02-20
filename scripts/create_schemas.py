#!/usr/bin/env python3
"""
Create database schemas for KBAI system
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.config import get_config
from src.extensions import db

def create_schemas():
    """Create database schemas"""
    print("📁 Creating database schemas...")
    
    # Create Flask app
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    db.init_app(app)
    
    with app.app_context():
        try:
            from sqlalchemy import text
            # Create schemas
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai"))
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai_balance"))
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS public "))
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai_employee"))
            db.session.commit()
            print("✅ Schemas created successfully!")
            print("   • kbai schema created")
            print("   • kbai_balance schema created")
            return True
        except Exception as e:
            print(f"❌ Schema creation failed: {str(e)}")
            return False

if __name__ == '__main__':
    success = create_schemas()
    if success:
        print("\n🎉 Database schemas are ready!")
        print("Now you can run: python scripts/setup_migrations.py")
    else:
        print("\n❌ Schema creation failed!")
        sys.exit(1)
