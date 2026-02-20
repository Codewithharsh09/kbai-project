
# Swagger Configuration
SWAGGER = {
    'title': 'KBAI Backend API',
    'version': '1.0',
    'description': 'Complete authentication system with super admin, admin, and Auth0 integration',
    'doc_dir': './docs/api/',
    'specs_route': '/api/docs/',
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs': [
        {
            'endpoint': 'apispec',
            'route': '/apispec.json',
            'rule_filter': lambda rule: True,
            'model_filter': lambda tag: True,
        }
    ],
    'securityDefinitions': {
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT token'
        }
    }
}
