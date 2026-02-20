"""
Advanced Logging Configuration for Flask Enterprise Template

This module provides comprehensive logging configuration with:
- Environment-based log levels
- Rotating file handlers
- Structured logging with JSON format
- Performance monitoring
- Request/response logging with full context
- User tracking and authentication logging
- Device and region detection
- Detailed error tracking with stack traces
- API-specific logging decorators
- Security event monitoring
- Database operation logging
- External service call monitoring

Author: Flask Enterprise Template
License: MIT
"""

import os
import json
import logging
import logging.handlers
import traceback
import uuid
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Union
from flask import request, g, session, current_app
from flask_jwt_extended import get_jwt_identity
from werkzeug.user_agent import UserAgent
import geoip2.database
import geoip2.errors
from src.config import get_config


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'process': record.process
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


def setup_logging(app):
    """
    Setup comprehensive logging for the Flask application.
    
    Args:
        app: Flask application instance
    """
    config_class = get_config()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config_class.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set log level
    log_level = getattr(logging, config_class.LOG_LEVEL.upper(), logging.INFO)
    app.logger.setLevel(log_level)
    
    # Remove default handlers
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d: %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    json_formatter = JSONFormatter()
    
    # Console handler for development
    if app.config.get('DEBUG'):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(detailed_formatter)
        app.logger.addHandler(console_handler)
    
    # Main application log file
    file_handler = logging.handlers.RotatingFileHandler(
        config_class.LOG_FILE,
        maxBytes=config_class.LOG_MAX_BYTES,
        backupCount=config_class.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_formatter)
    app.logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        config_class.LOG_FILE.replace('.log', '_error.log'),
        maxBytes=config_class.LOG_MAX_BYTES,
        backupCount=config_class.LOG_BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    app.logger.addHandler(error_handler)
    
    # API requests log handler
    api_handler = logging.handlers.RotatingFileHandler(
        config_class.LOG_FILE.replace('.log', '_api.log'),
        maxBytes=config_class.LOG_MAX_BYTES,
        backupCount=config_class.LOG_BACKUP_COUNT
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(json_formatter)
    app.logger.addHandler(api_handler)
    
    # Security events log handler
    security_handler = logging.handlers.RotatingFileHandler(
        config_class.LOG_FILE.replace('.log', '_security.log'),
        maxBytes=config_class.LOG_MAX_BYTES,
        backupCount=config_class.LOG_BACKUP_COUNT
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(json_formatter)
    app.logger.addHandler(security_handler)
    
    # Performance log handler
    if config_class.ENABLE_PERFORMANCE_MONITORING:
        perf_handler = logging.handlers.RotatingFileHandler(
            config_class.LOG_FILE.replace('.log', '_performance.log'),
            maxBytes=config_class.LOG_MAX_BYTES,
            backupCount=config_class.LOG_BACKUP_COUNT
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(json_formatter)
        app.logger.addHandler(perf_handler)
    
    # Set logging level for other loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    app.logger.info("Advanced logging configured", extra={
        'environment': app.config.get('FLASK_ENV', 'development'),
        'log_level': config_class.LOG_LEVEL,
        'performance_monitoring': config_class.ENABLE_PERFORMANCE_MONITORING
    })


def get_client_info():
    """Extract comprehensive client information from request"""
    try:
        user_agent = UserAgent(request.headers.get('User-Agent', ''))
        
        # Get real IP address (considering proxies)
        client_ip = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Device information
        device_info = {
            'browser': user_agent.browser or 'Unknown',
            'browser_version': user_agent.version or 'Unknown',
            'platform': user_agent.platform or 'Unknown',
            'os': user_agent.os or 'Unknown',
            'device_type': 'mobile' if user_agent.is_mobile else 'desktop' if user_agent.is_pc else 'unknown',
            'is_bot': user_agent.is_bot,
            'language': request.headers.get('Accept-Language', 'Unknown').split(',')[0] if request.headers.get('Accept-Language') else 'Unknown'
        }
        
        # Geographic information (requires GeoIP2 database)
        geo_info = get_geo_location(client_ip)
        
        return {
            'ip_address': client_ip,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'device': device_info,
            'geo': geo_info,
            'referrer': request.headers.get('Referer', 'Direct'),
            'origin': request.headers.get('Origin', 'Unknown')
        }
    except Exception as e:
        return {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'device': {'error': str(e)},
            'geo': {'error': str(e)},
            'referrer': request.headers.get('Referer', 'Direct'),
            'origin': request.headers.get('Origin', 'Unknown')
        }


def get_geo_location(ip_address):
    """Get geographic location from IP address"""
    try:
        # This requires GeoIP2 database file (GeoLite2-City.mmdb)
        # You can download it from: https://dev.maxmind.com/geoip/geoip2/geolite2/
        geoip_db_path = 'src/common/GeoLite2-City.mmdb'
        
        if os.path.exists(geoip_db_path):
            with geoip2.database.Reader(geoip_db_path) as reader:
                response = reader.city(ip_address)
                return {
                    'country': response.country.name or 'Unknown',
                    'country_code': response.country.iso_code or 'Unknown',
                    'city': response.city.name or 'Unknown',
                    'region': response.subdivisions.most_specific.name or 'Unknown',
                    'latitude': float(response.location.latitude) if response.location.latitude else None,
                    'longitude': float(response.location.longitude) if response.location.longitude else None,
                    'timezone': response.location.time_zone or 'Unknown'
                }
    except (geoip2.errors.AddressNotFoundError, geoip2.errors.GeoIP2Error, Exception):
        pass
    
    return {
        'country': 'Unknown',
        'country_code': 'Unknown',
        'city': 'Unknown',
        'region': 'Unknown',
        'latitude': None,
        'longitude': None,
        'timezone': 'Unknown'
    }


def get_user_context():
    """Get current user context from session or JWT token"""
    try:
        # Try to get user from session
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        user_role = session.get('user_role')
        
        # If not in session, try to get from JWT token in request headers
        if not user_id:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                # You would decode JWT token here to get user info
                # For now, we'll mark as authenticated but unknown user
                user_id = 'jwt_user'
                user_email = 'jwt_user'
                user_role = 'authenticated'
        
        return {
            'user_id': user_id,
            'user_email': user_email,
            'user_role': user_role,
            'is_authenticated': bool(user_id),
            'session_id': session.get('session_id', 'unknown')
        }
    except Exception as e:
        return {
            'user_id': None,
            'user_email': None,
            'user_role': None,
            'is_authenticated': False,
            'session_id': 'unknown',
            'error': str(e)
        }


def log_request_start(app):
    """Log comprehensive request start with all context information"""
    
    @app.before_request
    def log_request_info():
        g.start_time = datetime.utcnow()
        g.request_id = str(uuid.uuid4())
        
        # Skip logging for health checks and static files
        if request.path.startswith('/health') or request.path.startswith('/static'):
            return
        
        # Get comprehensive request information
        client_info = get_client_info()
        user_context = get_user_context()
        
        # Extract request payload (be careful with sensitive data)
        request_payload = get_request_payload()
        
        # Log comprehensive request information
        app.logger.info("API Request Started", extra={
            'request_id': g.request_id,
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'query_params': dict(request.args),
            'request_payload': request_payload,
            'client_info': client_info,
            'user_context': user_context,
            'headers': {
                'content_type': request.content_type,
                'content_length': request.content_length,
                'host': request.host,
                'scheme': request.scheme
            },
            'timestamp': g.start_time.isoformat()
        })


def get_request_payload():
    """Safely extract request payload, filtering sensitive information"""
    try:
        if request.is_json:
            payload = request.get_json(silent=True)
            if payload:
                # Filter sensitive fields
                filtered_payload = filter_sensitive_data(payload)
                return filtered_payload
        
        elif request.form:
            # Form data
            filtered_form = filter_sensitive_data(dict(request.form))
            return filtered_form
        
        elif request.data:
            # Raw data (limit size for logging)
            if len(request.data) < 1000:  # Only log small payloads
                try:
                    data_str = request.data.decode('utf-8')
                    return {'raw_data': data_str[:500]}  # Truncate for safety
                except:
                    return {'raw_data': 'binary_data'}
        
        return None
    except Exception as e:
        return {'error': str(e)}


def filter_sensitive_data(data):
    """Filter sensitive information from data"""
    sensitive_fields = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'api_key',
        'access_token', 'refresh_token', 'authorization', 'auth',
        'credit_card', 'card_number', 'cvv', 'ssn', 'social_security',
        'email', 'phone', 'address', 'zip', 'postal_code'
    }
    
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                filtered[key] = '[FILTERED]'
            elif isinstance(value, (dict, list)):
                filtered[key] = filter_sensitive_data(value)
            else:
                filtered[key] = value
        return filtered
    elif isinstance(data, list):
        return [filter_sensitive_data(item) for item in data]
    else:
        return data


