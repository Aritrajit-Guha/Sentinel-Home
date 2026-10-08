from flask import Blueprint, jsonify, request, session

from app.core.auth import authenticate, create_user, current_user, login_user, public_user
from app.core.store import users


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register_account():
    payload = request.get_json(silent=True) or {}
    try:
        user = create_user(payload.get("email"), payload.get("password"))
        login_user(user)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    return jsonify({"status": "registered", "user": public_user(user)}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    user = authenticate(payload.get("email"), payload.get("password"))
    if user is None:
        return jsonify({"status": "error", "message": "Invalid email or password"}), 401
    login_user(user)
    return jsonify({"status": "ok", "user": public_user(user)})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"status": "logged_out"})


@auth_bp.get("/me")
def me():
    user = current_user()
    return jsonify({"authenticated": bool(user), "user": public_user(user)}), (200 if user else 401)
