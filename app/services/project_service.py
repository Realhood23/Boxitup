"""Project service for managing user enclosure projects."""
import os
import json
from typing import Optional
from flask import current_app

from app.models.project import Project
from app.models.enclosure import Enclosure


class ProjectService:
    """
    Service for managing user projects.

    Projects are stored locally (not in GitHub) since they're user-specific.
    """

    def __init__(self):
        self._projects_dir = None

    @property
    def projects_dir(self):
        if self._projects_dir is None:
            self._projects_dir = current_app.config.get('PROJECTS_DIR')
            if not os.path.exists(self._projects_dir):
                os.makedirs(self._projects_dir, exist_ok=True)
        return self._projects_dir

    def _get_user_dir(self, user_id: str) -> str:
        """Get or create user's project directory."""
        user_dir = os.path.join(self.projects_dir, user_id)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _get_project_path(self, project_id: str, user_id: str) -> str:
        """Get path to project file."""
        return os.path.join(self._get_user_dir(user_id), f'{project_id}.json')

    def create_project(self, name: str, description: str, user_id: str) -> Project:
        """Create a new project with default enclosure configuration."""
        # Create default enclosure config
        default_enclosure = Enclosure(
            inner_length_mm=100,
            inner_width_mm=60,
            inner_height_mm=30
        )

        project = Project(
            id='',  # Will be auto-generated
            name=name,
            description=description,
            user_id=user_id,
            enclosure_config=default_enclosure.to_dict()
        )

        self.save_project(project)
        return project

    def get_project(self, project_id: str, user_id: str) -> Optional[Project]:
        """Get a project by ID."""
        path = self._get_project_path(project_id, user_id)

        if not os.path.exists(path):
            return None

        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return Project.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None

    def save_project(self, project: Project):
        """Save a project to disk."""
        path = self._get_project_path(project.id, project.user_id)

        with open(path, 'w') as f:
            json.dump(project.to_dict(), f, indent=2)

    def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project."""
        path = self._get_project_path(project_id, user_id)

        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_user_projects(self, user_id: str) -> list[Project]:
        """Get all projects for a user."""
        user_dir = self._get_user_dir(user_id)
        projects = []

        if not os.path.exists(user_dir):
            return projects

        for filename in os.listdir(user_dir):
            if filename.endswith('.json'):
                path = os.path.join(user_dir, filename)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        projects.append(Project.from_dict(data))
                except (json.JSONDecodeError, IOError):
                    continue

        # Sort by updated date, newest first
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def duplicate_project(self, project_id: str, user_id: str, new_name: str) -> Optional[Project]:
        """Create a copy of an existing project."""
        original = self.get_project(project_id, user_id)
        if not original:
            return None

        # Create new project with copied data
        new_project = Project(
            id='',  # New ID will be generated
            name=new_name,
            description=f"Copy of {original.name}",
            user_id=user_id,
            components=original.components.copy(),
            enclosure_config=original.enclosure_config.copy() if original.enclosure_config else None
        )

        self.save_project(new_project)
        return new_project
