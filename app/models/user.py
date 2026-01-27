"""User model for GitHub OAuth authentication."""
from dataclasses import dataclass
from flask_login import UserMixin
from typing import Optional
import json
import os

# Simple in-memory user store (in production, use a proper database)
_users = {}


@dataclass
class User(UserMixin):
    """
    User authenticated via GitHub OAuth.

    Stores GitHub user info and access token for API calls.
    """
    id: str                               # GitHub user ID
    username: str                         # GitHub username
    email: str
    name: str                             # Display name
    avatar_url: str
    github_token: str                     # OAuth access token

    def get_id(self):
        """Required by Flask-Login."""
        return self.id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
            # Don't serialize token for security
        }

    @classmethod
    def from_github_data(cls, github_data: dict, token: str) -> 'User':
        """Create User from GitHub API response."""
        return cls(
            id=str(github_data['id']),
            username=github_data['login'],
            email=github_data.get('email', ''),
            name=github_data.get('name', github_data['login']),
            avatar_url=github_data.get('avatar_url', ''),
            github_token=token
        )

    def save(self):
        """Save user to store."""
        _users[self.id] = self

    @classmethod
    def get(cls, user_id: str) -> Optional['User']:
        """Get user by ID."""
        return _users.get(user_id)

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """Get user by GitHub username."""
        for user in _users.values():
            if user.username == username:
                return user
        return None

    def __repr__(self):
        return f"<User {self.username}>"
