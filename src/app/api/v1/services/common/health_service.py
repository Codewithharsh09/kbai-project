"""
Health Monitoring Service for Flask Enterprise Template

This module provides comprehensive health monitoring capabilities including:
- System resource monitoring
- Database health checks
- External service health checks
- Application health monitoring
- Performance metrics

Author: Flask Enterprise Template
License: MIT
"""

import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import current_app, request
from src.extensions import db
from src.config import get_config
from src.common.localization import get_message


class HealthService:
    """Service for comprehensive health monitoring"""
    
    def __init__(self):
        self.config = get_config()
        self.start_time = datetime.utcnow()
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get basic system health status.
        
        Returns:
            dict: System health information
        """
        try:
            # Check database connection
            db_healthy, db_message = self._check_database_health()
            
            # Check system resources
            system_health = self._check_system_resources()
            
            # Determine overall health
            overall_status = 'healthy'
            if not db_healthy or system_health['status'] != 'healthy':
                overall_status = 'degraded'
            
            return {
                'status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'version': 'v1',
                'uptime': str(datetime.utcnow() - self.start_time),
                'checks': {
                    'database': {
                        'status': 'healthy' if db_healthy else 'unhealthy',
                        'message': db_message
                    },
                    'system': system_health
                }
            }
        except Exception as e:
            current_app.logger.error(f"Health check failed: {str(e)}")
            locale = request.headers.get('Accept-Language', 'en')
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': 'v1',
                'error': get_message('health_check_failed', locale, error=str(e))
            }
    
    def get_detailed_health(self) -> Dict[str, Any]:
        """
        Get detailed system health information.
        
        Returns:
            dict: Detailed health information
        """
        basic_health = self.get_system_health()
        
        # Add application-specific health checks
        try:
            app_health = self._check_application_health()
            basic_health['checks']['application'] = app_health
        except Exception as e:
            basic_health['checks']['application'] = {
                'status': 'unhealthy',
                'message': get_message('app_health_check_failed', request.headers.get('Accept-Language', 'en'), error=str(e))
            }
        
        # Add external service health checks
        try:
            external_health = self._check_external_services()
            basic_health['checks']['external_services'] = external_health
        except Exception as e:
            basic_health['checks']['external_services'] = {
                'status': 'unhealthy',
                'message': get_message('external_service_check_failed', request.headers.get('Accept-Language', 'en'), error=str(e))
            }
        
        # Add performance metrics
        try:
            performance_metrics = self._get_performance_metrics()
            basic_health['performance'] = performance_metrics
        except Exception as e:
            current_app.logger.warning(f"Performance metrics collection failed: {str(e)}")
        
        return basic_health
    
    def _check_database_health(self) -> tuple[bool, str]:
        """
        Check database connection health.
        
        Returns:
            tuple: (is_healthy, message)
        """
        locale = request.headers.get('Accept-Language', 'en')
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db.session.commit()
            
            # Get database statistics
            try:
                # This is a simple query to test database responsiveness
                result = db.session.execute('SELECT COUNT(*) FROM sqlite_master').scalar()
                return True, get_message('db_connection_healthy_with_count', locale, count=result)
            except Exception:
                return True, get_message('db_connection_healthy', locale)
                
        except Exception as e:
            return False, get_message('db_connection_failed', locale, error=str(e))
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """
        Check system resource usage.
        
        Returns:
            dict: System resource information
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Determine system health
            status = 'healthy'
            if cpu_percent > 80 or memory.percent > 80 or disk.percent > 90:
                status = 'degraded'
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = 'critical'
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'free': disk.free,
                    'percent': disk.percent,
                    'used': disk.used
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)  # System errors might be hard to translate directly without specifics
            }
    
    def _check_application_health(self) -> Dict[str, Any]:
        """
        Check application-specific health.
        
        Returns:
            dict: Application health information
        """
        try:
            # Check if we can import and use key modules
            from src.models.auth import User
            
            # Try to get user count (this tests database connectivity)
            user_count = User.query.count()
            
            # Check configuration
            config_healthy = self._check_configuration()
            
            return {
                'status': 'healthy',
                'user_count': user_count,
                'configuration': config_healthy,
                'message': get_message('app_running_with_users', request.headers.get('Accept-Language', 'en'), count=user_count)
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': get_message('app_health_check_failed', request.headers.get('Accept-Language', 'en'), error=str(e))
            }
    
    def _check_external_services(self) -> Dict[str, Any]:
        """
        Check external service health.
        
        Returns:
            dict: External service health information
        """
        services = {}
        
        # Check email service
        try:
            email_healthy = self._check_email_service()
            msg_key = 'email_service_configured' if email_healthy else 'email_service_not_configured'
            services['email'] = {
                'status': 'healthy' if email_healthy else 'unhealthy',
                'message': get_message(msg_key, request.headers.get('Accept-Language', 'en'))
            }
        except Exception as e:
            services['email'] = {
                'status': 'unhealthy',
                'message': get_message('email_service_check_failed', request.headers.get('Accept-Language', 'en'), error=str(e))
            }
        
        # Check AI services
        try:
            ai_healthy = self._check_ai_services()
            msg_key = 'ai_services_configured' if ai_healthy else 'ai_services_not_configured'
            services['ai_services'] = {
                'status': 'healthy' if ai_healthy else 'unhealthy',
                'message': get_message(msg_key, request.headers.get('Accept-Language', 'en'))
            }
        except Exception as e:
            services['ai_services'] = {
                'status': 'unhealthy',
                'message': get_message('ai_services_check_failed', request.headers.get('Accept-Language', 'en'), error=str(e))
            }
        
        return services
    
    def _check_configuration(self) -> Dict[str, Any]:
        """
        Check application configuration.
        
        Returns:
            dict: Configuration health information
        """
        config_issues = []
        locale = request.headers.get('Accept-Language', 'en')
        
        # Check required configuration
        if not current_app.config.get('SECRET_KEY') or current_app.config.get('SECRET_KEY') == 'dev-key-change-in-production':
            config_issues.append(get_message('secret_key_not_configured', locale))
        
        if not current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('JWT_SECRET_KEY') == 'jwt-dev-key-change-in-production':
            config_issues.append(get_message('jwt_secret_key_not_configured', locale))
        
        if not current_app.config.get('DATABASE_URL_DB'):
            config_issues.append(get_message('db_url_not_configured', locale))
        
        return {
            'status': 'healthy' if not config_issues else 'unhealthy',
            'issues': config_issues
        }
    
    def _check_email_service(self) -> bool:
        """
        Check if email service is configured.
        
        Returns:
            bool: True if email service is configured
        """
        return bool(current_app.config.get('GMAIL_ADDRESS') and current_app.config.get('GMAIL_PASSWORD'))
    
    def _check_ai_services(self) -> bool:
        """
        Check if AI services are configured.
        
        Returns:
            bool: True if at least one AI service is configured
        """
        return bool(current_app.config.get('OPENAI_KEY') or current_app.config.get('GEMINI_API_KEY'))
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            dict: Performance metrics
        """
        try:
            # Get process information
            process = psutil.Process()
            
            return {
                'process': {
                    'pid': process.pid,
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
                },
                'uptime': str(datetime.utcnow() - self.start_time),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            current_app.logger.warning(f"Performance metrics collection failed: {str(e)}")
            return {
                'error': get_message('performance_metrics_failed', request.headers.get('Accept-Language', 'en'), error=str(e)),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of health status.
        
        Returns:
            dict: Health summary
        """
        health = self.get_system_health()
        
        # Count healthy vs unhealthy checks
        healthy_checks = 0
        total_checks = 0
        
        for check_name, check_data in health.get('checks', {}).items():
            if isinstance(check_data, dict) and 'status' in check_data:
                total_checks += 1
                if check_data['status'] == 'healthy':
                    healthy_checks += 1
        
        return {
            'overall_status': health['status'],
            'healthy_checks': healthy_checks,
            'total_checks': total_checks,
            'health_percentage': (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            'timestamp': health['timestamp']
        }
    
    def is_healthy(self) -> bool:
        """
        Check if the system is healthy.
        
        Returns:
            bool: True if system is healthy
        """
        health = self.get_system_health()
        return health['status'] == 'healthy'
    
    def get_health_status_code(self) -> int:
        """
        Get appropriate HTTP status code for health status.
        
        Returns:
            int: HTTP status code
        """
        health = self.get_system_health()
        
        if health['status'] == 'healthy':
            return 200
        elif health['status'] == 'degraded':
            return 200  # Still operational
        else:
            return 503  # Service unavailable
