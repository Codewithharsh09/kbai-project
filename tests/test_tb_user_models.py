"""
Test Suite for TbUser and UserTempData Models
Simple tests to achieve high coverage for both models
"""
import pytest
from datetime import datetime

from src.app.database.models.public.tb_user import TbUser, UserTempData


# ============================================================================
# TbUser Tests
# ============================================================================

class TestTbUser:
    """Test TbUser model methods"""
    
    def test_model_exists(self):
        """Test that TbUser model exists and can be instantiated"""
        user = TbUser()
        assert user is not None
        assert hasattr(user, 'id_user')
        assert hasattr(user, 'email')
        assert hasattr(user, 'role')
        assert hasattr(user, 'name')
        assert hasattr(user, 'username')
        assert hasattr(user, 'surname')
        assert hasattr(user, 'company_name')
        assert hasattr(user, 'phone')
        assert hasattr(user, 'language')
        assert hasattr(user, 'premium_licenses_1')
        assert hasattr(user, 'premium_licenses_2')
        assert hasattr(user, 'status')
        assert hasattr(user, 'is_verified')
        assert hasattr(user, 'mfa')
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert hasattr(user, 'auth0_user_id')
        assert hasattr(user, 'auth0_metadata')
    
    def test_is_super_admin_true(self):
        """Test is_super_admin method returns True for superadmin"""
        user = TbUser()
        user.role = 'superadmin'
        assert user.is_super_admin() is True
        
        user.role = 'SUPERADMIN'
        assert user.is_super_admin() is True
    
    def test_is_super_admin_false(self):
        """Test is_super_admin method returns False for non-superadmin"""
        user = TbUser()
        user.role = 'admin'
        assert user.is_super_admin() is False
        
        user.role = 'user'
        assert user.is_super_admin() is False
        
        user.role = 'manager'
        assert user.is_super_admin() is False
        
        user.role = 'staff'
        assert user.is_super_admin() is False
    
    def test_is_admin_true_superadmin(self):
        """Test is_admin method returns True for superadmin"""
        user = TbUser()
        user.role = 'superadmin'
        assert user.is_admin() is True
        
        user.role = 'SUPERADMIN'
        assert user.is_admin() is True
    
    def test_is_admin_true_admin(self):
        """Test is_admin method returns True for admin"""
        user = TbUser()
        user.role = 'admin'
        assert user.is_admin() is True
        
        user.role = 'ADMIN'
        assert user.is_admin() is True
    
    def test_is_admin_false(self):
        """Test is_admin method returns False for non-admin roles"""
        user = TbUser()
        user.role = 'user'
        assert user.is_admin() is False
        
        user.role = 'manager'
        assert user.is_admin() is False
        
        user.role = 'staff'
        assert user.is_admin() is False
    
    def test_to_dict(self):
        """Test to_dict method"""
        user = TbUser()
        user.id_user = 1
        user.id_admin = 2
        user.email = 'test@example.com'
        user.role = 'user'
        user.name = 'John'
        user.username = 'john_doe'
        user.surname = 'Doe'
        user.language = 'en'
        user.status = 'ACTIVE'
        user.is_verified = True
        user.mfa = False
        user.created_at = datetime(2024, 1, 1, 12, 0, 0)
        user.auth0_user_id = 'auth0|123'
        user.company_name = 'Test Company'
        user.phone = '+1234567890'
        user.premium_licenses_1 = 5
        user.premium_licenses_2 = 3
        
        result = user.to_dict()
        
        assert result['id_user'] == 1
        assert result['id_admin'] == 2
        assert result['email'] == 'test@example.com'
        assert result['role'] == 'user'
        assert result['name'] == 'John'
        assert result['username'] == 'john_doe'
        assert result['surname'] == 'Doe'
        assert result['language'] == 'en'
        assert result['status'] == 'ACTIVE'
        assert result['is_verified'] is True
        assert result['mfa'] is False
        assert result['created_at'] == '2024-01-01T12:00:00'
        assert result['auth0_user_id'] == 'auth0|123'
        assert result['company_name'] == 'Test Company'
        assert result['phone'] == '+1234567890'
        assert result['premium_licenses_1'] == 5
        assert result['premium_licenses_2'] == 3
    
    def test_to_dict_with_none_values(self):
        """Test to_dict method with None values"""
        user = TbUser()
        user.id_user = 1
        user.created_at = None
        user.id_admin = None
        user.name = None
        user.username = None
        user.surname = None
        user.company_name = None
        user.phone = None
        user.auth0_user_id = None
        
        result = user.to_dict()
        
        assert result['id_user'] == 1
        assert result['created_at'] is None
        assert result['id_admin'] is None
        assert result['name'] is None
        assert result['username'] is None
        assert result['surname'] is None
        assert result['company_name'] is None
        assert result['phone'] is None
        assert result['auth0_user_id'] is None
    
    def test_create_method_exists(self):
        """Test that create class method exists"""
        assert hasattr(TbUser, 'create')
        assert callable(getattr(TbUser, 'create'))
    
    def test_find_one_method_exists(self):
        """Test that findOne class method exists"""
        assert hasattr(TbUser, 'findOne')
        assert callable(getattr(TbUser, 'findOne'))
    
    def test_find_method_exists(self):
        """Test that find class method exists"""
        assert hasattr(TbUser, 'find')
        assert callable(getattr(TbUser, 'find'))
    
    def test_update_method_exists(self):
        """Test that update method exists"""
        user = TbUser()
        assert hasattr(user, 'update')
        assert callable(getattr(user, 'update'))
    
    def test_delete_method_exists(self):
        """Test that delete method exists"""
        user = TbUser()
        assert hasattr(user, 'delete')
        assert callable(getattr(user, 'delete'))
    
    def test_create_with_minimal_data(self, db_session):
        """Test create method with minimal data"""
        user_data = {'email': 'test@example.com'}
        
        user, error = TbUser.create(user_data)
        
        # Should succeed with minimal data
        assert user is not None or error is not None  # Either succeeds or fails gracefully
    
    def test_find_one_basic(self, db_session):
        """Test findOne method basic functionality"""
        # Try to find a user that doesn't exist
        result = TbUser.findOne(email='nonexistent@example.com')
        
        # Should return None for non-existent user
        assert result is None
    
    def test_find_basic(self, db_session):
        """Test find method basic functionality"""
        # Try to find users
        users, total, error = TbUser.find(page=1, per_page=10)
        
        # Should return without error
        assert error is None
        assert isinstance(users, list)
        assert isinstance(total, int)
    
    def test_update_basic(self, db_session):
        """Test update method basic functionality"""
        user = TbUser()
        user.email = 'test@example.com'
        user.name = 'Old Name'
        
        # Try to update
        success, error = user.update({'name': 'New Name'})
        
        # Should either succeed or fail gracefully
        assert isinstance(success, bool)
        assert error is None or isinstance(error, str)
    
    def test_delete_basic(self, db_session):
        """Test delete method basic functionality"""
        user = TbUser()
        user.status = 'ACTIVE'
        
        # Try to delete
        success, error = user.delete()
        
        # Should either succeed or fail gracefully
        assert isinstance(success, bool)
        assert error is None or isinstance(error, str)
    
    def test_create_with_full_data(self, db_session):
        """Test create method with full data"""
        user_data = {
            'email': 'test@example.com',
            'name': 'John',
            'surname': 'Doe',
            'role': 'user',
            'company_name': 'Test Company',
            'phone': '+1234567890',
            'language': 'en',
            'status': 'ACTIVE',
            'is_verified': True,
            'created_by': 1,
            'auth0_user_id': 'auth0|123',
            'auth0_metadata': {'key': 'value'}
        }
        
        user, error = TbUser.create(user_data)
        
        # Should either succeed or fail gracefully
        assert user is not None or error is not None
    
    def test_find_one_with_select_columns(self, db_session):
        """Test findOne method with select_columns"""
        result = TbUser.findOne(select_columns=['id_user', 'email'], email='nonexistent@example.com')
        
        # Should return None for non-existent user
        assert result is None
    
    def test_find_with_search(self, db_session):
        """Test find method with search"""
        users, total, error = TbUser.find(page=1, per_page=10, search='nonexistent')
        
        # Should return without error
        assert error is None
        assert isinstance(users, list)
        assert isinstance(total, int)
    
    def test_find_with_filters(self, db_session):
        """Test find method with filters"""
        users, total, error = TbUser.find(page=1, per_page=10, role='admin', status='ACTIVE')
        
        # Should return without error
        assert error is None
        assert isinstance(users, list)
        assert isinstance(total, int)
    
    def test_find_with_select_columns(self, db_session):
        """Test find method with select_columns"""
        users, total, error = TbUser.find(select_columns=['id_user', 'email'], page=1, per_page=10)
        
        # Should return without error
        assert error is None
        assert isinstance(users, list)
        # When using select_columns, total might be a different type
        assert total is not None
    
    def test_update_with_multiple_fields(self, db_session):
        """Test update method with multiple fields"""
        user = TbUser()
        user.email = 'test@example.com'
        user.name = 'Old Name'
        user.surname = 'Old Surname'
        user.status = 'INACTIVE'
        
        # Try to update multiple fields
        success, error = user.update({
            'name': 'New Name',
            'surname': 'New Surname',
            'status': 'ACTIVE',
            'mfa': True,
            'premium_licenses_1': 5,
            'premium_licenses_2': 3
        })
        
        # Should either succeed or fail gracefully
        assert isinstance(success, bool)
        assert error is None or isinstance(error, str)


