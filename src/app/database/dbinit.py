# """
# Database Initialization Module

# Simple database initialization for KBAI Backend
# """

# import logging
# from flask import current_app
# from sqlalchemy.exc import SQLAlchemyError
# from .models import *
# from src.extensions import db

# logger = logging.getLogger(__name__)


# def init_database(app=None):
#     """
#     Initialize database with all tables
    
#     Args:
#         app: Flask application instance (optional)
        
#     Returns:
#         bool: True if initialization successful, False otherwise
#     """
#     if app is None:
#         app = current_app
    
#     try:
#         with app.app_context():
#             # Create all database tables
#             db.create_all()
#             logger.info("Database tables created successfully")
#             logger.info("Database initialization completed successfully")
#             return True
            
#     except SQLAlchemyError as e:
#         logger.error(f"Database initialization failed: {str(e)}")
#         return False
#     except Exception as e:
#         logger.error(f"Unexpected error during database initialization: {str(e)}")
#         return False

"""
Database Initialization and Auto-Migration Module
"""

import logging
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def init_database(app=None):
    """
    Initialize database:
    - Ensure all schemas exist
    - Ensure all tables exist
    - Add any missing columns for every model in the system
    """

    if app is None:
        from flask import current_app
        app = current_app

    from src.extensions import db
    from .models import TbUser, UserTempData, TbUserCompany, TbLicences, LicenceAdmin

    # ✅ List all models to process
    models = [TbUser, UserTempData, TbUserCompany, TbLicences, LicenceAdmin]

    try:
        with app.app_context():
            inspector = inspect(db.engine)

            # --- Step 1: Ensure all schemas exist ---
            schemas = set()
            for model in models:
                table_args = getattr(model, '__table_args__', {})
                if isinstance(table_args, dict):
                    schema = table_args.get('schema')
                    if schema:
                        schemas.add(schema)

            for schema in schemas:
                try:
                    sql = f'CREATE SCHEMA IF NOT EXISTS {schema};'
                    db.session.execute(text(sql))
                    db.session.commit()
                    logger.info(f"✅ Schema '{schema}' ensured.")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to ensure schema {schema}: {e}")

            # --- Step 2: Create any missing tables ---
            db.create_all()
            logger.info("✅ All tables created if missing.")

            # --- Step 3: Auto-check and add missing columns ---
            for model in models:
                table_name = model.__tablename__
                table_args = getattr(model, '__table_args__', {})
                schema = table_args.get('schema', None)

                full_table_name = f"{schema}.{table_name}" if schema else table_name

                try:
                    # Get existing columns
                    columns_in_db = [col['name'] for col in inspector.get_columns(table_name, schema=schema)]
                except Exception as e:
                    logger.warning(f"⚠️ Could not inspect table {full_table_name}: {e}")
                    continue

                for col in model.__table__.columns:
                    if col.name not in columns_in_db:
                        try:
                            col_type = col.type.compile(db.engine.dialect)
                            nullable = 'NULL' if col.nullable else 'NOT NULL'
                            default_clause = ""

                            # Add default value if specified
                            if col.default is not None and hasattr(col.default, 'arg'):
                                default_value = col.default.arg
                                if isinstance(default_value, str):
                                    default_clause = f" DEFAULT '{default_value}'"
                                else:
                                    default_clause = f" DEFAULT {default_value}"

                            sql = f'ALTER TABLE {full_table_name} ADD COLUMN {col.name} {col_type}{default_clause} {nullable};'
                            db.session.execute(text(sql))
                            db.session.commit()
                            logger.info(f"🟢 Column '{col.name}' added successfully to {full_table_name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to add column '{col.name}' to {full_table_name}: {e}")

            logger.info("🎉 Database initialization and auto-migration completed successfully.")
            return True

    except SQLAlchemyError as e:
        logger.error(f"❌ Database initialization failed (SQLAlchemyError): {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore rollback errors if session is unavailable
        raise  # Re-raise to propagate error
    except Exception as e:
        logger.error(f"❌ Unexpected error during database initialization: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Ignore rollback errors if session is unavailable
        raise  # Re-raise to propagate error
