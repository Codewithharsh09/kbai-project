#!/usr/bin/env python3
"""
Reset database and apply migrations cleanly
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from src.config import get_config
from src.extensions import db
from src.app.database.models import *  # Import all models

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e.stderr}")
        return False

def reset_database():
    """Reset database by dropping and recreating schemas"""
    print("🗑️ Resetting database...")
    
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    db.init_app(app)
    
    with app.app_context():
        try:
            from sqlalchemy import text
            # Drop schemas if they exist
            db.session.execute(text("DROP SCHEMA IF EXISTS kbai CASCADE"))
            db.session.execute(text("DROP SCHEMA IF EXISTS kbai_balance CASCADE"))
            db.session.commit()
            print("✅ Database reset successfully")
            return True
        except Exception as e:
            print(f"❌ Database reset failed: {str(e)}")
            return False

def setup_clean_migrations():
    """Setup database with clean migrations"""
    print("🚀 Setting up clean KBAI database...")
    
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    db.init_app(app)
    
    with app.app_context():
        # Step 1: Reset database
        if not reset_database():
            return False
        
        # Step 2: Create schemas
        print("📁 Creating database schemas...")
        try:
            from sqlalchemy import text
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai"))
            db.session.execute(text("CREATE SCHEMA IF NOT EXISTS kbai_balance"))
            db.session.commit()
            print("✅ Schemas created successfully")
        except Exception as e:
            print(f"❌ Schema creation failed: {str(e)}")
            return False
        
        # Step 3: Remove existing migration files
        print("🗑️ Cleaning existing migrations...")
        import shutil
        if os.path.exists('migrations/versions'):
            for file in os.listdir('migrations/versions'):
                if file.endswith('.py') and file != '.gitkeep':
                    os.remove(f'migrations/versions/{file}')
        print("✅ Migration files cleaned")
        
        # Step 4: Create fresh migration
        print("📝 Creating fresh migration...")
        if not run_command('flask db migrate -m "Initial migration with all KBAI tables"', "Fresh migration creation"):
            return False
        
        # Step 5: Apply migrations
        print("🔄 Applying migrations...")
        if not run_command("flask db upgrade", "Migration application"):
            return False
        
        print("\n🎉 Clean database setup completed successfully!")
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
        success = setup_clean_migrations()
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
