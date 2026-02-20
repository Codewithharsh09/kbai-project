"""
Health Check Routes

Provides health check endpoints for monitoring system status
"""

from flask import Blueprint
from flask_restx import Api, Resource, Namespace
from src.common.response_utils import success_response, error_response
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
        try:
            health_service = HealthService()
            health_data = health_service.get_system_health()
            status_code = health_service.get_health_status_code()
            
            if status_code == 200:
                return success_response(
                    message="System is healthy",
                    data=health_data
                )
            else:
                return error_response(
                    message="System health check failed",
                    data=health_data,
                    status_code=status_code
                )
        except Exception as e:
            return error_response(
                message="Health check failed",
                data={"error": str(e)},
                status_code=500
            )


@health_ns.route('/detailed')
class DetailedHealthCheck(Resource):
    """Detailed health check endpoint"""
    
    @health_ns.doc('detailed_health_check')
    def get(self):
        """Get detailed system health status"""
        try:
            health_service = HealthService()
            health_data = health_service.get_detailed_health()
            status_code = health_service.get_health_status_code()
            
            if status_code == 200:
                return success_response(
                    message="Detailed health check completed",
                    data=health_data
                )
            else:
                return error_response(
                    message="Detailed health check failed",
                    data=health_data,
                    status_code=status_code
                )
        except Exception as e:
            return error_response(
                message="Detailed health check failed",
                data={"error": str(e)},
                status_code=500
            )


@health_ns.route('/summary')
class HealthSummary(Resource):
    """Health summary endpoint"""
    
    @health_ns.doc('health_summary')
    def get(self):
        """Get health summary"""
        try:
            health_service = HealthService()
            summary_data = health_service.get_health_summary()
            return success_response(
                message="Health summary retrieved successfully",
                data=summary_data
            )
        except Exception as e:
            return error_response(
                message="Health summary failed",
                data={"error": str(e)},
                status_code=500
            )