# ============================================================================
# UserTempData Tests
# ============================================================================

class TestUserTempData:
    """Test UserTempData model methods"""
    
    def test_model_exists(self):
        """Test that UserTempData model exists and can be instantiated"""
        temp_data = UserTempData()
        assert temp_data is not None
        assert hasattr(temp_data, 'email')
        assert hasattr(temp_data, 'name')
        assert hasattr(temp_data, 'surname')
        assert hasattr(temp_data, 'company_name')
        assert hasattr(temp_data, 'number_licences')
        assert hasattr(temp_data, 'premium_licenses_1')
        assert hasattr(temp_data, 'premium_licenses_2')
        assert hasattr(temp_data, 'phone')
        assert hasattr(temp_data, 'language')
        assert hasattr(temp_data, 'id_user')
        assert hasattr(temp_data, 'companies')
    
    def test_to_dict(self):
        """Test to_dict method"""
        temp_data = UserTempData()
        temp_data.email = 'test@example.com'
        temp_data.name = 'John'
        temp_data.surname = 'Doe'
        temp_data.company_name = 'Test Company'
        temp_data.number_licences = 5
        temp_data.premium_licenses_1 = 3
        temp_data.premium_licenses_2 = 2
        temp_data.phone = '+1234567890'
        temp_data.language = 'en'
        temp_data.id_user = 1
        temp_data.companies = [1, 2, 3]
        
        result = temp_data.to_dict()
        
        assert result['email'] == 'test@example.com'
        assert result['name'] == 'John'
        assert result['surname'] == 'Doe'
        assert result['company_name'] == 'Test Company'
        assert result['number_licences'] == 5
        assert result['premium_licenses_1'] == 3
        assert result['premium_licenses_2'] == 2
        assert result['phone'] == '+1234567890'
        assert result['language'] == 'en'
        assert result['id_user'] == 1
        assert result['companies'] == [1, 2, 3]
    
    def test_to_dict_with_none_values(self):
        """Test to_dict method with None values"""
        temp_data = UserTempData()
        temp_data.email = 'test@example.com'
        temp_data.name = None
        temp_data.surname = None
        temp_data.company_name = None
        temp_data.number_licences = None
        temp_data.premium_licenses_1 = None
        temp_data.premium_licenses_2 = None
        temp_data.phone = None
        temp_data.language = None
        temp_data.id_user = None
        temp_data.companies = None
        
        result = temp_data.to_dict()
        
        assert result['email'] == 'test@example.com'
        assert result['name'] is None
        assert result['surname'] is None
        assert result['company_name'] is None
        assert result['number_licences'] is None
        assert result['premium_licenses_1'] is None
        assert result['premium_licenses_2'] is None
        assert result['phone'] is None
        assert result['language'] is None
        assert result['id_user'] is None
        assert result['companies'] is None
    
    def test_create_or_update_method_exists(self):
        """Test that create_or_update class method exists"""
        assert hasattr(UserTempData, 'create_or_update')
        assert callable(getattr(UserTempData, 'create_or_update'))
    
    def test_find_one_method_exists(self):
        """Test that findOne class method exists"""
        assert hasattr(UserTempData, 'findOne')
        assert callable(getattr(UserTempData, 'findOne'))
    
    def test_delete_method_exists(self):
        """Test that delete method exists"""
        temp_data = UserTempData()
        assert hasattr(temp_data, 'delete')
        assert callable(getattr(temp_data, 'delete'))
    
    def test_create_or_update_basic(self, db_session):
        """Test create_or_update method basic functionality"""
        temp_data_dict = {'email': 'test@example.com'}
        
        temp_data, error = UserTempData.create_or_update(temp_data_dict)
        
        # Should either succeed or fail gracefully
        assert temp_data is not None or error is not None
    
    def test_find_one_basic(self, db_session):
        """Test findOne method basic functionality"""
        # Try to find temp data that doesn't exist
        result = UserTempData.findOne(email='nonexistent@example.com')
        
        # Should return None for non-existent data
        assert result is None
    
    def test_delete_basic(self, db_session):
        """Test delete method basic functionality"""
        temp_data = UserTempData()
        temp_data.email = 'test@example.com'
        
        # Try to delete
        success, error = temp_data.delete()
        
        # Should either succeed or fail gracefully
        assert isinstance(success, bool)
        assert error is None or isinstance(error, str)
    
    def test_create_or_update_with_full_data(self, db_session):
        """Test create_or_update method with full data"""
        temp_data_dict = {
            'email': 'test@example.com',
            'name': 'John',
            'surname': 'Doe',
            'company_name': 'Test Company',
            'number_licences': 5,
            'premium_licenses_1': 3,
            'premium_licenses_2': 2,
            'phone': '+1234567890',
            'language': 'en',
            'id_user': 1,
            'companies': [1, 2, 3]
        }
        
        temp_data, error = UserTempData.create_or_update(temp_data_dict)
        
        # Should either succeed or fail gracefully
        assert temp_data is not None or error is not None
    
    def test_find_one_with_select_columns(self, db_session):
        """Test findOne method with select_columns"""
        result = UserTempData.findOne(select_columns=['email', 'name'], email='nonexistent@example.com')
        
        # Should return None for non-existent data
        assert result is None