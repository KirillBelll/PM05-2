"""Проекты и права доступа участников."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import DeleteForm, MemberForm, ProjectForm
from models import Project, ProjectMember, Requirement, User
from models.project import PROJECT_STATUSES
from services.audit import apply_form, changes_text, log_action
from services.security import admin_required

from .helpers import filter_args, paginate

bp = Blueprint("projects", __name__, url_prefix="/projects")

FIELDS = ("code", "name", "description", "status", "manager_id", "start_date", "end_date")


def _manager_choices():
    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    return [(0, "— не назначен —")] + [(u.id, u.full_name) for u in users]


def _apply(form, project):
    return apply_form(form, project, FIELDS, zero_is_null=("manager_id",))


@bp.route("/")
@login_required
@admin_required
def list_projects():
    q = request.args.get("q", "").strip()
    status = request.args.get("status")

    query = (
        db.session.query(Project, func.count(Requirement.id).label("req_count"))
        .outerjoin(Requirement, Requirement.project_id == Project.id)
        .group_by(Project.id)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.code.ilike(like), Project.name.ilike(like)))
    if status in PROJECT_STATUSES:
        query = query.filter(Project.status == status)

    pagination = paginate(query.order_by(Project.code))
    return render_template(
        "admin/projects_list.html", pagination=pagination, rows=pagination.items,
        statuses=PROJECT_STATUSES, args=filter_args(), delete_form=DeleteForm(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_project():
    form = ProjectForm()
    form.manager_id.choices = _manager_choices()
    if form.validate_on_submit():
        project = Project()
        _apply(form, project)
        db.session.add(project)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Проект с таким шифром уже существует.", "error")
        else:
            log_action("create", "project", project.id, f"Создан проект {project.code} «{project.name}»")
            flash("Проект создан.", "success")
            return redirect(url_for("projects.view_project", project_id=project.id))
    return render_template("admin/project_form.html", form=form, project=None)


@bp.route("/<int:project_id>")
@login_required
@admin_required
def view_project(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    member_form = MemberForm()
    member_ids = {m.user_id for m in project.members}
    member_form.user_id.choices = [
        (u.id, f"{u.full_name} ({u.login})")
        for u in User.query.filter_by(is_active=True).order_by(User.full_name)
        if u.id not in member_ids
    ]
    req_stats = dict(
        db.session.query(Requirement.status, func.count(Requirement.id))
        .filter(Requirement.project_id == project.id)
        .group_by(Requirement.status).all()
    )
    return render_template(
        "admin/project_view.html", project=project, member_form=member_form,
        delete_form=DeleteForm(), req_stats=req_stats,
        req_total=sum(req_stats.values()),
    )


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_project(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    form = ProjectForm(obj=project)
    form.manager_id.choices = _manager_choices()
    if request.method == "GET":
        form.manager_id.data = project.manager_id or 0

    if form.validate_on_submit():
        changes = _apply(form, project)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Проект с таким шифром уже существует.", "error")
        else:
            log_action("update", "project", project.id, changes_text(project.code, changes))
            flash("Изменения сохранены.", "success")
            return redirect(url_for("projects.view_project", project_id=project.id))
    return render_template("admin/project_form.html", form=form, project=project)


@bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_project(project_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    project = db.session.get(Project, project_id) or abort(404)
    req_count = project.requirements.count()
    info = f"Удалён проект {project.code} «{project.name}» вместе с {req_count} требованиями"
    db.session.delete(project)
    log_action("delete", "project", project_id, info)
    flash("Проект удалён.", "success")
    return redirect(url_for("projects.list_projects"))


@bp.route("/<int:project_id>/members", methods=["POST"])
@login_required
@admin_required
def add_member(project_id):
    project = db.session.get(Project, project_id) or abort(404)
    form = MemberForm()
    form.user_id.choices = [(u.id, u.login) for u in User.query.filter_by(is_active=True)]
    if form.validate_on_submit():
        member = ProjectMember(project_id=project.id, user_id=form.user_id.data,
                               access_level=form.access_level.data)
        db.session.add(member)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Пользователь уже состоит в проекте.", "error")
        else:
            log_action("create", "member", member.id,
                       f"{project.code}: добавлен {member.user.login}, права «{member.access_label}»")
            flash("Участник добавлен.", "success")
    else:
        flash("Выберите пользователя и уровень доступа.", "error")
    return redirect(url_for("projects.view_project", project_id=project.id))


@bp.route("/<int:project_id>/members/<int:member_id>", methods=["POST"])
@login_required
@admin_required
def update_member(project_id, member_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    member = db.session.get(ProjectMember, member_id)
    if not member or member.project_id != project_id:
        abort(404)

    action = request.form.get("action")
    if action == "delete":
        info = f"{member.project.code}: исключён {member.user.login}"
        db.session.delete(member)
        log_action("delete", "member", member_id, info)
        flash("Участник исключён из проекта.", "success")
    elif request.form.get("access_level") in ("read", "write", "manage"):
        old = member.access_label
        member.access_level = request.form["access_level"]
        log_action("update", "member", member.id,
                   f"{member.project.code}: права {member.user.login} «{old}» → «{member.access_label}»")
        flash("Права доступа обновлены.", "success")
    else:
        abort(400)
    return redirect(url_for("projects.view_project", project_id=project_id))
