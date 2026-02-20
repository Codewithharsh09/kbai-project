"""
Performance Monitoring Service
Tracks and optimizes database query performance
"""

import time
from typing import Dict, Any, Callable
from functools import wraps
from flask import current_app
from sqlalchemy import event
from sqlalchemy.engine import Engine

class PerformanceService:
    """Service for monitoring and optimizing database performance"""
    
    def __init__(self):
        self.query_times = []
        self.slow_queries = []
        self.query_counts = {}
    
    def log_query_time(self, query_time: float, query: str = None):
        """Log query execution time"""
        self.query_times.append(query_time)
        
        # Track slow queries (>100ms)
        if query_time > 0.1:
            self.slow_queries.append({
                'time': query_time,
                'query': query,
                'timestamp': time.time()
            })
            current_app.logger.warning(f"Slow query detected: {query_time:.3f}s - {query}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.query_times:
            return {'message': 'No queries executed yet'}
        
        avg_time = sum(self.query_times) / len(self.query_times)
        max_time = max(self.query_times)
        min_time = min(self.query_times)
        
        return {
            'total_queries': len(self.query_times),
            'average_time': round(avg_time, 3),
            'max_time': round(max_time, 3),
            'min_time': round(min_time, 3),
            'slow_queries_count': len(self.slow_queries),
            'slow_queries': self.slow_queries[-10:]  # Last 10 slow queries
        }
    
    def monitor_query(self, func: Callable) -> Callable:
        """Decorator to monitor query performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            query_time = end_time - start_time
            self.log_query_time(query_time, func.__name__)
            
            return result
        return wrapper

# Initialize performance service
performance_service = PerformanceService()

# SQLAlchemy event listeners for query monitoring
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query start time"""
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query end time and performance"""
    if hasattr(context, '_query_start_time'):
        query_time = time.time() - context._query_start_time
        performance_service.log_query_time(query_time, statement[:100])  # First 100 chars

# Performance monitoring decorator
def monitor_performance(func: Callable) -> Callable:
    """Decorator for monitoring function performance"""
    return performance_service.monitor_query(func)
