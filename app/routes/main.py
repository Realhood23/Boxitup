"""Main routes for the application."""
from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page with overview of the application."""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page with documentation."""
    return render_template('about.html')


@main_bp.route('/docs')
def docs():
    """Documentation and help."""
    return render_template('docs.html')
