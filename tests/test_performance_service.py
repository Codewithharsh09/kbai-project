"""
Comprehensive Test Suite for Performance Service
Tests database query monitoring and optimization
"""
import pytest
from unittest.mock import patch, MagicMock
from src.app.api.v1.services.common.performance_service import PerformanceService
from src.app.api.v1.services.common.performance_service import PerformanceService


class TestPerformanceService:
    """Test Performance Service functionality"""
    
    def test_performance_service_initialization(self):
        """Unit: Service initializes correctly"""
        service = PerformanceService()
        assert service is not None
        assert service.query_times == []
        assert service.slow_queries == []
        assert service.query_counts == {}
    
    def test_log_query_time_normal(self):
        """Unit: Log normal query time"""
        service = PerformanceService()
        service.log_query_time(0.05, "SELECT * FROM users")
        
        assert len(service.query_times) == 1
        assert len(service.slow_queries) == 0
    
    def test_log_query_time_slow(self):
        """Unit: Log slow query time"""
        service = PerformanceService()
        service.log_query_time(0.15, "SELECT * FROM users")
        
        assert len(service.query_times) == 1
        assert len(service.slow_queries) == 1
    
    def test_get_performance_stats_with_queries(self):
        """Unit: Get performance stats with queries"""
        service = PerformanceService()
        service.log_query_time(0.1)
        service.log_query_time(0.2)
        service.log_query_time(0.3)
        
        stats = service.get_performance_stats()
        
        assert stats['total_queries'] == 3
        assert 'average_time' in stats
        assert 'max_time' in stats
        assert 'min_time' in stats
    
    def test_get_performance_stats_no_queries(self):
        """Unit: Get performance stats with no queries"""
        service = PerformanceService()
        stats = service.get_performance_stats()
        
        assert 'message' in stats
        assert 'No queries executed yet' in stats['message']

    def test_log_query_time_tracks_and_flags_slow(self, app):
        svc = PerformanceService()
        with app.app_context():
            svc.log_query_time(0.05, "SELECT 1")
            svc.log_query_time(0.2, "SELECT 2")
            stats = svc.get_performance_stats()
            assert stats['total_queries'] == 2
            assert stats['slow_queries_count'] == 1

    def test_monitor_query_decorator_records_time(self, app):
        svc = PerformanceService()

        @svc.monitor_query
        def dummy():
            return 42

        with app.app_context():
            assert dummy() == 42
            stats = svc.get_performance_stats()
            assert stats['total_queries'] >= 1

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
