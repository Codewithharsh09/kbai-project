"""
Health Check Routes

Provides health check endpoints for monitoring system status
"""

from flask import Blueprint, request
from flask_restx import Api, Resource, Namespace
from src.common.response_utils import success_response, error_response
from src.common.localization import get_message
from src.app.api.v1.services import HealthService

# Create blueprint
health_bp = Blueprint('health', __name__)

# Create namespace for health routes
health_ns = Namespace('health', description='Health check operations')

# Add namespace to blueprint
api = Api(health_bp)
api.add_namespace(health_ns)


@health_ns.route('/')
class HealthCheck(Resource):
    """Basic health check endpoint"""
    
    @health_ns.doc('health_check')
    def get(self):
        """Get basic system health status"""
        locale = request.headers.get('Accept-Language', 'en')
        try:
            health_service = HealthService()
            health_data = health_service.get_system_health()
            status_code = health_service.get_health_status_code()
            
            if status_code == 200:
                return success_response(
                    message=get_message('health_system_healthy', locale),
                    data=health_data
                )
            else:
                return error_response(
                    message=get_message('health_check_failed', locale),
                    data=health_data,
                    status_code=status_code
                )
        except Exception as e:
            return error_response(
                message=get_message('health_check_failed', locale),
                data={"error": str(e)},
                status_code=500
            )


@health_ns.route('/detailed')
class DetailedHealthCheck(Resource):
    """Detailed health check endpoint"""
    
    @health_ns.doc('detailed_health_check')
    def get(self):
        """Get detailed system health status"""
        locale = request.headers.get('Accept-Language', 'en')
        try:
            health_service = HealthService()
            health_data = health_service.get_detailed_health()
            status_code = health_service.get_health_status_code()
            
            if status_code == 200:
                return success_response(
                    message=get_message('health_detailed_success', locale),
                    data=health_data
                )
            else:
                return error_response(
                    message=get_message('health_detailed_failed', locale),
                    data=health_data,
                    status_code=status_code
                )
        except Exception as e:
            return error_response(
                message=get_message('health_detailed_failed', locale),
                data={"error": str(e)},
                status_code=500
            )


@health_ns.route('/summary')
class HealthSummary(Resource):
    """Health summary endpoint"""
    
    @health_ns.doc('health_summary')
    def get(self):
        """Get health summary"""
        locale = request.headers.get('Accept-Language', 'en')
        try:
            health_service = HealthService()
            summary_data = health_service.get_health_summary()
            return success_response(
                message=get_message('health_summary_success', locale),
                data=summary_data
            )
        except Exception as e:
            return error_response(
                message=get_message('health_summary_failed', locale),
                data={"error": str(e)},
                status_code=500
            )
