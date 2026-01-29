"""Project management routes - create, edit, manage enclosure projects."""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from app.models.project import Project, ProjectComponent, EnabledFeature
from app.models.enclosure import Enclosure, EnclosureShape, LidType, Hole, HoleType

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/')
@login_required
def index():
    """List user's projects."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    projects = service.get_user_projects(current_user.id)
    return render_template('projects/index.html', projects=projects)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create a new project."""
    if request.method == 'GET':
        return render_template(
            'projects/new.html',
            shapes=EnclosureShape,
            lid_types=LidType
        )

    # Handle POST
    from app.services.project_service import ProjectService
    service = ProjectService()

    try:
        project = service.create_project(
            name=request.form.get('name'),
            description=request.form.get('description', ''),
            user_id=current_user.id
        )
        flash(f'Project "{project.name}" created!', 'success')
        return redirect(url_for('projects.edit', project_id=project.id))

    except Exception as e:
        flash(f'Error creating project: {str(e)}', 'error')
        return render_template('projects/new.html')


@projects_bp.route('/<project_id>')
@login_required
def view(project_id):
    """View project details (read-only)."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.index'))

    return render_template('projects/view.html', project=project)


@projects_bp.route('/<project_id>/edit')
@login_required
def edit(project_id):
    """
    Edit project - the main project builder interface.

    This is where users:
    - Add/remove components
    - Toggle component features on/off
    - Position components in the enclosure
    - Configure enclosure settings
    - Place holes for enabled features
    """
    from app.services.project_service import ProjectService
    from app.services.component_service import ComponentService

    project_service = ProjectService()
    component_service = ComponentService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.index'))

    # Get available components for adding
    components = component_service.search_components(limit=100)
    categories = component_service.get_categories()

    # Check what features still need holes placed
    unplaced_features = project.get_all_unplaced_features()

    return render_template(
        'projects/editor.html',
        project=project,
        components=components,
        categories=categories,
        unplaced_features=unplaced_features,
        shapes=EnclosureShape,
        lid_types=LidType,
        hole_types=HoleType
    )


@projects_bp.route('/<project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    """Delete a project."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    if service.delete_project(project_id, current_user.id):
        flash('Project deleted', 'info')
    else:
        flash('Could not delete project', 'error')

    return redirect(url_for('projects.index'))


# ============ API Endpoints for Project Builder ============

@projects_bp.route('/api/<project_id>/components', methods=['POST'])
@login_required
def api_add_component(project_id):
    """Add a component to the project."""
    from app.services.project_service import ProjectService
    from app.services.component_service import ComponentService

    project_service = ProjectService()
    component_service = ComponentService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    component_id = data.get('component_id')

    component = component_service.get_component(component_id)
    if not component:
        return jsonify({'error': 'Component not found'}), 404

    # Add component with its features
    project_component = project.add_component(
        component_id=component.id,
        component_name=component.name,
        features=[f.to_dict() for f in component.features]
    )

    project_service.save_project(project)

    return jsonify({
        'success': True,
        'component': project_component.to_dict(),
        'unplaced_count': len(project.get_all_unplaced_features())
    })


