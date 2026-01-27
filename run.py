"""Entry point for the Flask application."""
import os
from app import create_app

# Determine environment - default to production for hosting platforms
env = os.environ.get('FLASK_ENV', 'production')

# Create the application
app = create_app(env)

if __name__ == '__main__':
    # Local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(env == 'development'))
