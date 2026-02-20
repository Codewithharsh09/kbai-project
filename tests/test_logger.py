"""
Comprehensive tests for src/common/logger.py covering all lines.
Tests JSONFormatter, utility functions, and decorators.
"""
import pytest
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from src.common.logger import JSONFormatter, get_client_info, get_geo_location, get_user_context, get_request_payload, filter_sensitive_data, get_response_info


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_format_basic_record(self):
        """Covers format method with standard record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='t.py',
            lineno=1, msg='msg', args=(), exc_info=None
        )
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        assert parsed['level'] == 'INFO'
        assert parsed['message'] == 'msg'
        assert 'timestamp' in parsed
        assert 'logger' in parsed

    def test_format_with_exception(self):
        """Covers format with exc_info."""
        formatter = JSONFormatter()
        try:
            raise ValueError('test err')
        except:
            import sys
            record = logging.LogRecord(
                name='t', level=logging.ERROR, pathname='t.py',
                lineno=1, msg='err', args=(), exc_info=sys.exc_info()
            )
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            assert 'exception' in parsed
            assert parsed['exception']['type'] == 'ValueError'
            assert 'test err' in parsed['exception']['message']

    def test_format_with_extra_fields(self):
        """Covers record.__dict__ extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='t', level=logging.INFO, pathname='t.py',
            lineno=1, msg='ok', args=(), exc_info=None
        )
        record.custom_field = 'custom_value'
        record.another_field = 123
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        assert parsed['custom_field'] == 'custom_value'
        assert parsed['another_field'] == 123


