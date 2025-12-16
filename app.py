from flask import Flask, render_template
from config import Config
from models import db, User
from flask_login import LoginManager
from routes import init_app


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Регистрируем блюпринты
    init_app(app)
    print(f"Registered Blueprints: {list(app.blueprints.keys())}")

    @app.route('/')
    def index():
        return render_template('index.html')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)