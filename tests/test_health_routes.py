"""
Tests for health routes covering success and failure branches (class-based).
"""

from typing import Any, Dict
from unittest.mock import patch
import pytest



class TestHealthRoutes:
    def test_health_route_basic_success(self, app, client):
        """Covers HealthCheck.get success path with 200 code."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_system_health.return_value = {'status': 'healthy'}
            instance.get_health_status_code.return_value = 200

            resp = client.get('/api/v1/health/') if client else None
            # Some apps mount with /api/v1; fallback to /health
            if resp is None or resp.status_code == 404:
                resp = client.get('/health/')

            assert resp.status_code == 200
            data = resp.get_json()
            assert data['success'] is True
            assert data['message'] == 'System is healthy'

    def test_health_route_basic_failure(self, app, client):
        """Covers HealthCheck.get error branch with non-200 status code."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_system_health.return_value = {'status': 'unhealthy'}
            instance.get_health_status_code.return_value = 503

            resp = client.get('/api/v1/health/') if client else None
            if resp is None or resp.status_code == 404:
                resp = client.get('/health/')

            assert resp.status_code == 503
            data = resp.get_json()
            assert data['success'] is False
            assert data['message'] == 'System health check failed'

    def test_health_route_detailed_success(self, app, client):
        """Covers DetailedHealthCheck.get success path."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_detailed_health.return_value = {'checks': {}, 'status': 'healthy'}
            instance.get_health_status_code.return_value = 200

            resp = client.get('/api/v1/health/detailed')
            if resp.status_code == 404:
                resp = client.get('/health/detailed')

            assert resp.status_code == 200
            data = resp.get_json()
            assert data['success'] is True
            assert data['message'] == 'Detailed health check completed'

    def test_health_route_detailed_failure(self, app, client):
        """Covers DetailedHealthCheck.get non-200 path."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_detailed_health.return_value = {'checks': {}, 'status': 'unhealthy'}
            instance.get_health_status_code.return_value = 503

            resp = client.get('/api/v1/health/detailed')
            if resp.status_code == 404:
                resp = client.get('/health/detailed')

            assert resp.status_code == 503
            data = resp.get_json()
            assert data['success'] is False
            assert data['message'] == 'Detailed health check failed'

    def test_health_route_summary_success(self, app, client):
        """Covers HealthSummary.get normal success path."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_health_summary.return_value = {'overall_status': 'healthy'}

            resp = client.get('/api/v1/health/summary')
            if resp.status_code == 404:
                resp = client.get('/health/summary')

            assert resp.status_code == 200
            data = resp.get_json()
            assert data['success'] is True
            assert data['message'] == 'Health summary retrieved successfully'

    def test_health_route_summary_exception(self, app, client):
        """Covers HealthSummary.get exception path (500)."""
        with patch('src.app.api.v1.routes.common.health_routes.HealthService') as HS:
            instance = HS.return_value
            instance.get_health_summary.side_effect = Exception('boom')

            resp = client.get('/api/v1/health/summary')
            if resp.status_code == 404:
                resp = client.get('/health/summary')

            assert resp.status_code == 500
            data = resp.get_json()
            assert data['success'] is False
            assert data['message'] == 'Health summary failed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])