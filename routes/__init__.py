"""Маршруты приложения, разбитые на blueprints по разделам панели."""
from .auth import bp as auth_bp
from .dashboard import bp as dashboard_bp
from .users import bp as users_bp
from .projects import bp as projects_bp
from .requirements import bp as requirements_bp
from .dictionaries import bp as dictionaries_bp
from .audit import bp as audit_bp
from .maintenance import bp as maintenance_bp

ALL_BLUEPRINTS = [
    auth_bp, dashboard_bp, users_bp, projects_bp, requirements_bp,
    dictionaries_bp, audit_bp, maintenance_bp,
]
