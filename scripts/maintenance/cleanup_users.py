#!/usr/bin/env python3
"""
Flask Enterprise Backend Template - User Cleanup Maintenance Script

This script performs maintenance operations on user data including:
- Cleanup of inactive users
- Removal of expired sessions
- Audit log cleanup
- Orphaned data removal
- User statistics reporting

Usage:
    python scripts/maintenance/cleanup_users.py [options]

Author: Flask Enterprise Template
License: MIT
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import application modules
from src.db_setup import get_db_session, check_db_connection
from src.models.db_model import User, AuditLog
from sqlalchemy import and_, or_, func, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('maintenance.log')
    ]
)
logger = logging.getLogger(__name__)


class UserCleanupManager:
    """
    Manager class for user cleanup operations.

    This class provides methods for various user maintenance operations
    while ensuring data integrity and proper logging.
    """

    def __init__(self, dry_run=False):
        """
        Initialize cleanup manager.

        Args:
            dry_run (bool): If True, don't actually delete data, just report what would be deleted
        """
        self.dry_run = dry_run
        self.session = None
        self.stats = {
            'users_processed': 0,
            'users_deactivated': 0,
            'users_deleted': 0,
            'audit_logs_cleaned': 0,
            'orphaned_data_removed': 0
        }

    def __enter__(self):
        """Context manager entry"""
        self.session = get_db_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
            self.session.close()

    def check_database_health(self):
        """Check database connection and health"""
        logger.info("Checking database health...")

        healthy, message = check_db_connection()
        if not healthy:
            logger.error(f"Database health check failed: {message}")
            return False

        logger.info("Database health check passed")
        return True

    def cleanup_inactive_users(self, days_inactive=90, days_never_logged_in=30):
        """
        Clean up users who have been inactive for specified period.

        Args:
            days_inactive (int): Days since last login to consider inactive
            days_never_logged_in (int): Days since account creation for users who never logged in
        """
        logger.info(
            f"Starting cleanup of inactive users (inactive: {days_inactive} days, never logged in: {days_never_logged_in} days)")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        never_logged_in_cutoff = datetime.now(timezone.utc) - timedelta(days=days_never_logged_in)

        # Find inactive users (excluding admins and already deleted users)
        inactive_users = self.session.query(User).filter(
            and_(
                User.is_deleted == False,
                User.role != 'admin',  # Never auto-cleanup admin users
                or_(
                    # Users who never logged in and account is old enough
                    User.created_at < never_logged_in_cutoff
                )
            )
        ).all()

        logger.info(f"Found {len(inactive_users)} inactive users")

        for user in inactive_users:
            self.stats['users_processed'] += 1

            # Log user details
            logger.info(f"Processing inactive user: {user.username} (ID: {user.id})")

            if not self.dry_run:
                # Soft delete the user
                user.soft_delete()
                self.stats['users_deleted'] += 1

                # Log the cleanup action
                AuditLog.log_event(
                    session=self.session,
                    event_type='user_cleanup',
                    description=f'Auto-cleanup inactive user: {user.username}',
                    user=None,  # System action
                    resource_type='User',
                    resource_id=user.id
                )

                logger.info(f"Soft deleted inactive user: {user.username}")
            else:
                logger.info(f"[DRY RUN] Would soft delete user: {user.username}")

    def cleanup_old_audit_logs(self, days_to_keep=365):
        """
        Clean up old audit log entries.

        Args:
            days_to_keep (int): Number of days of audit logs to retain
        """
        logger.info(f"Starting cleanup of audit logs older than {days_to_keep} days")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Count old audit logs
        old_logs_count = self.session.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).count()

        logger.info(f"Found {old_logs_count} old audit log entries")

        if old_logs_count > 0 and not self.dry_run:
            # Delete old audit logs in batches to avoid memory issues
            batch_size = 1000
            deleted_count = 0

            while True:
                # Delete a batch of old logs
                batch_deleted = self.session.execute(
                    text("""
                         DELETE
                         FROM audit_logs
                         WHERE id IN (SELECT id
                                      FROM audit_logs
                                      WHERE created_at < :cutoff_date
                                      LIMIT :batch_size)
                         """),
                    {'cutoff_date': cutoff_date, 'batch_size': batch_size}
                ).rowcount

                deleted_count += batch_deleted

                if batch_deleted == 0:
                    break

                # Commit batch
                self.session.commit()
                logger.info(f"Deleted batch of {batch_deleted} audit logs (total: {deleted_count})")

            self.stats['audit_logs_cleaned'] = deleted_count
            logger.info(f"Cleaned up {deleted_count} old audit log entries")
        elif self.dry_run:
            logger.info(f"[DRY RUN] Would delete {old_logs_count} old audit log entries")

    def cleanup_orphaned_data(self):
        """
        Clean up orphaned data (data referencing non-existent users).

        TODO: PROJECT_SPECIFIC - Add cleanup for your custom models
        """
        logger.info("Starting cleanup of orphaned data")

        # Example: Clean up orphaned project entities
        try:
            from src.models.db_model import ProjectEntity

            # Find entities owned by deleted users
            orphaned_entities = self.session.query(ProjectEntity).join(
                User, ProjectEntity.owner_id == User.id
            ).filter(User.is_deleted == True).all()

            logger.info(f"Found {len(orphaned_entities)} orphaned project entities")

            for entity in orphaned_entities:
                logger.info(f"Processing orphaned entity: {entity.name} (ID: {entity.id})")

                if not self.dry_run:
                    entity.soft_delete()
                    self.stats['orphaned_data_removed'] += 1
                    logger.info(f"Soft deleted orphaned entity: {entity.name}")
                else:
                    logger.info(f"[DRY RUN] Would soft delete entity: {entity.name}")

        except ImportError:
            logger.info("ProjectEntity model not found, skipping orphaned entity cleanup")

        # TODO: PROJECT_SPECIFIC - Add cleanup for your custom models here
        # Example:
        # try:
        #     from src.models.db_model import YourCustomModel
        #     orphaned_items = self.session.query(YourCustomModel).join(
        #         User, YourCustomModel.user_id == User.id
        #     ).filter(User.is_deleted == True).all()
        #     # ... cleanup logic
        # except ImportError:
        #     pass

    def cleanup_user_sessions(self, days_expired=7):
        """
        Clean up expired user sessions.

        Note: This is a placeholder as the current template uses JWT tokens
        which are stateless. If you implement server-side session storage,
        add the cleanup logic here.

        Args:
            days_expired (int): Days after which sessions are considered expired
        """
        logger.info(f"Session cleanup placeholder (current template uses stateless JWT)")

        # TODO: PROJECT_SPECIFIC - If you implement server-side sessions, add cleanup here
        # Example with Redis sessions:
        # try:
        #     import redis
        #     r = redis.Redis(host='localhost', port=6379, db=0)
        #     # Clean up expired session keys
        # except ImportError:
        #     logger.info("Redis not available for session cleanup")

    def deactivate_suspicious_users(self):
        """
        Deactivate users with suspicious activity patterns.

        This method looks for users with multiple failed login attempts
        or other suspicious patterns and deactivates them for security.
        """
        logger.info("Checking for users with suspicious activity")

        # Find users with excessive failed login attempts
        suspicious_users = self.session.query(User).filter(
            and_(
                User.is_deleted == False,
                User.is_active == True,
                User.failed_login_attempts >= 10  # Adjust threshold as needed
            )
        ).all()

        logger.info(f"Found {len(suspicious_users)} users with suspicious activity")

        for user in suspicious_users:
            logger.warning(f"Suspicious user activity: {user.username} ({user.failed_login_attempts} failed attempts)")

            if not self.dry_run:
                user.is_active = False
                self.stats['users_deactivated'] += 1

                # Log the security action
                AuditLog.log_event(
                    session=self.session,
                    event_type='security_deactivation',
                    description=f'Auto-deactivated user due to suspicious activity: {user.failed_login_attempts} failed login attempts',
                    user=None,  # System action
                    resource_type='User',
                    resource_id=user.id
                )

                logger.warning(f"Deactivated suspicious user: {user.username}")
            else:
                logger.info(f"[DRY RUN] Would deactivate user: {user.username}")

    def generate_user_statistics(self):
        """Generate user statistics report"""
        logger.info("Generating user statistics...")

        # Basic user counts
        total_users = self.session.query(User).filter(User.is_deleted == False).count()
        active_users = self.session.query(User).filter(
            and_(User.is_deleted == False, User.is_active == True)
        ).count()
        inactive_users = total_users - active_users

        # Role distribution
        role_stats = {}
        roles = self.session.query(User.role, func.count(User.id)).filter(
            User.is_deleted == False
        ).group_by(User.role).all()

        for role, count in roles:
            role_stats[role] = count

        # Login statistics
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_logins = self.session.query(User).filter(
            and_(
                User.is_deleted == False,
                User.created_at >= thirty_days_ago
            )
        ).count()

        never_logged_in = self.session.query(User).filter(
            and_(
                User.is_deleted == False,
                User.created_at < thirty_days_ago
            )
        ).count()

        # Print statistics
        print("\n" + "=" * 50)
        print("USER STATISTICS REPORT")
        print("=" * 50)
        print(f"Total Users: {total_users}")
        print(f"Active Users: {active_users}")
        print(f"Inactive Users: {inactive_users}")
        print(f"Never Logged In: {never_logged_in}")
        print(f"Recent Logins (30 days): {recent_logins}")
        print("\nRole Distribution:")
        for role, count in role_stats.items():
            print(f"  {role.capitalize()}: {count}")

        if self.stats['users_processed'] > 0:
            print(f"\nCleanup Statistics:")
            print(f"  Users Processed: {self.stats['users_processed']}")
            print(f"  Users Deactivated: {self.stats['users_deactivated']}")
            print(f"  Users Deleted: {self.stats['users_deleted']}")
            print(f"  Audit Logs Cleaned: {self.stats['audit_logs_cleaned']}")
            print(f"  Orphaned Data Removed: {self.stats['orphaned_data_removed']}")

        print("=" * 50)

    def run_full_cleanup(self, **options):
        """
        Run complete cleanup process.

        Args:
            **options: Cleanup options passed from command line
        """
        logger.info("Starting full user cleanup process")

        if not self.check_database_health():
            logger.error("Database health check failed, aborting cleanup")
            return False

        try:
            # Run cleanup operations
            self.cleanup_inactive_users(
                days_inactive=options.get('days_inactive', 90),
                days_never_logged_in=options.get('days_never_logged_in', 30)
            )

            self.cleanup_old_audit_logs(
                days_to_keep=options.get('audit_retention_days', 365)
            )

            self.cleanup_orphaned_data()
            self.deactivate_suspicious_users()
            self.cleanup_user_sessions()

            # Generate final report
            self.generate_user_statistics()

            logger.info("User cleanup process completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error during cleanup process: {str(e)}")
            return False


def main():
    """Main function to handle command line arguments and run cleanup"""
    parser = argparse.ArgumentParser(
        description="Flask Enterprise Template - User Cleanup Maintenance Script"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be cleaned up without actually doing it'
    )

    parser.add_argument(
        '--days-inactive',
        type=int,
        default=90,
        help='Days since last login to consider user inactive (default: 90)'
    )

    parser.add_argument(
        '--days-never-logged-in',
        type=int,
        default=30,
        help='Days since account creation for users who never logged in (default: 30)'
    )

    parser.add_argument(
        '--audit-retention-days',
        type=int,
        default=365,
        help='Number of days to retain audit logs (default: 365)'
    )

    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only generate statistics report, no cleanup'
    )

    args = parser.parse_args()

    # Print header
    print("Flask Enterprise Template - User Cleanup Script")
    print("=" * 50)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be modified")

    if args.stats_only:
        print("📊 STATISTICS ONLY MODE")

    print()

    try:
        with UserCleanupManager(dry_run=args.dry_run) as cleanup_manager:
            if args.stats_only:
                cleanup_manager.generate_user_statistics()
            else:
                success = cleanup_manager.run_full_cleanup(
                    days_inactive=args.days_inactive,
                    days_never_logged_in=args.days_never_logged_in,
                    audit_retention_days=args.audit_retention_days
                )

                if success:
                    print("\n✅ Cleanup completed successfully")
                    sys.exit(0)
                else:
                    print("\n❌ Cleanup failed")
                    sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()