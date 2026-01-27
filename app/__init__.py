"""
Enclosure Generator - Flask Application Factory
A web app for generating 3D-printable enclosures for electronics projects.
"""
from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app(config_name='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in with GitHub to access this feature.'

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.components import components_bp
    from app.routes.projects import projects_bp
    from app.routes.generator import generator_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(components_bp, url_prefix='/components')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(generator_bp, url_prefix='/generator')

    # Setup user loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    return app
