"""
App factory — creates the Flask app and registers all domain blueprints.
Route logic lives in api/blueprints/<domain>.py.
"""

import hmac
import os
from flask import Flask, render_template, request, session

from api.blueprints.user import user_bp
from api.blueprints.auth import auth_bp
from api.blueprints.nutrition import nutrition_bp
from api.blueprints.schedule import schedule_bp
from api.blueprints.chat import chat_bp
from api.blueprints.external import external_bp
from api.blueprints.health import health_bp
from api.blueprints.metrics import metrics_bp
from api.blueprints.activity import activity_bp
from api.blueprints.helpers import error_response

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static',
)

import config
app.secret_key = config.SECRET_KEY

# Session cookie hardening
app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY

# Session expiry — when SESSION_LIFETIME_MINUTES > 0, auth sessions get a TTL
# and (optionally) slide forward on each authenticated request.
if config.SESSION_LIFETIME_MINUTES > 0:
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=config.SESSION_LIFETIME_MINUTES)

for bp in (user_bp, auth_bp, nutrition_bp, schedule_bp, chat_bp, external_bp, health_bp, metrics_bp, activity_bp):
    app.register_blueprint(bp)


# CSRF protection — state-changing requests under an active session must
# echo the session's CSRF token via the X-CSRF-Token header. Pre-auth
# endpoints (login, user creation) are exempt because no token exists yet.
CSRF_EXEMPT_PATHS = {
    '/api/auth/login',
    '/api/user/create',
}
CSRF_WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


@app.before_request
def apply_session_expiry():
    """Give auth sessions a TTL and slide it forward while active."""
    if config.SESSION_LIFETIME_MINUTES <= 0:
        return None
    if session.get('user_id'):
        session.permanent = True
        if config.SESSION_REFRESH:
            # Touch the session so PERMANENT_SESSION_LIFETIME slides forward.
            session.modified = True
    return None


@app.before_request
def enforce_csrf():
    if not config.CSRF_PROTECTION:
        return None
    if request.method not in CSRF_WRITE_METHODS:
        return None
    if request.path in CSRF_EXEMPT_PATHS:
        return None
    if not session.get('user_id'):
        # No active session → nothing to protect; endpoint auth still applies.
        return None
    expected = session.get('csrf_token')
    provided = request.headers.get('X-CSRF-Token', '')
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        return error_response(
            'CSRF token missing or invalid. Refresh the page and try again.',
            'CSRF_FAILED',
            403,
        )
    return None


@app.route('/', methods=['GET'])
def index():
    """Serve the single-page frontend application."""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
