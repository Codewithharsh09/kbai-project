"""
Comprehensive Test Suite for Health Service
Tests system health monitoring, database checks, and external services
"""
import pytest
from unittest.mock import patch, MagicMock
from src.app.api.v1.services.common.health_service import HealthService
from unittest.mock import MagicMock, patch
from src.app.api.v1.services.common.health_service import HealthService


class TestHealthService:
    """Test Health Service functionality"""
    
    @patch('flask.current_app')
    def test_health_service_initialization(self, mock_current_app):
        """Unit: Service initializes correctly"""
        service = HealthService()
        assert service is not None
        assert service.config is not None
    
    @patch('flask.current_app')
    @patch('src.app.api.v1.services.common.health_service.db')
    def test_get_system_health_success(self, mock_db, mock_current_app):
        """Unit: Get system health successfully"""
        mock_current_app.config = {
            'SECRET_KEY': 'test-secret',
            'JWT_SECRET_KEY': 'test-jwt',
            'DATABASE_URL_DB': 'postgresql://test'
        }
        mock_db.engine.execute.return_value = True
        
        service = HealthService()
        health = service.get_system_health()
        
        assert 'status' in health
        assert 'timestamp' in health
    
    @patch('flask.current_app')
    def test_get_detailed_health(self, mock_current_app):
        """Unit: Get detailed health"""
        mock_current_app.config = {
            'SECRET_KEY': 'test-secret',
            'JWT_SECRET_KEY': 'test-jwt',
            'DATABASE_URL_DB': 'postgresql://test'
        }
        
        service = HealthService()
        health = service.get_detailed_health()
        
        assert 'status' in health
        assert 'checks' in health
    
    @patch('flask.current_app')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_check_system_resources(self, mock_memory, mock_cpu, mock_current_app):
        """Unit: Check system resources"""
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(
            total=1000000,
            available=500000,
            percent=50.0
        )
        
        service = HealthService()
        resources = service._check_system_resources()
        
        assert 'status' in resources or 'cpu_percent' in resources

    def test_get_system_health_degraded_when_db_unhealthy(self, app, monkeypatch):
        """Covers path where DB health fails -> overall status degraded/unhealthy."""
        hs = HealthService()

        monkeypatch.setattr(hs, '_check_database_health', lambda: (False, 'db down'))
        monkeypatch.setattr(hs, '_check_system_resources', lambda: {'status': 'healthy'})

        with app.app_context():
            result = hs.get_system_health()
            assert result['status'] in ('degraded', 'unhealthy')
            assert 'checks' in result


def test_get_detailed_health_handles_application_and_external_errors(app, monkeypatch):
    """Covers exceptions inside application/external checks and performance metrics."""
    hs = HealthService()

    monkeypatch.setattr(hs, 'get_system_health', lambda: {'status': 'healthy', 'checks': {}})
    def _raise_app():
        raise Exception('app fail')
    def _raise_ext():
        raise Exception('ext fail')
    monkeypatch.setattr(hs, '_check_application_health', _raise_app)
    monkeypatch.setattr(hs, '_check_external_services', _raise_ext)
    monkeypatch.setattr(hs, '_get_performance_metrics', lambda: {'ok': True})

    with app.app_context():
        detailed = hs.get_detailed_health()
        assert 'application' in detailed['checks']
        assert 'external_services' in detailed['checks']