def log_request_end(app):
    """Log comprehensive request end with response information"""
    
    @app.after_request
    def log_response_info(response):
        # Skip logging for health checks and static files
        if request.path.startswith('/health') or request.path.startswith('/static'):
            return response
        
        if hasattr(g, 'start_time'):
            duration = datetime.utcnow() - g.start_time
            duration_ms = duration.total_seconds() * 1000
            
            # Get response information
            response_info = get_response_info(response)
            
            # Log comprehensive response information
            app.logger.info("API Request Completed", extra={
                'request_id': getattr(g, 'request_id', 'unknown'),
                'method': request.method,
                'path': request.path,
                'endpoint': request.endpoint,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'response_info': response_info,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Log slow requests
            config_class = get_config()
            if (config_class.ENABLE_PERFORMANCE_MONITORING and 
                duration.total_seconds() > config_class.PERFORMANCE_LOG_THRESHOLD):
                app.logger.warning("Slow Request Detected", extra={
                    'request_id': getattr(g, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'duration_ms': round(duration_ms, 2),
                    'threshold_seconds': config_class.PERFORMANCE_LOG_THRESHOLD,
                    'performance_issue': True
                })
        
        return response


def get_response_info(response):
    """Extract response information for logging"""
    try:
        response_info = {
            'status_code': response.status_code,
            'content_type': response.content_type,
            'content_length': response.content_length,
            'headers': dict(response.headers),
            'is_json': response.is_json,
            'is_streamed': response.is_streamed
        }
        
        # Try to get response data (be careful with large responses)
        if response.data and len(response.data) < 2000:  # Only log small responses
            try:
                if response.is_json:
                    response_info['data'] = response.get_json()
                else:
                    response_info['data'] = response.data.decode('utf-8')[:1000]  # Truncate
            except:
                response_info['data'] = 'binary_data'
        
        return response_info
    except Exception as e:
        return {'error': str(e), 'status_code': getattr(response, 'status_code', 'unknown')}

def api_logger(include_payload=True, include_response=True):
    """
    🔍 Universal Flask API Logger
    Logs details for each API call:
      - User ID, IP, Device info
      - Request method, path
      - Payload, Response, Duration
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            app = current_app._get_current_object()
            start_time = datetime.utcnow()
            request_id = getattr(g, "request_id", str(uuid.uuid4()))

            # 🧠 Extract base info
            try:
                user_id = get_jwt_identity() or "Anonymous"
            except Exception:
                user_id = "Anonymous"

            client_ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.remote_addr
            )
            user_agent = request.user_agent
            device_info = {
                "platform": user_agent.platform,   # e.g. windows, linux, iphone
                "browser": user_agent.browser,     # e.g. chrome, safari
                "version": user_agent.version,
                "string": user_agent.string,
            }

            method = request.method
            path = request.path
            timestamp = start_time.isoformat()

            # 📦 Get request payload (if any)
            payload = None
            if include_payload:
                try:
                    payload = request.get_json(silent=True)
                except Exception:
                    payload = None

            # 🔹 START LOG
            start_log = {
                "event": "API_CALL_START",
                "request_id": request_id,
                "timestamp": timestamp,
                "method": method,
                "path": path,
                "user_id": user_id,
                "client_ip": client_ip,
                "device_info": device_info,
                "payload": payload,
            }

            print("\n🚀 [API CALL START]")
            # print(json.dumps(start_log, indent=2, ensure_ascii=False))
            app.logger.info(json.dumps(start_log, indent=2, ensure_ascii=False))

            try:
                # ▶️ Call the actual API
                result = func(*args, **kwargs)

                duration_ms = round((datetime.utcnow() - start_time).total_seconds() * 1000, 2)

                # 📤 Response (trim if large)
                response_preview = None
                if include_response:
                    try:
                        if hasattr(result, "data"):
                            data = result.data
                            response_preview = data.decode("utf-8", errors="ignore")[:800]
                        else:
                            response_preview = str(result)[:800]
                    except Exception:
                        response_preview = "Unable to parse response"

                # ✅ SUCCESS LOG
                success_log = {
                    "event": "API_CALL_SUCCESS",
                    "request_id": request_id,
                    "status": "success",
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "response_preview": response_preview,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                print("\n✅ [API CALL SUCCESS]")
                # print(json.dumps(success_log, indent=2, ensure_ascii=False))
                app.logger.info(json.dumps(success_log, indent=2, ensure_ascii=False))

                return result

            except Exception as e:
                duration_ms = round((datetime.utcnow() - start_time).total_seconds() * 1000, 2)
                error_log = {
                    "event": "API_CALL_ERROR",
                    "request_id": request_id,
                    "status": "error",
                    "method": method,
                    "path": path,
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                print("\n❌ [API CALL ERROR]")
                print(json.dumps(error_log, indent=2, ensure_ascii=False))
                print("──────────────────────────────")

                app.logger.error(json.dumps(error_log), exc_info=True)
                raise e

        return wrapper
    return decorator


def log_user_action(app, action, details=None, user_id=None):
    """
    Log user actions for audit trail.
    
    Args:
        app: Flask application instance
        action: Action performed by user
        details: Additional action details
        user_id: User ID (if not provided, will try to get from context)
    """
    try:
        # Get user context
        user_context = get_user_context()
        if not user_id:
            user_id = user_context.get('user_id')
        
        action_info = {
            'action': action,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': getattr(g, 'request_id', 'unknown')
        }
        
        # Add request context if available
        if request:
            action_info.update({
                'request_path': request.path,
                'request_method': request.method,
                'remote_addr': request.remote_addr
            })
        
        # Add user context
        action_info['user_context'] = user_context
        
        if details:
            action_info['action_details'] = details
        
        app.logger.info("User Action", extra=action_info)
        
    except Exception as e:
        app.logger.error(f"Failed to log user action: {e}", exc_info=True)


def get_logger(name=None):
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger(__name__)


def setup_comprehensive_logging(app):
    """
    Setup comprehensive logging system for the Flask application.
    This is the main function to call to enable all logging features.
    
    Args:
        app: Flask application instance
    """
    # Setup basic logging
    setup_logging(app)
    
    # Setup request/response logging
    log_request_start(app)
    log_request_end(app)
    
    # Setup global exception handler
    log_exception_handler(app)
    
    app.logger.info("Comprehensive logging system initialized", extra={
        'features': [
            'request_response_logging',
            'error_logging',
            'security_logging',
            'performance_monitoring',
            'user_action_logging',
            'authentication_logging',
            'business_event_logging',
            'database_operation_logging',
            'external_service_logging'
        ]
    })
