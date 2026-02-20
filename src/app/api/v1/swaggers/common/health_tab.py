"""
Health Tab Swagger Documentation

Contains all health check related API documentation including:
- Basic health check
- Detailed health check
- Health summary
"""

from flask_restx import Namespace, fields

# Create Health Namespace
health_ns = Namespace('health', description='Health check operations')

# Health Check Response Models
basic_health_response_model = health_ns.model('BasicHealthResponse', {
    'status': fields.String(description='Overall system status'),
    'timestamp': fields.DateTime(description='Health check timestamp'),
    'version': fields.String(description='Application version'),
    'environment': fields.String(description='Environment (development/production)')
})

detailed_health_response_model = health_ns.model('DetailedHealthResponse', {
    'status': fields.String(description='Overall system status'),
    'timestamp': fields.DateTime(description='Health check timestamp'),
    'version': fields.String(description='Application version'),
    'environment': fields.String(description='Environment'),
    'database': fields.Raw(description='Database connection status'),
    'auth0': fields.Raw(description='Auth0 service status'),
    'email': fields.Raw(description='Email service status'),
    'cache': fields.Raw(description='Cache service status'),
    'uptime': fields.String(description='System uptime'),
    'memory_usage': fields.Raw(description='Memory usage information'),
    'disk_usage': fields.Raw(description='Disk usage information')
})

health_summary_response_model = health_ns.model('HealthSummaryResponse', {
    'overall_status': fields.String(description='Overall system health status'),
    'healthy_services': fields.Integer(description='Number of healthy services'),
    'total_services': fields.Integer(description='Total number of services'),
    'last_check': fields.DateTime(description='Last health check timestamp'),
    'response_time_ms': fields.Integer(description='Health check response time in milliseconds')
})

# Example Responses
EXAMPLE_BASIC_HEALTH = {
    "status": "healthy",
    "timestamp": "2023-12-01T15:30:00Z",
    "version": "1.0.0",
    "environment": "development"
}

EXAMPLE_DETAILED_HEALTH = {
    "status": "healthy",
    "timestamp": "2023-12-01T15:30:00Z",
    "version": "1.0.0",
    "environment": "development",
    "database": {
        "status": "healthy",
        "response_time_ms": 15,
        "connection_pool": {
            "active": 2,
            "idle": 8,
            "max": 20
        }
    },
    "auth0": {
        "status": "healthy",
        "response_time_ms": 45
    },
    "email": {
        "status": "healthy",
        "response_time_ms": 120
    },
    "cache": {
        "status": "healthy",
        "response_time_ms": 5,
        "memory_usage": "45MB"
    },
    "uptime": "2 days, 5 hours, 30 minutes",
    "memory_usage": {
        "used": "512MB",
        "total": "2GB",
        "percentage": 25.6
    },
    "disk_usage": {
        "used": "15GB",
        "total": "100GB",
        "percentage": 15.0
    }
}

EXAMPLE_HEALTH_SUMMARY = {
    "overall_status": "healthy",
    "healthy_services": 4,
    "total_services": 4,
    "last_check": "2023-12-01T15:30:00Z",
    "response_time_ms": 185
}
