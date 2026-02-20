"""
Class-based tests for UserService covering common error branches and permissions.
All DB/model calls are mocked.
"""

from unittest.mock import patch, MagicMock
from src.app.api.v1.services.public.auth_user_service import UserService


class TestUserService:
    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_find_denied_for_basic_user(self, mock_tbuser, app):
        service = UserService()
        # current user has role 'user' => 403
        current = MagicMock()
        current.role = 'user'
        mock_tbuser.findOne.return_value = current

        with app.app_context():
            resp, status = service.find(current_user_id=1)
            assert status == 403
            assert resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_find_user_not_found(self, mock_tbuser, app):
        service = UserService()
        mock_tbuser.findOne.return_value = None

        with app.app_context():
            resp, status = service.find(current_user_id=99)
            assert status == 404
            assert resp['error'] == 'User not found'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_findOne_target_missing(self, mock_tbuser, app):
        service = UserService()
        mock_tbuser.findOne.return_value = None

        with app.app_context():
            resp, status = service.findOne(user_id=10, current_user_id=1)
            assert status == 404
            assert resp['error'] == 'User not found'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_update_validation_error(self, mock_tbuser, app):
        service = UserService()
        # current and target exist
        current = MagicMock()
        current.role = 'superadmin'
        target = MagicMock()
        mock_tbuser.findOne.side_effect = [current, target]

        # invalid update (schema raises)
        with app.app_context():
            resp, status = service.update(user_id=2, update_data={'invalid': True}, current_user_id=1)
            assert status == 400
            assert resp['error'] == 'Validation failed'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_delete_self_forbidden(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock()
        current.role = 'superadmin'
        target = MagicMock()
        mock_tbuser.findOne.side_effect = [current, target]

        with app.app_context():
            resp, status = service.delete(user_id=1, current_user_id=1)
            assert status == 403
            assert resp['error'] == 'Self-deletion not allowed'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_hard_delete_staff_cannot_delete_superadmin(self, mock_tbuser, app):
        service = UserService()
        staff = MagicMock()
        staff.role = 'staff'
        superadmin = MagicMock()
        superadmin.role = 'superadmin'
        superadmin.email = 'sa@test.com'
        mock_tbuser.findOne.side_effect = [staff, superadmin]

        with app.app_context():
            resp, status = service.hard_delete(user_id=2, current_user_id=1)
            assert status == 403
            assert resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_change_user_password_validation_error(self, mock_tbuser, app):
        service = UserService()
        target = MagicMock()
        mock_tbuser.findOne.return_value = target

        with app.app_context():
            resp, status = service.change_user_password(user_id=5, password_data={'bad': True}, current_user_id=1)
            assert status == 400
            assert resp['error'] == 'Validation failed'


    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_find_superadmin_success(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); current.id_user = 1; current.role = 'superadmin'
        mock_tbuser.findOne.return_value = current

        other = MagicMock()
        other.id_user = 2
        other.role = 'admin'
        other.to_dict.return_value = {'id_user': 2, 'role': 'admin'}
        mock_tbuser.find.return_value = ([other, current], 2, None)

        with patch('src.app.api.v1.services.public.auth_user_service.db') as mock_db, app.app_context():
            mock_db.session.query.return_value.filter.return_value.count.return_value = 3
            resp, status = service.find(current_user_id=1)
            assert status == 200
            users = resp['data']['users']
            assert len(users) == 1 and users[0]['id_user'] == 2
            assert users[0]['number_licences'] == 3

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_find_model_error(self, mock_tbuser, app):
        service = UserService()
        sa = MagicMock(); sa.id_user = 1; sa.role = 'superadmin'
        mock_tbuser.findOne.return_value = sa
        mock_tbuser.find.return_value = ([], 0, 'db error')
        with app.app_context():
            resp, status = service.find(current_user_id=1)
            assert status == 500
            assert resp['error']

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_find_admin_scope(self, mock_tbuser, app):
        service = UserService()
        admin = MagicMock(); admin.id_user = 9; admin.role = 'admin'
        mock_tbuser.findOne.return_value = admin
        u = MagicMock(); u.id_user = 20; u.role = 'user'; u.to_dict.return_value = {'id_user':20,'role':'user'}
        mock_tbuser.find.return_value = ([u], 1, None)
        with app.app_context():
            resp, status = service.find(current_user_id=9)
            assert status == 200
            assert resp['data']['users'][0]['number_licences'] == 0

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_findOne_admin_includes_license_count(self, mock_tbuser, app):
        service = UserService()
        target = MagicMock(); target.id_user = 2; target.role = 'admin'
        target.to_dict.return_value = {'id_user':2,'role':'admin','email':'a@test.com'}
        mock_tbuser.findOne.return_value = target
        with patch('src.app.api.v1.services.public.auth_user_service.db') as mock_db, app.app_context():
            mock_db.session.query.return_value.filter.return_value.count.return_value = 2
            resp, status = service.findOne(user_id=2, current_user_id=1)
            assert status == 200
            assert resp['data']['user']['number_licences'] == 2

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_findOne_user_companies_empty(self, mock_tbuser, app):
        service = UserService()
        target = MagicMock(); target.id_user = 7; target.role = 'user'
        target.to_dict.return_value = {'id_user':7,'role':'user','email':'u@test.com'}
        mock_tbuser.findOne.return_value = target
        with patch('src.app.api.v1.services.public.auth_user_service.TbUserCompany') as mock_map, app.app_context():
            mock_map.query.filter_by.return_value.all.return_value = []
            resp, status = service.findOne(user_id=7, current_user_id=1)
            assert status == 200
            assert resp['data']['user']['companies'] == []

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_update_permission_denied_simple(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); target = MagicMock()
        mock_tbuser.findOne.side_effect = [current, target]
        with patch.object(UserService, 'check_hierarchy_permission', return_value=(False, 'no')), app.app_context():
            resp, status = service.update(2, {'name':'X'}, 1)
            assert status == 403 and resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_update_success_simple(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); target = MagicMock(); target.role = 'user'
        target.to_dict.return_value = {'id_user':2}
        target.update.return_value = (True, None)
        mock_tbuser.findOne.side_effect = [current, target]
        # Patch the instance schema to return validated dict
        service.update_schema = MagicMock()
        service.update_schema.load.return_value = {'name': 'New Name'}
        with patch.object(UserService, 'check_hierarchy_permission', return_value=(True, '')), app.app_context():
            resp, status = service.update(2, {'name':'New Name'}, 1)
            assert status == 200 and resp['success']

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_delete_permission_denied(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); target = MagicMock()
        mock_tbuser.findOne.side_effect = [current, target]
        with patch.object(UserService, 'check_hierarchy_permission', return_value=(False, 'no')), app.app_context():
            resp, status = service.delete(user_id=2, current_user_id=1)
            assert status == 403 and resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_delete_success(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); target = MagicMock(); target.delete.return_value = (True, None)
        mock_tbuser.findOne.side_effect = [current, target]
        with patch.object(UserService, 'check_hierarchy_permission', return_value=(True, '')), app.app_context():
            resp, status = service.delete(user_id=2, current_user_id=1)
            assert status == 200 and resp['success']

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_hard_delete_user_role_forbidden(self, mock_tbuser, app):
        service = UserService()
        current = MagicMock(); current.role = 'user'
        target = MagicMock(); target.role = 'user'
        mock_tbuser.findOne.side_effect = [current, target]
        with app.app_context():
            resp, status = service.hard_delete(user_id=2, current_user_id=1)
            assert status == 403 and resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_change_user_password_user_not_found(self, mock_tbuser, app):
        service = UserService()
        mock_tbuser.findOne.return_value = None
        with app.app_context():
            resp, status = service.change_user_password(user_id=5, password_data={'new_password': 'x'}, current_user_id=1)
            assert status == 404 and resp['error'] == 'User not found'

    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_change_user_password_success(self, mock_tbuser, app):
        service = UserService()
        target = MagicMock(); target.update.return_value = (True, None)
        mock_tbuser.findOne.return_value = target
        service.password_schema = MagicMock()
        service.password_schema.load.return_value = {'new_password': 'P@ss'}
        with app.app_context():
            resp, status = service.change_user_password(user_id=5, password_data={'new_password': 'P@ss'}, current_user_id=1)
            assert status == 200 and resp['success']

    # create() simple branches
    @patch('src.app.api.v1.services.public.auth_user_service.UserTempData')
    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_create_email_conflict_in_tb_user(self, mock_tbuser, mock_temp, app):
        service = UserService()
        creator = MagicMock(); creator.role = 'superadmin'
        # First call: current user, Second: email exists
        mock_tbuser.findOne.side_effect = [creator, MagicMock()]
        mock_temp.findOne.return_value = None
        with app.app_context():
            resp, status = service.create({'email':'a@test.com','password':'p','role':'user','first_name':'A','last_name':'B'}, 1)
            assert status == 409 and resp['error'] == 'Email already exists'

    @patch('src.app.api.v1.services.public.auth_user_service.UserTempData')
    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_create_email_conflict_in_temp(self, mock_tbuser, mock_temp, app):
        service = UserService()
        creator = MagicMock(); creator.role = 'superadmin'
        # Current user ok, TbUser.findOne(email) returns None
        mock_tbuser.findOne.side_effect = [creator, None]
        mock_temp.findOne.return_value = MagicMock()
        with app.app_context():
            resp, status = service.create({'email':'b@test.com','password':'p','role':'user','first_name':'A','last_name':'B'}, 1)
            assert status == 409

    @patch('src.app.api.v1.services.public.auth_user_service.UserTempData')
    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_create_permission_denied_admin_by_user(self, mock_tbuser, mock_temp, app):
        service = UserService()
        creator = MagicMock(); creator.role = 'user'
        mock_tbuser.findOne.side_effect = [creator, None]
        mock_temp.findOne.return_value = None
        with app.app_context():
            resp, status = service.create({'email':'c@test.com','password':'p','role':'admin','first_name':'A','last_name':'B','number_licences':1}, 1)
            assert status == 403 and resp['error'] == 'Permission denied'

    @patch('src.app.api.v1.services.public.auth_user_service.UserTempData')
    @patch('src.app.api.v1.services.public.auth_user_service.TbUser')
    def test_create_auth0_value_error_conflict(self, mock_tbuser, mock_temp, app):
        service = UserService()
        creator = MagicMock(); creator.role = 'superadmin'
        mock_tbuser.findOne.side_effect = [creator, None]
        mock_temp.findOne.return_value = None
        with patch('src.app.api.v1.services.auth0_service') as a0, app.app_context():
            a0.create_auth0_user.side_effect = ValueError('User already exists')
            resp, status = service.create({'email':'d@test.com','password':'p','role':'user','first_name':'A','last_name':'B'}, 1)
            assert status == 409


    # ------------------------------------------------------------------
    # check_hierarchy_permission branches (without MagicMock)
    # ------------------------------------------------------------------
    class _StubUser:
        def __init__(self, id_user: int, role: str, id_admin: int | None = None, email: str | None = None):
            self.id_user = id_user
            self.role = role
            self.id_admin = id_admin
            self.email = email or f'user{ id_user }@test.com'

    def test_check_perm_staff_cannot_manage_superadmin(self):
        service = UserService()
        staff = self._StubUser(1, 'staff')
        superadmin = self._StubUser(2, 'superadmin')
        ok, msg = service.check_hierarchy_permission(staff, superadmin, 'update')
        assert ok is False and 'cannot manage superadmin' in msg.lower()

    def test_check_perm_staff_can_manage_others(self):
        service = UserService()
        staff = self._StubUser(1, 'staff')
        admin = self._StubUser(3, 'admin')
        ok, msg = service.check_hierarchy_permission(staff, admin, 'delete')
        assert ok is True and msg == ''

    def test_check_perm_user_role_rules(self):
        service = UserService()
        usr = self._StubUser(5, 'user')
        other = self._StubUser(6, 'user')
        # list forbidden
        ok, msg = service.check_hierarchy_permission(usr, other, 'list')
        assert ok is False and "cannot list" in msg
        # update only self
        ok, msg = service.check_hierarchy_permission(usr, other, 'update')
        assert ok is False and 'only update themselves' in msg
        ok, msg = service.check_hierarchy_permission(usr, usr, 'update')
        assert ok is True and msg == ''
        # unknown action -> forbidden
        ok, msg = service.check_hierarchy_permission(usr, other, 'manage')
        assert ok is False and 'cannot manage' in msg.lower()

    def test_check_perm_admin_self_created_or_forbidden(self):
        service = UserService()
        admin = self._StubUser(9, 'admin')
        self_admin = self._StubUser(9, 'admin')
        created = self._StubUser(10, 'user', id_admin=9)
        stranger = self._StubUser(11, 'user', id_admin=99)
        # self
        ok, msg = service.check_hierarchy_permission(admin, self_admin, 'update')
        assert ok is True and msg == ''
        # created by admin
        ok, msg = service.check_hierarchy_permission(admin, created, 'delete')
        assert ok is True and msg == ''
        # not created by admin
        ok, msg = service.check_hierarchy_permission(admin, stranger, 'delete')
        assert ok is False and 'directly created or yourself' in msg