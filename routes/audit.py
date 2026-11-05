"""Журнал действий администратора."""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from models import AuditLog, User
from models.service import AUDIT_ACTIONS, AUDIT_ENTITIES
from services.security import admin_required

from .helpers import arg_int, filter_args, paginate

bp = Blueprint("audit", __name__, url_prefix="/audit")


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


@bp.route("/")
@login_required
@admin_required
def index():
    query = AuditLog.query
    user_id = arg_int("user")
    action, entity = request.args.get("action"), request.args.get("entity")
    date_from, date_to = _parse_date(request.args.get("from")), _parse_date(request.args.get("to"))

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action in AUDIT_ACTIONS:
        query = query.filter(AuditLog.action == action)
    if entity in AUDIT_ENTITIES:
        query = query.filter(AuditLog.entity == entity)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at < date_to + timedelta(days=1))

    pagination = paginate(query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()))
    return render_template(
        "admin/audit.html", pagination=pagination, entries=pagination.items,
        users=User.query.order_by(User.full_name).all(), actions=AUDIT_ACTIONS,
        entities=AUDIT_ENTITIES, args=filter_args(),
    )
