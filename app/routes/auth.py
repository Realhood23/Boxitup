"""GitHub OAuth authentication routes."""
import os
# Allow OAuth scope changes (GitHub returns comma-separated, we send space-separated)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from flask import Blueprint, redirect, url_for, request, session, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from requests_oauthlib import OAuth2Session

from app.models.user import User

auth_bp = Blueprint('auth', __name__)


def get_github_oauth():
    """Create GitHub OAuth2 session."""
    client_id = current_app.config['GITHUB_CLIENT_ID']
    redirect_uri = url_for('auth.callback', _external=True)

    return OAuth2Session(
        client_id,
        redirect_uri=redirect_uri,
        scope=current_app.config['GITHUB_OAUTH_SCOPES']
    )


@auth_bp.route('/login')
def login():
    """Initiate GitHub OAuth flow."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    github = get_github_oauth()
    authorization_url, state = github.authorization_url(
        current_app.config['GITHUB_AUTHORIZE_URL']
    )

    # Store state for CSRF protection
    session['oauth_state'] = state

    return redirect(authorization_url)


@auth_bp.route('/callback')
def callback():
    """Handle GitHub OAuth callback."""
    # Verify state for CSRF protection
    if request.args.get('state') != session.get('oauth_state'):
        flash('Authentication failed: Invalid state', 'error')
        return redirect(url_for('main.index'))

    github = get_github_oauth()

    try:
        # Exchange code for token
        token = github.fetch_token(
            current_app.config['GITHUB_TOKEN_URL'],
            client_secret=current_app.config['GITHUB_CLIENT_SECRET'],
            authorization_response=request.url
        )

        # Get user info from GitHub
        github = OAuth2Session(
            current_app.config['GITHUB_CLIENT_ID'],
            token=token
        )
        user_response = github.get(f"{current_app.config['GITHUB_API_URL']}/user")
        github_user = user_response.json()

        # Get email if not public
        if not github_user.get('email'):
            emails_response = github.get(f"{current_app.config['GITHUB_API_URL']}/user/emails")
            emails = emails_response.json()
            for email in emails:
                if email.get('primary'):
                    github_user['email'] = email['email']
                    break

        # Create or update user
        user = User.from_github_data(github_user, token['access_token'])
        user.save()

        # Log in the user
        login_user(user)

        flash(f'Welcome, {user.name}!', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Show user profile."""
    from flask import render_template
    return render_template('auth/profile.html')
