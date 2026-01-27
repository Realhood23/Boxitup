"""Route blueprints for the Enclosure Generator application."""
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.components import components_bp
from app.routes.projects import projects_bp
from app.routes.generator import generator_bp

__all__ = ['main_bp', 'auth_bp', 'components_bp', 'projects_bp', 'generator_bp']