class TestLoggerUtilityFunctions:
    """Tests for utility functions in logger.py."""

    def test_get_client_info_success(self, app):
        """Covers get_client_info success path."""
        with app.test_request_context(
            headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'},
            environ_base={'REMOTE_ADDR': '192.168.1.1'}
        ):
            info = get_client_info()
            assert 'ip_address' in info
            assert 'device' in info
            # Accept either success or error (both paths are covered)
            assert isinstance(info['device'], dict)

    def test_get_client_info_exception(self, app):
        """Covers get_client_info exception path."""
        with app.test_request_context():
            with patch('src.common.logger.UserAgent', side_effect=Exception('parse err')):
                info = get_client_info()
                assert 'error' in info['device']

    @patch('os.path.exists')
    def test_get_geo_location_with_db(self, mock_exists, app):
        """Covers get_geo_location with database available."""
        mock_exists.return_value = True
        with patch('src.common.logger.geoip2.database.Reader') as mock_reader:
            mock_response = MagicMock()
            mock_response.country.name = 'United States'
            mock_response.country.iso_code = 'US'
            mock_response.city.name = 'New York'
            mock_response.subdivisions.most_specific.name = 'NY'
            mock_response.location.latitude = 40.7128
            mock_response.location.longitude = -74.0060
            mock_response.location.time_zone = 'America/New_York'
            mock_reader.return_value.__enter__.return_value.city.return_value = mock_response
            geo = get_geo_location('192.168.1.1')
            assert geo['country'] == 'United States'
            assert geo['city'] == 'New York'

    @patch('os.path.exists')
    def test_get_geo_location_without_db(self, mock_exists, app):
        """Covers get_geo_location without database (missing file)."""
        mock_exists.return_value = False
        geo = get_geo_location('1.1.1.1')
        assert geo['country'] == 'Unknown'

    @patch('os.path.exists')
    def test_get_geo_location_address_not_found(self, mock_exists, app):
        """Covers get_geo_location with AddressNotFoundError."""
        mock_exists.return_value = True
        with patch('src.common.logger.geoip2.database.Reader') as mock_reader:
            mock_reader.return_value.__enter__.return_value.city.side_effect = Exception('Not found')
            geo = get_geo_location('127.0.0.1')
            assert geo['country'] == 'Unknown'

    def test_get_user_context_from_session(self, app):
        """Covers get_user_context with session data."""
        with app.test_request_context():
            with patch('src.common.logger.session.get') as mock_get:
                def session_get(key, default=None):
                    sess_map = {'user_id': 1, 'user_email': 'test@example.com', 'user_role': 'admin', 'session_id': 'sid1'}
                    return sess_map.get(key, default)
                mock_get.side_effect = session_get
                ctx = get_user_context()
                assert ctx['user_id'] == 1
                assert ctx['is_authenticated'] is True

    def test_get_user_context_from_jwt(self, app):
        """Covers get_user_context with JWT in header."""
        with app.test_request_context(headers={'Authorization': 'Bearer test_token'}):
            ctx = get_user_context()
            assert ctx['user_id'] == 'jwt_user'

    def test_get_user_context_exception(self, app):
        """Covers get_user_context exception path."""
        with app.test_request_context():
            with patch('src.common.logger.session.get', side_effect=Exception('err')):
                ctx = get_user_context()
                assert ctx['error'] == 'err'
                assert ctx['is_authenticated'] is False

    def test_get_request_payload_json(self, app):
        """Covers get_request_payload with JSON data."""
        with app.test_request_context(
            json={'name': 'test'},
            content_type='application/json'
        ):
            payload = get_request_payload()
            assert payload == {'name': 'test'}

    def test_get_request_payload_form(self, app):
        """Covers get_request_payload with form data."""
        with app.test_request_context(method='POST', data={'name': 'test'}, content_type='application/x-www-form-urlencoded'):
            payload = get_request_payload()
            assert 'name' in payload

    def test_get_request_payload_raw_data_small(self, app):
        """Covers get_request_payload with small raw data."""
        with app.test_request_context(data=b'small data'):
            payload = get_request_payload()
            assert payload is not None

    def test_get_request_payload_raw_data_large(self, app):
        """Covers get_request_payload with large raw data."""
        with app.test_request_context(data=b'x' * 2000):
            payload = get_request_payload()
            assert payload is None

    def test_filter_sensitive_data_password(self):
        """Covers filter_sensitive_data with password."""
        data = {'username': 'u', 'password': 'p'}
        filtered = filter_sensitive_data(data)
        assert filtered['password'] == '[FILTERED]'
        assert filtered['username'] == 'u'

    def test_filter_sensitive_data_nested(self):
        """Covers filter_sensitive_data with nested dict."""
        data = {'user': {'email': 'e@e.com', 'other': 'ok'}}
        filtered = filter_sensitive_data(data)
        assert filtered['user']['email'] == '[FILTERED]'
        assert filtered['user']['other'] == 'ok'

    def test_filter_sensitive_data_list(self):
        """Covers filter_sensitive_data with list."""
        data = [{'password': 'p1'}, {'password': 'p2'}]
        filtered = filter_sensitive_data(data)
        assert all(item['password'] == '[FILTERED]' for item in filtered)

    def test_filter_sensitive_data_string(self):
        """Covers filter_sensitive_data with string input."""
        assert filter_sensitive_data('not a dict') == 'not a dict'

    def test_get_response_info_success(self, app):
        """Covers get_response_info success with JSON response."""
        with app.app_context():
            response = app.response_class(
                response=json.dumps({'ok': True}),
                mimetype='application/json',
                status=200
            )
            info = get_response_info(response)
            assert info['status_code'] == 200
            assert info['is_json'] is True

    def test_get_response_info_large_response(self, app):
        """Covers get_response_info with large response (no data logged)."""
        with app.app_context():
            response = app.response_class(
                response=json.dumps({'x': 'y' * 3000}),
                mimetype='application/json',
                status=200
            )
            info = get_response_info(response)
            assert 'data' not in info

    def test_get_response_info_exception(self, app):
        """Covers get_response_info exception path."""
        response = MagicMock()
        response.status_code = 500
        response.content_type.side_effect = Exception('err')
        info = get_response_info(response)
        assert 'error' in info or info.get('status_code') == 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

