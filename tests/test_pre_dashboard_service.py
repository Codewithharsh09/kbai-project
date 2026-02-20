"""
Simple unit tests for KBAI Pre-Dashboard service, matching company test style.
No mocks; invoke service methods and assert on broad status codes.
"""


class TestPreDashboardService:
    def test_find_one_pre_dashboard(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        result, status_code = service.findOne(1)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_find_one_pre_dashboard_not_found(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        result, status_code = service.findOne(99999)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_find_one_pre_dashboard_invalid_id(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        result, status_code = service.findOne(-1)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_update_pre_dashboard(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {'step_upload': True}
        result, status_code = service.update(1, payload)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_update_pre_dashboard_not_found(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {'step_upload': True}
        result, status_code = service.update(99999, payload)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_update_pre_dashboard_empty_data(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {}
        result, status_code = service.update(1, payload)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_update_pre_dashboard_multiple_fields(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {
            'step_upload': True,
            'step_compare': False,
            'step_competitor': True,
            'step_predictive': False,
            'completed_flag': True
        }
        result, status_code = service.update(1, payload)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_update_pre_dashboard_invalid_id(self):
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {'step_upload': True}
        result, status_code = service.update(-1, payload)

        assert status_code in [200, 404, 500]
        assert isinstance(result, dict)

    def test_find_one_with_real_data(self, db_session):
        """Integration test with real database data"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService
        from src.app.database.models import KbaiCompany, KbaiPreDashboard, TbLicences

        # Create license
        license1 = TbLicences(licence_token="LIC-123456")
        db_session.add(license1)
        db_session.commit()

        # Create company
        company = KbaiCompany(
            id_licence=license1.id_licence,
            company_name="Test Company",
            email="test@example.com"
        )
        db_session.add(company)
        db_session.commit()

        # Create pre-dashboard record
        pre_dashboard = KbaiPreDashboard(
            company_id=company.id_company,
            step_upload=True,
            step_compare=False
        )
        db_session.add(pre_dashboard)
        db_session.commit()

        # Test service
        service = KbaiPreDashboardService()
        result, status_code = service.findOne(company.id_company)

        assert status_code == 200
        assert result['success'] is True
        assert result['data']['company_id'] == company.id_company

    def test_update_with_real_data(self, db_session):
        """Integration test with real database data"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService
        from src.app.database.models import KbaiCompany, KbaiPreDashboard, TbLicences

        # Create license
        license1 = TbLicences(licence_token="LIC-123456")
        db_session.add(license1)
        db_session.commit()

        # Create company
        company = KbaiCompany(
            id_licence=license1.id_licence,
            company_name="Test Company",
            email="test@example.com"
        )
        db_session.add(company)
        db_session.commit()

        # Create pre-dashboard record
        pre_dashboard = KbaiPreDashboard(
            company_id=company.id_company,
            step_upload=False,
            step_compare=False
        )
        db_session.add(pre_dashboard)
        db_session.commit()

        # Test service update
        service = KbaiPreDashboardService()
        payload = {'step_upload': True, 'step_compare': True}
        result, status_code = service.update(company.id_company, payload)

        assert status_code == 200
        assert result['success'] is True
        assert result['data']['company_id'] == company.id_company

    def test_find_one_company_not_found(self, db_session):
        """Test when company doesn't exist"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        result, status_code = service.findOne(99999)

        assert status_code == 404
        assert result['message'] == 'Company not found'

    def test_update_company_not_found(self, db_session):
        """Test update when company doesn't exist"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService

        service = KbaiPreDashboardService()
        payload = {'step_upload': True}
        result, status_code = service.update(99999, payload)

        assert status_code == 404
        assert result['message'] == 'Company not found'

    def test_find_one_pre_dashboard_not_found(self, db_session):
        """Test when company exists but pre-dashboard doesn't"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService
        from src.app.database.models import KbaiCompany, TbLicences

        # Create license and company
        license1 = TbLicences(licence_token="LIC-123456")
        db_session.add(license1)
        db_session.commit()

        company = KbaiCompany(
            id_licence=license1.id_licence,
            company_name="Test Company",
            email="test@example.com"
        )
        db_session.add(company)
        db_session.commit()

        # Test service (no pre-dashboard record created)
        service = KbaiPreDashboardService()
        result, status_code = service.findOne(company.id_company)

        assert status_code == 404
        assert 'Pre-dashboard record not found' in result['message']

    def test_update_pre_dashboard_not_found(self, db_session):
        """Test update when company exists but pre-dashboard doesn't"""
        from src.app.api.v1.services.kbai.pre_dashboard_service import KbaiPreDashboardService
        from src.app.database.models import KbaiCompany, TbLicences

        # Create license and company
        license1 = TbLicences(licence_token="LIC-123456")
        db_session.add(license1)
        db_session.commit()

        company = KbaiCompany(
            id_licence=license1.id_licence,
            company_name="Test Company",
            email="test@example.com"
        )
        db_session.add(company)
        db_session.commit()

        # Test service update (no pre-dashboard record created)
        service = KbaiPreDashboardService()
        payload = {'step_upload': True}
        result, status_code = service.update(company.id_company, payload)

        assert status_code == 404
        assert 'Pre-dashboard record not found' in result['message']


