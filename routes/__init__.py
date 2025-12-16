from .auth import bp as auth_bp
from .workspace import bp as workspace_bp
from .reports import bp as reports_bp
from .about import bp as about_bp
from .contacts import bp as contacts_bp


# admin — опционально
try:
    from .admin import bp as admin_bp
except ImportError:
    admin_bp = None


def init_app(app):
    """Регистрация всех blueprints в Flask-приложении"""

    # Проверяем, чтобы blueprint не регистрировался повторно
    if 'auth' not in app.blueprints:
        app.register_blueprint(auth_bp, url_prefix='/auth')

    if 'workspace' not in app.blueprints:
        app.register_blueprint(workspace_bp, url_prefix='/workspace')

    if 'reports' not in app.blueprints:
        app.register_blueprint(reports_bp, url_prefix='/reports')

    if 'about' not in app.blueprints:
        app.register_blueprint(about_bp, url_prefix='/about')

    if 'contacts' not in app.blueprints:
        app.register_blueprint(contacts_bp, url_prefix='/contacts')

    if admin_bp and 'admin' not in app.blueprints:
        app.register_blueprint(admin_bp, url_prefix='/admin')