"""GitHub API service for managing the component database repository."""
import requests
import base64
import json
from typing import Optional
from flask import current_app


class GitHubService:
    """
    Service for interacting with the GitHub component database repository.

    Components are stored as individual JSON files in the repository.
    This service handles reading, writing, and committing component data.
    """

    def __init__(self, token: str = None):
        """
        Initialize GitHub service.

        Args:
            token: GitHub access token. If None, will be read-only for public repos.
        """
        self.token = token
        self.api_url = 'https://api.github.com'
        self._repo = None
        self._branch = None

    @property
    def repo(self):
        if self._repo is None:
            self._repo = current_app.config.get('GITHUB_COMPONENTS_REPO', '')
        return self._repo

    @property
    def branch(self):
        if self._branch is None:
            self._branch = current_app.config.get('GITHUB_COMPONENTS_BRANCH', 'main')
        return self._branch

    def _headers(self):
        """Get request headers."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'EnclosureGenerator/1.0'
        }
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        return headers

    def get_file_content(self, path: str) -> Optional[dict]:
        """
        Get file content from the repository.

        Args:
            path: File path relative to repository root

        Returns:
            Dict with file content and metadata, or None if not found
        """
        url = f'{self.api_url}/repos/{self.repo}/contents/{path}'
        params = {'ref': self.branch}

        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return {
                'content': content,
                'sha': data['sha'],
                'path': data['path']
            }
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()

    def list_files(self, path: str = '', extension: str = None) -> list[dict]:
        """
        List files in a directory.

        Args:
            path: Directory path relative to repository root
            extension: Filter by file extension (e.g., '.json')

        Returns:
            List of file info dicts
        """
        url = f'{self.api_url}/repos/{self.repo}/contents/{path}'
        params = {'ref': self.branch}

        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code != 200:
            if response.status_code == 404:
                return []
            response.raise_for_status()

        files = []
        for item in response.json():
            if item['type'] == 'file':
                if extension is None or item['name'].endswith(extension):
                    files.append({
                        'name': item['name'],
                        'path': item['path'],
                        'sha': item['sha'],
                        'size': item['size']
                    })
            elif item['type'] == 'dir':
                # Recursively list subdirectories
                subfiles = self.list_files(item['path'], extension)
                files.extend(subfiles)

        return files

    def create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
        committer_name: str,
        committer_email: str,
        sha: str = None
    ) -> dict:
        """
        Create or update a file in the repository.

        Args:
            path: File path relative to repository root
            content: File content (string)
            message: Commit message
            committer_name: Name of the committer
            committer_email: Email of the committer
            sha: SHA of existing file (required for updates)

        Returns:
            Dict with commit info
        """
        if not self.token:
            raise ValueError("GitHub token required for write operations")

        url = f'{self.api_url}/repos/{self.repo}/contents/{path}'

        # Encode content to base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')

        data = {
            'message': message,
            'content': content_base64,
            'branch': self.branch,
            'committer': {
                'name': committer_name,
                'email': committer_email
            }
        }

        if sha:
            data['sha'] = sha

        response = requests.put(url, headers=self._headers(), json=data)

        if response.status_code not in (200, 201):
            response.raise_for_status()

        return response.json()

    def delete_file(
        self,
        path: str,
        message: str,
        committer_name: str,
        committer_email: str,
        sha: str
    ) -> dict:
        """
        Delete a file from the repository.

        Args:
            path: File path relative to repository root
            message: Commit message
            committer_name: Name of the committer
            committer_email: Email of the committer
            sha: SHA of the file to delete

        Returns:
            Dict with commit info
        """
        if not self.token:
            raise ValueError("GitHub token required for write operations")

        url = f'{self.api_url}/repos/{self.repo}/contents/{path}'

        data = {
            'message': message,
            'sha': sha,
            'branch': self.branch,
            'committer': {
                'name': committer_name,
                'email': committer_email
            }
        }

        response = requests.delete(url, headers=self._headers(), json=data)

        if response.status_code != 200:
            response.raise_for_status()

        return response.json()

    def get_component(self, component_id: str) -> Optional[dict]:
        """
        Get a component by ID.

        Components are stored in components/{category}/{id}.json
        This method searches all categories.
        """
        # First try to find the component file
        files = self.list_files('components', '.json')

        for file_info in files:
            if file_info['name'] == f'{component_id}.json':
                result = self.get_file_content(file_info['path'])
                if result:
                    return {
                        'data': json.loads(result['content']),
                        'sha': result['sha'],
                        'path': result['path']
                    }

        return None

    def list_components(self, category: str = None) -> list[dict]:
        """
        List all components, optionally filtered by category.

        Args:
            category: Category folder name, or None for all

        Returns:
            List of component data dicts
        """
        if category:
            path = f'components/{category}'
        else:
            path = 'components'

        files = self.list_files(path, '.json')
        components = []

        for file_info in files:
            result = self.get_file_content(file_info['path'])
            if result:
                try:
                    component_data = json.loads(result['content'])
                    component_data['_sha'] = result['sha']
                    component_data['_path'] = result['path']
                    components.append(component_data)
                except json.JSONDecodeError:
                    continue

        return components

    def save_component(
        self,
        component_data: dict,
        user_name: str,
        user_email: str,
        existing_sha: str = None
    ) -> dict:
        """
        Save a component to the repository.

        Args:
            component_data: Component data dict
            user_name: Name of the user making the commit
            user_email: Email of the user
            existing_sha: SHA if updating existing component

        Returns:
            Commit info dict
        """
        component_id = component_data.get('id')
        category = component_data.get('category', 'other')

        if not component_id:
            raise ValueError("Component must have an ID")

        path = f'components/{category}/{component_id}.json'
        content = json.dumps(component_data, indent=2)

        if existing_sha:
            message = f'Update component: {component_data.get("name", component_id)}'
        else:
            message = f'Add component: {component_data.get("name", component_id)}'

        return self.create_or_update_file(
            path=path,
            content=content,
            message=message,
            committer_name=user_name,
            committer_email=user_email,
            sha=existing_sha
        )

    def get_categories(self) -> list[str]:
        """Get list of component categories (subdirectories of components/)."""
        url = f'{self.api_url}/repos/{self.repo}/contents/components'
        params = {'ref': self.branch}

        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code != 200:
            if response.status_code == 404:
                return []
            response.raise_for_status()

        categories = []
        for item in response.json():
            if item['type'] == 'dir':
                categories.append(item['name'])

        return sorted(categories)

    def get_user_info(self) -> Optional[dict]:
        """Get info about the authenticated user."""
        if not self.token:
            return None

        url = f'{self.api_url}/user'
        response = requests.get(url, headers=self._headers())

        if response.status_code == 200:
            return response.json()
        return None
