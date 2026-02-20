#!/usr/bin/env python3
"""
Simple script to create database tables from existing models
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

def create_tables():
    """Create all database tables from existing models"""
    print("Creating database tables from existing models...")
    
    # Create Flask app
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ All database tables created successfully!")
            print("\nTables created:")
            print("- Public schema: tb_licences, tb_groups, tb_user, tb_user_group")
            print("- KBAI schema: kbai_companies, kbai_zone, kbai_sectors, kbai_threshold, kbai_state, kbai_pre_dashboard")
            print("- KBAI Balance schema: kbai_balances, kbai_kpi_values, kbai_analysis_kpi, kbai_analysis, kbai_goal_objectives, kbai_goal_progress, kbai_reports")
            print("- KBAI Employees: kbai_employees, kbai_employee_company_map, kbai_employee_evaluations")
            print("\nYou can now start the application with: python run.py")
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    create_tables()
