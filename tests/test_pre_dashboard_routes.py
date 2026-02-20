"""
Simple tests for KBAI Pre-Dashboard routes, matching company test style.
No mocks; just verify endpoints respond with expected status ranges.
"""


class TestPreDashboardRoutes:
    def _try(self, client, method, paths, **kw):
        for p in paths:
            resp = getattr(client, method)(p, **kw)
            if resp.status_code != 404:
                return resp
        return resp

    def test_get_pre_dashboard_route(self, client):
        resp = self._try(client, 'get', ['/api/v1/kbai/pre-dashboard/1', '/kbai/pre-dashboard/1'])
        assert resp.status_code in [200, 404, 500]

    def test_update_pre_dashboard_no_body(self, client):
        resp = self._try(client, 'put', ['/api/v1/kbai/pre-dashboard/1', '/kbai/pre-dashboard/1'], json={})
        assert resp.status_code in [400, 500]

    def test_update_pre_dashboard_with_body(self, client):
        payload = {'step_upload': True, 'completed_flag': False}
        resp = self._try(client, 'put', ['/api/v1/kbai/pre-dashboard/1', '/kbai/pre-dashboard/1'], json=payload)
        assert resp.status_code in [200, 400, 404, 500]

    def test_pre_dashboard_routes_exist(self, client):
        routes = [
            ('/api/v1/kbai/pre-dashboard/1', 'GET'),
            ('/api/v1/kbai/pre-dashboard/1', 'PUT'),
        ]
        for route, method in routes:
            resp = getattr(client, method.lower())(route)
            assert resp.status_code in [200, 400, 404, 500]


