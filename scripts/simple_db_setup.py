#!/usr/bin/env python3
"""
Simple Database Setup - Uses db.create_all() approach
This script creates all database schemas and tables using the existing models
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

def create_schemas():
    """Create database schemas"""
    print("📁 Creating database schemas...")
    try:
        from sqlalchemy import text
        # Create schemas
        db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai"))
        db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai_balance"))
        db.session.commit()
        print("✅ Schemas created successfully!")
        return True
    except Exception as e:
        print(f"❌ Schema creation failed: {str(e)}")
        return False

def create_all_tables():
    """Create all database tables using db.create_all()"""
    print("🔄 Creating all database tables...")
    try:
        # This will create all tables based on your existing models
        db.create_all()
        print("✅ All tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {str(e)}")
        return False

def setup_database():
    """Complete database setup"""
    print("🚀 Setting up KBAI database...")
    
    # Create Flask app
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    db.init_app(app)
    
    with app.app_context():
        # Step 1: Create schemas
        if not create_schemas():
            return False
        
        # Step 2: Create all tables
        if not create_all_tables():
            return False
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📊 Database includes:")
        print("   • Public schema: tb_licences, tb_groups, tb_user, tb_user_group")
        print("   • KBAI schema: kbai_companies, kbai_zone, kbai_sectors, kbai_threshold, kbai_state, kbai_pre_dashboard")
        print("   • KBAI Balance schema: kbai_balances, kbai_kpi_values, kbai_analysis_kpi, kbai_analysis, kbai_goal_objectives, kbai_goal_progress, kbai_reports")
        print("   • KBAI Employees: kbai_employees, kbai_employee_company_map, kbai_employee_evaluations")
        print("\n🚀 You can now start the application with: python run.py")
        
        return True

def main():
    """Main function"""
    try:
        success = setup_database()
        if success:
            print("\n✅ All done! Your database is ready.")
            sys.exit(0)
        else:
            print("\n❌ Database setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
