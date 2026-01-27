"""Application configuration settings."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')

    # GitHub OAuth
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
    GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
    GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    GITHUB_API_URL = 'https://api.github.com'
    GITHUB_OAUTH_SCOPES = ['repo', 'user:email']

    # GitHub Components Repository
    GITHUB_COMPONENTS_REPO = os.environ.get('GITHUB_COMPONENTS_REPO', '')
    GITHUB_COMPONENTS_BRANCH = os.environ.get('GITHUB_COMPONENTS_BRANCH', 'main')

    # GitHub Bot Token (for writing components to the central repo)
    GITHUB_BOT_TOKEN = os.environ.get('GITHUB_BOT_TOKEN', '')

    # Nexar/Octopart API
    NEXAR_CLIENT_ID = os.environ.get('NEXAR_CLIENT_ID')
    NEXAR_CLIENT_SECRET = os.environ.get('NEXAR_CLIENT_SECRET')
    NEXAR_TOKEN_URL = 'https://identity.nexar.com/connect/token'
    NEXAR_API_URL = 'https://api.nexar.com/graphql'

    # DigiKey API (optional)
    DIGIKEY_CLIENT_ID = os.environ.get('DIGIKEY_CLIENT_ID')
    DIGIKEY_CLIENT_SECRET = os.environ.get('DIGIKEY_CLIENT_SECRET')

    # Cache settings
    CACHE_TTL_SECONDS = int(os.environ.get('CACHE_TTL_SECONDS', 86400))

    # Local storage for projects (before GitHub sync)
    PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'projects')
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