@projects_bp.route('/api/<project_id>/components/<component_instance_id>', methods=['DELETE'])
@login_required
def api_remove_component(project_id, component_instance_id):
    """Remove a component from the project."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    project.remove_component(component_instance_id)
    service.save_project(project)

    return jsonify({'success': True})


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/position', methods=['PUT'])
@login_required
def api_update_position(project_id, component_instance_id):
    """Update component position in enclosure."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    updated_comp = None

    for comp in project.components:
        if comp.id == component_instance_id:
            # Accept both 'x'/'y' and 'x_mm'/'y_mm' formats
            comp.position_x_mm = data.get('x_mm', data.get('x', comp.position_x_mm))
            comp.position_y_mm = data.get('y_mm', data.get('y', comp.position_y_mm))
            comp.position_z_mm = data.get('z_mm', data.get('z', comp.position_z_mm))
            comp.rotation_deg = data.get('rotation', comp.rotation_deg)
            updated_comp = comp
            break

    service.save_project(project)

    return jsonify({
        'success': True,
        'position': {
            'x_mm': updated_comp.position_x_mm if updated_comp else 0,
            'y_mm': updated_comp.position_y_mm if updated_comp else 0,
            'z_mm': updated_comp.position_z_mm if updated_comp else 0
        }
    })


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/lock', methods=['PUT'])
@login_required
def api_update_lock(project_id, component_instance_id):
    """Update component lock state to prevent accidental movement."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    locked = data.get('locked', False)

    for comp in project.components:
        if comp.id == component_instance_id:
            comp.locked = locked
            break

    service.save_project(project)

    return jsonify({'success': True, 'locked': locked})


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/features', methods=['PUT'])
@login_required
def api_update_features(project_id, component_instance_id):
    """
    Update which features are enabled for a component.

    This is the toggle on/off for each feature that might need a hole.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    feature_states = data.get('features', {})  # {feature_id: enabled}

    for comp in project.components:
        if comp.id == component_instance_id:
            for feat in comp.enabled_features:
                if feat.feature_id in feature_states:
                    feat.enabled = feature_states[feat.feature_id]
            break

    project._update_ready_state()
    service.save_project(project)

    return jsonify({
        'success': True,
        'ready_to_generate': project.ready_to_generate,
        'unplaced_count': len(project.get_all_unplaced_features())
    })


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/features/<feature_id>', methods=['PUT'])
@login_required
def api_update_single_feature(project_id, component_instance_id, feature_id):
    """Update a single feature's properties (name, etc.)."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()

    for comp in project.components:
        if comp.id == component_instance_id:
            for feat in comp.enabled_features:
                if feat.feature_id == feature_id:
                    if 'feature_name' in data:
                        feat.feature_name = data['feature_name']
                    if 'enabled' in data:
                        feat.enabled = data['enabled']
                    break
            break

    service.save_project(project)

    return jsonify({'success': True})


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/features', methods=['POST'])
@login_required
def api_add_custom_feature(project_id, component_instance_id):
    """Add a custom feature to a component."""
    from app.services.project_service import ProjectService
    from app.models.project import EnabledFeature
    import uuid
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()

    for comp in project.components:
        if comp.id == component_instance_id:
            feature_id = f"custom_{uuid.uuid4().hex[:8]}"
            new_feature = EnabledFeature(
                feature_id=feature_id,
                feature_type=data.get('feature_type', 'cable_entry'),
                feature_name=data.get('feature_name', 'Custom Feature'),
                original_name=data.get('feature_name', 'Custom Feature'),
                enabled=True,  # Custom features start enabled
                hole_placed=False,
                is_custom=True,
                hole_width_mm=data.get('hole_width_mm', 10.0),
                hole_height_mm=data.get('hole_height_mm', 10.0),
                is_circular=data.get('is_circular', False),
                corner_radius_mm=data.get('corner_radius_mm', 0),
                required_face=data.get('required_face', 'front'),
                requires_external_access=True
            )
            comp.enabled_features.append(new_feature)

            service.save_project(project)

            return jsonify({
                'success': True,
                'feature': new_feature.to_dict()
            })

    return jsonify({'error': 'Component not found'}), 404


@projects_bp.route('/api/<project_id>/components/<component_instance_id>/features/<feature_id>', methods=['DELETE'])
@login_required
def api_remove_custom_feature(project_id, component_instance_id, feature_id):
    """Remove a custom feature from a component."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    for comp in project.components:
        if comp.id == component_instance_id:
            # Only allow removing custom features
            feat_to_remove = None
            for feat in comp.enabled_features:
                if feat.feature_id == feature_id and feat.is_custom:
                    feat_to_remove = feat
                    break

            if feat_to_remove:
                comp.enabled_features.remove(feat_to_remove)
                service.save_project(project)
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Feature not found or not removable'}), 404

    return jsonify({'error': 'Component not found'}), 404


@projects_bp.route('/api/<project_id>/enclosure', methods=['PUT'])
@login_required
def api_update_enclosure(project_id):
    """Update enclosure configuration."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()

    # Get existing enclosure or create new one
    if project.enclosure_config:
        enclosure = Enclosure.from_dict(project.enclosure_config)
    else:
        enclosure = Enclosure(
            inner_length_mm=100,
            inner_width_mm=60,
            inner_height_mm=30
        )

    # Update from the incoming data
    if 'dimensions' in data:
        dims = data['dimensions']
        enclosure.inner_length_mm = dims.get('inner_length_mm', enclosure.inner_length_mm)
        enclosure.inner_width_mm = dims.get('inner_width_mm', enclosure.inner_width_mm)
        enclosure.inner_height_mm = dims.get('inner_height_mm', enclosure.inner_height_mm)

    if 'wall_thickness_mm' in data:
        enclosure.wall_thickness_mm = data['wall_thickness_mm']
    if 'bottom_thickness_mm' in data:
        enclosure.bottom_thickness_mm = data['bottom_thickness_mm']
    if 'corner_radius_mm' in data:
        enclosure.corner_radius_mm = data['corner_radius_mm']
    if 'shape' in data:
        enclosure.shape = EnclosureShape(data['shape'])
    if 'lid' in data:
        lid = data['lid']
        if 'type' in lid:
            enclosure.lid_type = LidType(lid['type'])

    # Save the properly structured enclosure config
    project.enclosure_config = enclosure.to_dict()
    service.save_project(project)

    return jsonify({'success': True})


@projects_bp.route('/api/<project_id>/holes', methods=['POST'])
@login_required
def api_add_hole(project_id):
    """
    Add a hole to the enclosure.

    If linked to a component feature, also marks that feature's hole as placed.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()

    # Create enclosure if not exists
    if not project.enclosure_config:
        project.enclosure_config = Enclosure(
            inner_length_mm=100,
            inner_width_mm=60,
            inner_height_mm=30
        ).to_dict()

    enclosure = Enclosure.from_dict(project.enclosure_config)

    # Create the hole
    hole = Hole(
        id='',  # Will be auto-generated
        hole_type=HoleType(data.get('hole_type', 'component_access')),
        name=data.get('name', 'Hole'),
        face=data.get('face', 'front'),
        position_x_mm=data.get('x', 0),
        position_y_mm=data.get('y', 0),
        width_mm=data.get('width', 10),
        height_mm=data.get('height', 10),
        is_circular=data.get('is_circular', False),
        corner_radius_mm=data.get('corner_radius', 0),
        linked_component_id=data.get('component_id'),
        linked_feature_id=data.get('feature_id')
    )

    enclosure.add_hole(hole)
    project.enclosure_config = enclosure.to_dict()

    # If linked to a feature, mark it as placed
    if hole.linked_component_id and hole.linked_feature_id:
        project.mark_feature_hole_placed(
            hole.linked_component_id,
            hole.linked_feature_id,
            hole.id
        )

    service.save_project(project)

    return jsonify({
        'success': True,
        'hole': hole.to_dict(),
        'ready_to_generate': project.ready_to_generate,
        'unplaced_count': len(project.get_all_unplaced_features())
    })


