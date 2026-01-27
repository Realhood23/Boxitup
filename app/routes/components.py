"""Component management routes - search, browse, add new components."""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.models.component import Component, FeatureType, COMMON_FEATURES

components_bp = Blueprint('components', __name__)


@components_bp.route('/')
def index():
    """Browse all components."""
    # Get services
    from app.services.component_service import ComponentService
    service = ComponentService()

    # Get filter parameters
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    components = service.search_components(search=search, category=category)
    categories = service.get_categories()

    return render_template(
        'components/index.html',
        components=components,
        categories=categories,
        current_category=category,
        search_query=search
    )


@components_bp.route('/<component_id>')
def detail(component_id):
    """View component details."""
    from app.services.component_service import ComponentService
    service = ComponentService()

    component = service.get_component(component_id)
    if not component:
        flash('Component not found', 'error')
        return redirect(url_for('components.index'))

    return render_template('components/detail.html', component=component)


@components_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new component - either manually or via distributor URL."""
    if request.method == 'GET':
        return render_template(
            'components/add.html',
            feature_types=FeatureType,
            common_features=COMMON_FEATURES
        )

    # Handle POST - adding new component
    data = request.form.to_dict()

    # Check if URL was provided for auto-fetch
    distributor_url = data.get('distributor_url', '')
    if distributor_url:
        return redirect(url_for('components.fetch_from_url', url=distributor_url))

    # Manual component creation
    try:
        from app.services.component_service import ComponentService
        service = ComponentService()

        component = service.create_component_from_form(data, current_user)
        flash(f'Component "{component.name}" added successfully!', 'success')
        return redirect(url_for('components.detail', component_id=component.id))

    except Exception as e:
        flash(f'Error adding component: {str(e)}', 'error')
        return render_template(
            'components/add.html',
            feature_types=FeatureType,
            common_features=COMMON_FEATURES,
            form_data=data
        )


@components_bp.route('/fetch')
@login_required
def fetch_from_url():
    """Fetch component data from a distributor URL."""
    url = request.args.get('url', '')
    if not url:
        flash('Please provide a distributor URL', 'error')
        return redirect(url_for('components.add'))

    try:
        from app.services.nexar_service import NexarService
        nexar = NexarService()

        # Extract part number from URL and fetch data
        component_data = nexar.fetch_component_from_url(url)

        return render_template(
            'components/add.html',
            feature_types=FeatureType,
            common_features=COMMON_FEATURES,
            prefilled_data=component_data,
            source_url=url
        )

    except Exception as e:
        flash(f'Error fetching component data: {str(e)}', 'error')
        return redirect(url_for('components.add'))


@components_bp.route('/api/search')
def api_search():
    """API endpoint for component search (HTMX/AJAX)."""
    from app.services.component_service import ComponentService
    service = ComponentService()

    search = request.args.get('q', '')
    category = request.args.get('category', '')
    limit = request.args.get('limit', 20, type=int)

    components = service.search_components(
        search=search,
        category=category,
        limit=limit
    )

    # Return HTML partial for HTMX or JSON for API
    if request.headers.get('HX-Request'):
        return render_template(
            'components/_search_results.html',
            components=components
        )

    return jsonify([c.to_dict() for c in components])


@components_bp.route('/api/<component_id>')
def api_detail(component_id):
    """API endpoint for component details."""
    from app.services.component_service import ComponentService
    service = ComponentService()

    component = service.get_component(component_id)
    if not component:
        return jsonify({'error': 'Component not found'}), 404

    return jsonify(component.to_dict())


@components_bp.route('/api/categories')
def api_categories():
    """API endpoint for component categories."""
    from app.services.component_service import ComponentService
    service = ComponentService()

    return jsonify(service.get_categories())


@components_bp.route('/api/feature-types')
def api_feature_types():
    """API endpoint for available feature types."""
    return jsonify([
        {'value': ft.value, 'name': ft.name.replace('_', ' ').title()}
        for ft in FeatureType
    ])
