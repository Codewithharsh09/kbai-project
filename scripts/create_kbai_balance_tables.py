#!/usr/bin/env python3
"""
Database Migration Script: Create KBAI Balance Schema Tables

This script creates all the tables for the KBAI balance schema in the kbai_balance folder:
- kbai_balances
- kbai_kpi_values  
- kbai_analysis
- kbai_analysis_kpi
- analysis_kpi_info
- kpi_logic
- kbai_reports
- kbai_goal_objectives
- kbai_goal_progress

Usage:
    python scripts/create_kbai_balance_tables.py
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import create_app
from src.extensions import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_kbai_balance_tables():
    """Create all KBAI balance schema tables"""
    
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("Starting KBAI balance tables creation...")
            
            # Create all tables
            db.create_all()
            
            logger.info("✅ All KBAI balance tables created successfully!")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names(schema='kbai_balance')
            
            expected_tables = [
                'kbai_balances',
                'kbai_kpi_values', 
                'kbai_analysis',
                'kbai_analysis_kpi',
                'analysis_kpi_info',
                'kpi_logic',
                'kbai_reports',
                'kbai_goal_objectives',
                'kbai_goal_progress'
            ]
            
            logger.info("📋 Created tables in kbai_balance schema:")
            for table in expected_tables:
                if table in tables:
                    logger.info(f"  ✅ {table}")
                else:
                    logger.warning(f"  ❌ {table} - NOT FOUND")
            
            logger.info("🎉 KBAI balance schema setup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error creating KBAI balance tables: {str(e)}")
            raise

if __name__ == "__main__":
    create_kbai_balance_tables()
