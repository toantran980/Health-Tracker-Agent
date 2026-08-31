"""auth.py — Session-based authentication endpoints."""

from flask import Blueprint, request, jsonify, session

from api.blueprints import state
from api.blueprints.helpers import require_user, error_response, save_user_with_hash, get_csrf_token
from models.user_profile import UserProfile

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authenticate a user via its password and open a signed session cookie.

    Body (JSON):
        user_id  : str  (required)
        password : str  (required)
    """
    data = request.get_json(silent=True) or {}
    user_id = str(data.get('user_id', '')).strip()
    password = str(data.get('password', ''))

    if not user_id or not password:
        return error_response(
            "user_id and password are required", "MISSING_AUTH_FIELDS", 400
        )

    user, err = require_user(user_id)
    if err:
        return err

    from werkzeug.security import check_password_hash
    if not user.password_hash or not check_password_hash(user.password_hash, password):
        return error_response("Invalid credentials", "INVALID_CREDENTIALS", 401)

    session.clear()
    session["user_id"] = user.user_id
    return jsonify({
        "status": "authenticated",
        "user_id": user.user_id,
        "user": user.to_public_dict(),
        "csrf_token": get_csrf_token(),
    }), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Clear the session cookie."""
    session.clear()
    return jsonify({"status": "logged_out"}), 200


@auth_bp.route('/api/auth/me', methods=['GET'])
def me():
    """Return the authenticated user id (and CSRF token), or None if not logged in."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "authenticated": False,
            "user_id": None,
            "csrf_token": get_csrf_token(),
        }), 200

    user = state.users.get(user_id)
    if not user and state.mongo_store.enabled:
        doc = state.mongo_store.get_user(user_id)
        if doc:
            from api.blueprints.serialization_helpers import user_from_doc
            user = user_from_doc(doc)
            state.users[user_id] = user

    if not user:
        session.clear()
        return jsonify({
            "authenticated": False,
            "user_id": None,
            "csrf_token": get_csrf_token(),
        }), 200

    return jsonify({
        "authenticated": True,
        "user_id": user_id,
        "csrf_token": get_csrf_token(),
    }), 200


@auth_bp.route('/api/user/<user_id>/password', methods=['POST'])
def set_password(user_id):
    """
    Set (or reset) a user's password. Requires the password field.

    Body (JSON):
        password : str  (required, min 6 chars)
    """
    data = request.get_json(silent=True) or {}
    password = str(data.get('password', ''))

    if len(password) < 6:
        return error_response(
            "Password must be at least 6 characters", "PASSWORD_TOO_SHORT", 400
        )

    user, err = require_user(user_id)
    if err:
        return err

    from werkzeug.security import generate_password_hash
    user.password_hash = generate_password_hash(password)
    save_user_with_hash(user)
    return jsonify({"status": "success", "password_set": True}), 200