@projects_bp.route('/api/<project_id>/holes/<hole_id>', methods=['DELETE'])
@login_required
def api_remove_hole(project_id, hole_id):
    """Remove a hole from the enclosure."""
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if project.enclosure_config:
        enclosure = Enclosure.from_dict(project.enclosure_config)

        # Find the hole to get linked feature info before removing
        for hole in enclosure.holes:
            if hole.id == hole_id:
                # Unmark the feature's hole as placed
                if hole.linked_component_id and hole.linked_feature_id:
                    for comp in project.components:
                        if comp.id == hole.linked_component_id:
                            for feat in comp.enabled_features:
                                if feat.feature_id == hole.linked_feature_id:
                                    feat.hole_placed = False
                                    feat.hole_id = None
                break

        enclosure.remove_hole(hole_id)
        project.enclosure_config = enclosure.to_dict()
        project._update_ready_state()
        service.save_project(project)

    return jsonify({
        'success': True,
        'ready_to_generate': project.ready_to_generate
    })


@projects_bp.route('/api/<project_id>/holes/<hole_id>/position', methods=['PUT'])
@login_required
def api_update_hole_position(project_id, hole_id):
    """
    Update a hole's position and properties.

    Used for drag-and-drop repositioning and inline form editing.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if not project.enclosure_config:
        return jsonify({'error': 'No enclosure configuration'}), 400

    data = request.get_json()
    enclosure = Enclosure.from_dict(project.enclosure_config)

    # Find and update the hole
    hole_found = False
    for hole in enclosure.holes:
        if hole.id == hole_id:
            hole_found = True
            # Update position
            if 'position_x_mm' in data:
                hole.position_x_mm = data['position_x_mm']
            if 'position_y_mm' in data:
                hole.position_y_mm = data['position_y_mm']
            # Update other properties
            if 'name' in data:
                hole.name = data['name']
            if 'face' in data:
                hole.face = data['face']
            if 'width_mm' in data:
                hole.width_mm = data['width_mm']
            if 'height_mm' in data:
                hole.height_mm = data['height_mm']
            if 'is_circular' in data:
                hole.is_circular = data['is_circular']
            break

    if not hole_found:
        return jsonify({'error': 'Hole not found'}), 404

    project.enclosure_config = enclosure.to_dict()
    service.save_project(project)

    return jsonify({
        'success': True,
        'hole': hole.to_dict()
    })


@projects_bp.route('/api/<project_id>/suggest-holes', methods=['GET'])
@login_required
def api_suggest_holes(project_id):
    """
    Get AI-suggested hole placements based on component features.

    This is the "auto-suggest" button functionality.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if project.enclosure_config:
        enclosure = Enclosure.from_dict(project.enclosure_config)
        suggestions = enclosure.suggest_hole_placements(project.components)
        return jsonify({'suggestions': suggestions})

    return jsonify({'suggestions': []})


@projects_bp.route('/api/<project_id>/validate', methods=['GET'])
@login_required
def api_validate(project_id):
    """
    Validate project is ready for OpenSCAD generation.

    Returns list of any issues that need to be resolved.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    is_valid, issues = project.validate_for_generation()

    return jsonify({
        'valid': is_valid,
        'issues': issues,
        'unplaced_features': [
            {
                'component': comp.component_name,
                'feature': feat.feature_name
            }
            for comp, feat in project.get_all_unplaced_features()
        ]
    })
