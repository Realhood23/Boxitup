"""OpenSCAD script generation routes."""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user

generator_bp = Blueprint('generator', __name__)


@generator_bp.route('/<project_id>/preview')
@login_required
def preview(project_id):
    """
    Preview the enclosure before generating.

    Shows 3D visualization of the enclosure with all components and holes.
    """
    from app.services.project_service import ProjectService
    service = ProjectService()

    project = service.get_project(project_id, current_user.id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.index'))

    # Validate project
    is_valid, issues = project.validate_for_generation()

    return render_template(
        'generator/preview.html',
        project=project,
        is_valid=is_valid,
        issues=issues
    )


@generator_bp.route('/<project_id>/generate', methods=['POST'])
@login_required
def generate(project_id):
    """
    Generate the OpenSCAD script.

    Only allowed if all required holes have been placed.
    """
    from app.services.project_service import ProjectService
    from app.services.openscad_service import OpenSCADService

    project_service = ProjectService()
    openscad_service = OpenSCADService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Validate before generating
    is_valid, issues = project.validate_for_generation()
    if not is_valid:
        return jsonify({
            'error': 'Project is not ready for generation',
            'issues': issues
        }), 400

    try:
        # Generate the OpenSCAD script
        script = openscad_service.generate_script(project)

        return jsonify({
            'success': True,
            'script': script,
            'filename': f"{project.name.replace(' ', '_')}_enclosure.scad"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@generator_bp.route('/<project_id>/download')
@login_required
def download(project_id):
    """
    Download the generated OpenSCAD script as a file.
    """
    from app.services.project_service import ProjectService
    from app.services.openscad_service import OpenSCADService

    project_service = ProjectService()
    openscad_service = OpenSCADService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.index'))

    # Validate before generating
    is_valid, issues = project.validate_for_generation()
    if not is_valid:
        flash('Cannot generate: ' + ', '.join(issues), 'error')
        return redirect(url_for('generator.preview', project_id=project_id))

    try:
        script = openscad_service.generate_script(project)
        filename = f"{project.name.replace(' ', '_')}_enclosure.scad"

        return Response(
            script,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        flash(f'Error generating script: {str(e)}', 'error')
        return redirect(url_for('generator.preview', project_id=project_id))


@generator_bp.route('/<project_id>/download-lid')
@login_required
def download_lid(project_id):
    """
    Download just the lid as a separate OpenSCAD file.

    Useful for printing lid and body with different settings.
    """
    from app.services.project_service import ProjectService
    from app.services.openscad_service import OpenSCADService

    project_service = ProjectService()
    openscad_service = OpenSCADService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.index'))

    try:
        script = openscad_service.generate_lid_script(project)
        filename = f"{project.name.replace(' ', '_')}_lid.scad"

        return Response(
            script,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        flash(f'Error generating lid script: {str(e)}', 'error')
        return redirect(url_for('generator.preview', project_id=project_id))


@generator_bp.route('/api/<project_id>/script')
@login_required
def api_get_script(project_id):
    """API endpoint to get the generated script without downloading."""
    from app.services.project_service import ProjectService
    from app.services.openscad_service import OpenSCADService

    project_service = ProjectService()
    openscad_service = OpenSCADService()

    project = project_service.get_project(project_id, current_user.id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    is_valid, issues = project.validate_for_generation()
    if not is_valid:
        return jsonify({
            'error': 'Project not ready',
            'issues': issues
        }), 400

    try:
        script = openscad_service.generate_script(project)
        return jsonify({
            'script': script,
            'filename': f"{project.name.replace(' ', '_')}_enclosure.scad"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