class TestHealthServiceCoverage:
    """Additional tests to improve coverage"""
    
    @patch('flask.current_app')
    def test_get_system_health_exception_path(self, mock_current_app):
        """Test exception handling in get_system_health"""
        mock_current_app.config = {}
        mock_current_app.logger = MagicMock()
        
        service = HealthService()
        
        # Force exception by making _check_database_health fail
        with patch.object(service, '_check_database_health', side_effect=Exception("DB Error")):
            health = service.get_system_health()
            
        assert health['status'] == 'unhealthy'
        assert 'error' in health
    
    @patch('flask.current_app')
    def test_get_detailed_health_application_exception(self, mock_current_app):
        """Test application health check exception"""
        mock_current_app.config = {}
        mock_current_app.logger = MagicMock()
        
        service = HealthService()
        
        # Mock basic health to return success with proper structure
        with patch.object(service, 'get_system_health', return_value={
            'status': 'healthy',
            'checks': {'database': {'status': 'healthy'}}
        }):
            with patch.object(service, '_check_application_health', side_effect=Exception("App Error")):
                health = service.get_detailed_health()
                
        assert health['checks']['application']['status'] == 'unhealthy'
        assert 'Application health check failed' in health['checks']['application']['message']
    
    @patch('flask.current_app')
    def test_get_detailed_health_performance_exception(self, mock_current_app):
        """Test performance metrics exception"""
        mock_current_app.config = {}
        mock_current_app.logger = MagicMock()
        
        service = HealthService()
        
        # Mock basic health to return success with proper structure
        with patch.object(service, 'get_system_health', return_value={
            'status': 'healthy',
            'checks': {'database': {'status': 'healthy'}}
        }):
            with patch.object(service, '_get_performance_metrics', side_effect=Exception("Perf Error")):
                health = service.get_detailed_health()
                
        # Should still return health without performance metrics
        assert health['status'] == 'healthy'
    
    @patch('flask.current_app')
    def test_check_system_resources_success(self, mock_current_app):
        """Test system resources check success"""
        mock_current_app.config = {}
        
        service = HealthService()
        
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory', return_value=MagicMock(percent=60.0)), \
             patch('psutil.disk_usage', return_value=MagicMock(percent=40.0)):
            
            resources = service._check_system_resources()
            
        assert resources['cpu_percent'] == 50.0
        assert resources['memory']['percent'] == 60.0
        assert resources['disk']['percent'] == 40.0
        assert resources['status'] == 'healthy'
    
    @patch('flask.current_app')
    def test_check_system_resources_exception(self, mock_current_app):
        """Test system resources check exception"""
        mock_current_app.config = {}
        
        service = HealthService()
        
        with patch('psutil.cpu_percent', side_effect=Exception("PSUtil error")):
            resources = service._check_system_resources()
            
        assert resources['status'] == 'unhealthy'
        assert 'error' in resources
        assert 'PSUtil error' in resources['error']


    def test_get_health_status_code_maps_status(app, monkeypatch):
        """Covers mapping of status to HTTP codes."""
        hs = HealthService()
        monkeypatch.setattr(hs, 'get_system_health', lambda: {'status': 'healthy'})
        assert hs.get_health_status_code() == 200
        monkeypatch.setattr(hs, 'get_system_health', lambda: {'status': 'degraded'})
        assert hs.get_health_status_code() == 200
        monkeypatch.setattr(hs, 'get_system_health', lambda: {'status': 'unhealthy'})
        assert hs.get_health_status_code() == 503


class TestHealthServiceSummary:
    """Additional tests to cover get_health_summary and is_healthy."""

    def test_get_health_summary_counts_and_percentage(self, app):
        """Counts only dict checks with a 'status' key and computes percentage."""
        hs = HealthService()

        mocked_health = {
            'status': 'degraded',
            'timestamp': '2025-10-30T00:00:00Z',
            'checks': {
                'database': {'status': 'healthy'},
                'system': {'status': 'unhealthy'},
                'application': {'status': 'healthy'},
                'external_services': {'status': 'unhealthy'},
                'ignored_non_dict': 'oops',  # should be ignored
                'ignored_missing_status': {},  # should be ignored
            },
        }

        with app.app_context():
            with patch.object(hs, 'get_system_health', return_value=mocked_health):
                summary = hs.get_health_summary()

        assert summary['overall_status'] == 'degraded'
        # Only four valid dict checks with a 'status' key are counted
        assert summary['total_checks'] == 4
        assert summary['healthy_checks'] == 2
        assert summary['health_percentage'] == 50.0
        assert summary['timestamp'] == mocked_health['timestamp']

    def test_get_health_summary_when_no_checks(self, app):
        """Handles zero checks without division by zero (percentage 0)."""
        hs = HealthService()

        mocked_health = {
            'status': 'healthy',
            'timestamp': '2025-10-30T00:00:00Z',
            'checks': {},
        }

        with app.app_context():
            with patch.object(hs, 'get_system_health', return_value=mocked_health):
                summary = hs.get_health_summary()

        assert summary['overall_status'] == 'healthy'
        assert summary['total_checks'] == 0
        assert summary['healthy_checks'] == 0
        assert summary['health_percentage'] == 0

    def test_is_healthy_true_and_false(self, app):
        """Covers boolean mapping in is_healthy() for both outcomes."""
        hs = HealthService()

        with app.app_context():
            with patch.object(hs, 'get_system_health', return_value={'status': 'healthy'}):
                assert hs.is_healthy() is True

            with patch.object(hs, 'get_system_health', return_value={'status': 'unhealthy'}):
                assert hs.is_healthy() is False
                
if __name__ == '__main__':
    pytest.main([__file__, '-v'])          