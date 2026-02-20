#!/usr/bin/env python3
"""
Fix Public Schema - Remove extra tables and create correct ones based on ERD
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
from src.app.database.models import *  # Import all models

def drop_extra_tables():
    """Drop extra tables that don't exist in the ERD"""
    print("🗑️ Dropping extra tables from public schema...")
    try:
        from sqlalchemy import text
        
        # Drop extra tables that don't exist in your ERD
        extra_tables = [
            'tb_groups',  # This table doesn't exist in your ERD
            'tb_user_group',  # This table doesn't exist in your ERD
            'alembic_version'  # Migration tracking table (not part of your ERD)
        ]
        
        for table in extra_tables:
            try:
                db.session.execute(text(f"DROP TABLE IF EXISTS public.{table} CASCADE"))
                print(f"   ✅ Dropped {table}")
            except Exception as e:
                print(f"   ⚠️ Could not drop {table}: {str(e)}")
        
        db.session.commit()
        print("✅ Extra tables dropped successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to drop extra tables: {str(e)}")
        return False

def create_correct_tables():
    """Create the correct tables based on your ERD"""
    print("🔄 Creating correct public schema tables...")
    try:
        # This will create all tables based on your updated models
        db.create_all()
        print("✅ Correct tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {str(e)}")
        return False

def verify_tables():
    """Verify that only the correct tables exist"""
    print("🔍 Verifying public schema tables...")
    try:
        from sqlalchemy import text
        
        # Check what tables exist in public schema
        result = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)).fetchall()
        
        existing_tables = [row[0] for row in result]
        expected_tables = ['tb_licences', 'licence_admin', 'tb_user', 'tb_user_company']
        
        print("📊 Current public schema tables:")
        for table in existing_tables:
            if table in expected_tables:
                print(f"   ✅ {table} (correct)")
            else:
                print(f"   ❌ {table} (extra - should be removed)")
        
        # Check if all expected tables exist
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            print(f"⚠️ Missing tables: {missing_tables}")
            return False
        
        extra_tables = set(existing_tables) - set(expected_tables)
        if extra_tables:
            print(f"⚠️ Extra tables found: {extra_tables}")
            return False
        
        print("✅ All tables match your ERD!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

def fix_public_schema():
    """Fix the public schema to match your ERD"""
    print("🚀 Fixing public schema to match your ERD...")
    
    # Create Flask app
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    db.init_app(app)
    
    with app.app_context():
        # Step 1: Drop extra tables
        if not drop_extra_tables():
            return False
        
        # Step 2: Create correct tables
        if not create_correct_tables():
            return False
        
        # Step 3: Verify tables
        if not verify_tables():
            return False
        
        print("\n🎉 Public schema fixed successfully!")
        print("\n📊 Public schema now includes:")
        print("   • tb_licences - License management")
        print("   • licence_admin - License admin relationships")
        print("   • tb_user - User management with self-referencing admin")
        print("   • tb_user_company - User-company relationships")
        print("\n🔗 All relationships match your ERD!")
        
        return True

def main():
    """Main function"""
    try:
        success = fix_public_schema()
        if success:
            print("\n✅ Public schema is now correct and matches your ERD!")
            sys.exit(0)
        else:
            print("\n❌ Public schema fix failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
