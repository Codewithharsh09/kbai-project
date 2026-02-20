"""
Flask Enterprise Backend Template - Database Setup

This module configures SQLAlchemy with optimized connection pooling,
session management, and production-ready settings.

Features:
- Connection pooling with configurable parameters
- Thread-safe scoped sessions
- Automatic connection recycling
- Pool overflow management
- Pre-ping for connection validation

Author: Flask Enterprise Template
License: MIT
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

# Create declarative base for ORM models - must be before model imports
Base = declarative_base()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL_DB")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL_DB environment variable is required. "
        "Please set it in your .env file."
    )

# Database engine configuration for production optimization
ENGINE_CONFIG = {
    # Connection Pool Settings
    'poolclass': QueuePool,
    'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),  # Base connections (increased)
    'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),  # Additional connections (increased)
    'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', 30)),  # Timeout for getting connection
    'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 3600)),  # Recycle connections after 1 hour (increased)
    'pool_pre_ping': True,  # Validate connections before use

    # Engine Settings
    'echo': os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true',  # Log SQL queries
    'echo_pool': os.getenv('SQLALCHEMY_ECHO_POOL', 'False').lower() == 'true',  # Log pool events

}

try:
    # Create SQLAlchemy engine with optimized settings
    engine = create_engine(DATABASE_URL, **ENGINE_CONFIG)

    logger.info(f"Database engine created successfully")
    logger.debug(f"Pool size: {ENGINE_CONFIG['pool_size']}, Max overflow: {ENGINE_CONFIG['max_overflow']}")

except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# Create thread-safe scoped session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Scoped session for thread safety
db_session = scoped_session(SessionLocal)

# Add query property to Base
Base.query = db_session.query_property()

# Import all models to ensure they're registered with Base
from src.models.db_model import *  # noqa


# Database event listeners for monitoring and optimization
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance (if using SQLite)"""
    if 'sqlite' in DATABASE_URL.lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout events (debug only)"""
    if logger.level <= logging.DEBUG:
        logger.debug(f"Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin events (debug only)"""
    if logger.level <= logging.DEBUG:
        logger.debug(f"Connection returned to pool")


def get_db_session():
    """
    Get a new database session.

    This function creates a new session for use in request contexts
    where you need explicit session management.

    Returns:
        Session: SQLAlchemy session instance

    Usage:
        session = get_db_session()
        try:
            # Your database operations
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    return SessionLocal()


def init_db():
    """
    Initialize database by creating all tables.

    This should be called once during application setup
    or in deployment scripts.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


def check_db_connection():
    """
    Check database connection health.

    Returns:
        tuple: (is_healthy, message)
    """
    try:
        # Test connection
        with engine.connect() as connection:
            connection.execute("SELECT 1")

        logger.info("Database connection check passed")
        return True, "Database connection healthy"

    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False, f"Database connection failed: {str(e)}"


def get_db_stats():
    """
    Get database connection pool statistics.

    Returns:
        dict: Pool statistics
    """
    pool = engine.pool

    stats = {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'invalid': pool.invalid()
    }

    logger.debug(f"Database pool stats: {stats}")
    return stats


def cleanup_db_session():
    """
    Clean up database session.

    This should be called at the end of request lifecycle
    or in application teardown.
    """
    try:
        db_session.remove()
        logger.debug("Database session cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up database session: {str(e)}")


# TODO: PROJECT_SPECIFIC - Add custom database utilities here
def create_sample_data():
    """
    TODO: PROJECT_SPECIFIC - Create sample data for development

    This function can be used to populate the database with
    sample data for development and testing purposes.
    """
    session = get_db_session()
    try:
        # Add your sample data creation logic here
        # Example:
        # from src.models.db_model import User
        # admin_user = User(email='admin@example.com')
        # session.add(admin_user)
        # session.commit()

        logger.info("Sample data created successfully")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create sample data: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Command line interface for database operations
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            print("Initializing database...")
            init_db()
            print("Database initialized successfully!")

        elif command == "check":
            print("Checking database connection...")
            healthy, message = check_db_connection()
            print(f"Status: {message}")
            sys.exit(0 if healthy else 1)

        elif command == "stats":
            print("Database pool statistics:")
            stats = get_db_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")

        elif command == "sample":
            print("Creating sample data...")
            create_sample_data()
            print("Sample data created successfully!")

        else:
            print(f"Unknown command: {command}")
            print("Available commands: init, check, stats, sample")
            sys.exit(1)
    else:
        print("Usage: python db_setup.py <command>")
        print("Available commands: init, check, stats, sample")