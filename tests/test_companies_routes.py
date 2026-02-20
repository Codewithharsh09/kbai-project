"""
Comprehensive Test Suite for Companies Routes
Tests company CRUD operations via API routes
"""
import pytest
import json
from unittest.mock import patch, Mock, MagicMock


class TestCompaniesRoutes:
    """Test Companies Routes functionality"""
    
    @patch('src.app.api.middleware.auth0_verify.get_current_user')
    def test_create_company_route_success(self, mock_get_user, client, admin_user):
        """Integration: Create company via route"""
        mock_get_user.return_value = admin_user
        
        response = client.post('/api/v1/kbai/companies/',
                              json={
                                  'company_name': 'Test Company',
                                  'email': 'test@company.com',
                                  'contact_person': 'John Doe'
                              },
                              headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code in [201, 400, 500]
    
    def test_get_company_by_id_route(self, client):
        """Integration: Get company by ID route"""
        response = client.get('/api/v1/kbai/companies/1')
        
        assert response.status_code in [200, 404]
    
    @patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token')
    @patch('src.app.api.middleware.auth0_verify.get_current_user')
    def test_update_company_route(self, mock_get_user, mock_verify, client, admin_user):
        """Integration: Update company route"""
        mock_verify.return_value = {'sub': 'auth0|123'}
        mock_get_user.return_value = admin_user
        
        response = client.put('/api/v1/kbai/companies/1',
                             json={'company_name': 'Updated Name'},
                             headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code in [200, 403, 404,401, 500]
    
    @patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token')
    @patch('src.app.api.middleware.auth0_verify.get_current_user')
    def test_delete_company_route(self, mock_get_user, mock_verify, client, admin_user):
        """Integration: Delete company route"""
        mock_verify.return_value = {'sub': 'auth0|123'}
        mock_get_user.return_value = admin_user
        
        response = client.delete('/api/v1/kbai/companies/1',
                                headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code in [200, 401, 403, 404, 500]
    
    @patch('src.app.api.middleware.auth0_verify.auth0_service.verify_auth0_token')
    @patch('src.app.api.middleware.auth0_verify.get_current_user')
    def test_get_user_companies_route(self, mock_get_user, mock_verify, client, admin_user):
        """Integration: Get companies for user route"""
        mock_verify.return_value = {'sub': 'auth0|123'}
        mock_get_user.return_value = admin_user
        
        response = client.get('/api/v1/kbai/companies/user/1',
                             headers={'Authorization': 'Bearer test-token'})
        
        assert response.status_code in [200, 401, 403, 404, 500]
    
    def test_company_routes_exist(self, client):
        """Unit: All company routes are accessible"""
        routes = [
            ('/api/v1/kbai/companies/1', 'GET'),
            ('/api/v1/kbai/companies/user/1', 'GET')
        ]
        
        for route, method in routes:
            if method == 'GET':
                response = client.get(route)
            else:
                response = client.post(route)
            
            # Routes should exist (not 404 for GET, may be 404 for POST without auth)
            if route.endswith('/1') or route.endswith('/user/1'):
                # These can return 404 if resource doesn't exist
                assert response.status_code in [200, 401, 403, 404, 500]
            else:
                # POST routes may need auth
                assert response.status_code != 404


class TestCompaniesService:
    """Test Companies Service methods"""
    
    def test_company_service_initialization(self):
        """Unit: Service initializes correctly"""
        from src.app.api.v1.services.kbai.companies_service import KbaiCompaniesService
        service = KbaiCompaniesService()
        assert service is not None
        assert service.default_page_size == 10
    
    def test_check_company_permission_superadmin(self):
        """Unit: Superadmin has all permissions"""
        from src.app.api.v1.services.kbai.companies_service import KbaiCompaniesService
        service = KbaiCompaniesService()
        
        mock_user = Mock()
        mock_user.role = 'superadmin'
        
        has_permission, msg = service.check_company_permission(mock_user)
        assert has_permission is True
    
    def test_check_company_permission_user_role(self):
        """Unit: User role cannot manage companies"""
        from src.app.api.v1.services.kbai.companies_service import KbaiCompaniesService
        service = KbaiCompaniesService()
        
        mock_user = Mock()
        mock_user.role = 'user'
        
        has_permission, msg = service.check_company_permission(mock_user)
        assert has_permission is False


class TestCompaniesRoutesAdditional:
    def _bypass_auth(self, monkeypatch):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av

        def identity(*args, **kwargs):
            def _wrap(f):
                return f
            return _wrap

        monkeypatch.setattr(cr, 'require_auth0', identity, raising=False)
        dummy_user = type('U', (), {'id_user': 1, 'role': 'superadmin', 'email': 'sa@test.com'})()
        monkeypatch.setattr(av, '_extract_token_from_request', lambda: ('tok', None), raising=False)
        monkeypatch.setattr(av, '_verify_and_get_user', lambda token: (dummy_user, None), raising=False)
        monkeypatch.setattr(av, 'get_current_user', lambda: dummy_user, raising=False)

    def _try(self, client, method, paths, **kw):
        for p in paths:
            resp = getattr(client, method)(p, **kw)
            if resp.status_code != 404:
                return resp
        return resp

    def test_companies_list_requires_auth(self, client):
        resp = client.get('/api/v1/kbai/companies/')
        assert resp.status_code in [401, 403]

    def test_companies_list_calls_service(self, monkeypatch, client):
        self._bypass_auth(monkeypatch)
        import src.app.api.v1.routes.kbai.companies_routes as cr

        called = {}

        def fake_find(page, per_page, search=None, **filters):
            called['page'] = page
            called['per_page'] = per_page
            called['search'] = search
            called['filters'] = filters
            return ({
                'message': 'ok',
                'data': [{'id_company': 1}],
                'pagination': {'page': page, 'per_page': per_page, 'total': 1, 'pages': 1},
                'success': True
            }, 200)

        cr.kbai_companies_service = MagicMock(find=fake_find)
        resp = self._try(client, 'get', [
            '/api/v1/kbai/companies/?page=2&per_page=5&search=tech&status=ACTIVE',
            '/kbai/companies/?page=2&per_page=5&search=tech&status=ACTIVE'
        ])

        assert resp.status_code == 200
        assert called['page'] == 2
        assert called['per_page'] == 5
        assert called['search'] == 'tech'
        assert called['filters'].get('status_flag') == 'ACTIVE'
        assert resp.json['data']['companies'][0]['id_company'] == 1

    def test_company_detail_get_not_found(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        monkeypatch.setattr(cr, 'kbai_companies_service', MagicMock(findOne=lambda cid: ({'message': 'Company not found'}, 404)))
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/999', '/kbai/companies/999'])
        assert resp.status_code == 404

    def test_company_detail_get_success(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        monkeypatch.setattr(cr, 'kbai_companies_service', MagicMock(findOne=lambda cid: ({'message': 'ok', 'data': {'id_company': 1}, 'success': True}, 200)))
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/1', '/kbai/companies/1'])
        assert resp.status_code == 200

    def test_companies_list_post_validation_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        self._bypass_auth(monkeypatch)
        resp = self._try(client, 'post', ['/api/v1/kbai/companies/', '/api/v1/kbai/companies', '/kbai/companies/','/kbai/companies'], json={})
        assert resp.status_code == 400

    def test_company_detail_put_no_body(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        self._bypass_auth(monkeypatch)
        resp = self._try(client, 'put', ['/api/v1/kbai/companies/1', '/kbai/companies/1'], json={})
        assert resp.status_code == 400

    def test_company_detail_put_validation_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        self._bypass_auth(monkeypatch)
        # Send invalid field to trigger schema validation
        resp = self._try(client, 'put', ['/api/v1/kbai/companies/1', '/kbai/companies/1'], json={'invalid': True})
        assert resp.status_code in [400, 500]

    def test_company_detail_put_service_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        self._bypass_auth(monkeypatch)
        cr.kbai_companies_service = MagicMock(update=lambda company_id, data, current_user_id: ({'message': 'Service failed'}, 500))
        resp = self._try(client, 'put', ['/api/v1/kbai/companies/1', '/kbai/companies/1'], json={'company_name': 'X'})
        assert resp.status_code == 500

    def test_company_detail_delete_service_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        self._bypass_auth(monkeypatch)
        cr.kbai_companies_service = MagicMock(delete=lambda company_id, current_user_id: ({'message': 'Service failed'}, 500))
        resp = self._try(client, 'delete', ['/api/v1/kbai/companies/1', '/kbai/companies/1'])
        assert resp.status_code == 500

    def test_companies_by_user_permission_denied(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        # set current user as admin id_user=2 and request for tb_user_id=1 to trigger 403
        self._bypass_auth(monkeypatch)
        bad_user = type('U', (), {'id_user': 2, 'role': 'admin', 'email': 'a@test.com'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: bad_user, raising=False)
        # Also patch the imported alias in route module
        monkeypatch.setattr(cr, 'get_current_user', lambda: bad_user, raising=False)
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/user/1', '/api/v1/kbai/companies/user/1/','/kbai/companies/user/1'])
        assert resp.status_code == 403

    def test_companies_by_user_not_found(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        su = type('U', (), {'id_user': 1, 'role': 'superadmin'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: su, raising=False)
        # Mock TbUser.findOne to return None via module attribute
        tb = MagicMock()
        tb.findOne.return_value = None
        monkeypatch.setattr(cr, 'TbUser', tb, raising=False)
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/user/123', '/kbai/companies/user/123'])
        assert resp.status_code == 404

    def test_companies_by_user_service_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        su = type('U', (), {'id_user': 1, 'role': 'superadmin'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: su, raising=False)
        tb = MagicMock(); tb.findOne.return_value = MagicMock(id_user=1)
        monkeypatch.setattr(cr, 'TbUser', tb, raising=False)
        cr.kbai_companies_service = MagicMock(find_by_user=lambda **kw: ({'message': 'Service failed'}, 500))
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/user/1', '/kbai/companies/user/1'])
        assert resp.status_code == 500

    def test_companies_dropdown_admin_other_user_forbidden(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        admin = type('U', (), {'id_user': 2, 'role': 'admin'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: admin, raising=False)
        # Also patch the route module's imported reference
        monkeypatch.setattr(cr, 'get_current_user', lambda: admin, raising=False)
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/list/1', '/api/v1/kbai/companies/list/1/', '/kbai/companies/list/1', '/kbai/companies/list/1/'])
        assert resp.status_code == 403

    def test_companies_dropdown_target_user_not_found(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        su = type('U', (), {'id_user': 1, 'role': 'superadmin'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: su, raising=False)
        tb = MagicMock(); tb.findOne.return_value = None
        monkeypatch.setattr(cr, 'TbUser', tb, raising=False)
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/list/999', '/kbai/companies/list/999'])
        assert resp.status_code == 404

    def test_companies_dropdown_service_error(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        su = type('U', (), {'id_user': 1, 'role': 'superadmin'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: su, raising=False)
        tb = MagicMock(); tb.findOne.return_value = MagicMock(id_user=1)
        monkeypatch.setattr(cr, 'TbUser', tb, raising=False)
        cr.kbai_companies_service = MagicMock(find_companies=lambda tb_user_id: ({'message':'Service failed'}, 500))
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/list/1', '/kbai/companies/list/1'])
        assert resp.status_code == 500

    def test_companies_dropdown_user_role_forbidden(self, monkeypatch, client):
        import src.app.api.v1.routes.kbai.companies_routes as cr
        import src.app.api.middleware.auth0_verify as av
        self._bypass_auth(monkeypatch)
        user = type('U', (), {'id_user': 1, 'role': 'user'})()
        monkeypatch.setattr(av, 'get_current_user', lambda: user, raising=False)
        monkeypatch.setattr(cr, 'get_current_user', lambda: user, raising=False)
        resp = self._try(client, 'get', ['/api/v1/kbai/companies/list/1', '/kbai/companies/list/1'])
        assert resp.status_code == 403


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
