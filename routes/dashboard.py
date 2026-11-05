"""Главная страница панели: сводные показатели."""
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models import (
    AuditLog, Project, Requirement, RequirementCategory, RequirementType,
    TraceLink, User,
)
from models.requirement import REQ_STATUSES
from services.security import admin_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
@admin_required
def index():
    total_req = Requirement.query.count()
    linked_ids = db.session.query(TraceLink.source_id).union(
        db.session.query(TraceLink.target_id)
    ).subquery()
    linked_req = db.session.query(func.count()).select_from(linked_ids).scalar() or 0

    stats = {
        "projects": Project.query.count(),
        "projects_active": Project.query.filter_by(status="active").count(),
        "requirements": total_req,
        "links": TraceLink.query.count(),
        "users": User.query.count(),
        "users_active": User.query.filter_by(is_active=True).count(),
        "coverage": round(linked_req * 100 / total_req) if total_req else 0,
    }

    by_status_raw = dict(
        db.session.query(Requirement.status, func.count(Requirement.id))
        .group_by(Requirement.status).all()
    )
    by_status = [
        {"code": code, "label": label, "count": by_status_raw.get(code, 0)}
        for code, label in REQ_STATUSES.items()
    ]

    by_category = (
        db.session.query(RequirementCategory.name, RequirementCategory.color, func.count(Requirement.id))
        .outerjoin(Requirement, Requirement.category_id == RequirementCategory.id)
        .group_by(RequirementCategory.id)
        .order_by(func.count(Requirement.id).desc())
        .all()
    )

    by_type = (
        db.session.query(RequirementType.code, RequirementType.name, func.count(Requirement.id))
        .outerjoin(Requirement, Requirement.type_id == RequirementType.id)
        .group_by(RequirementType.id)
        .order_by(RequirementType.level)
        .all()
    )

    projects = (
        db.session.query(Project, func.count(Requirement.id))
        .outerjoin(Requirement, Requirement.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.code)
        .all()
    )

    recent = AuditLog.query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(7).all()

    return render_template(
        "admin/dashboard.html", stats=stats, by_status=by_status,
        by_category=by_category, by_type=by_type, projects=projects, recent=recent,
    )
