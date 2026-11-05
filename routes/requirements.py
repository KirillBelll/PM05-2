"""Требования, связи трассировки и матрица трассируемости."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import DeleteForm, LinkForm, RequirementForm
from models import Project, Requirement, RequirementCategory, RequirementType, TraceLink
from models.requirement import REQ_PRIORITIES, REQ_STATUSES
from services.audit import apply_form, changes_text, log_action
from services.security import admin_required

from .helpers import arg_int, filter_args, paginate

bp = Blueprint("requirements", __name__, url_prefix="/requirements")

FIELDS = ("project_id", "code", "title", "description", "type_id", "category_id",
          "priority", "status", "source")

SORTS = {
    "code": RequirementType.level.asc(),
    "-updated": Requirement.updated_at.desc(),
    "priority": db.case(
        {"critical": 0, "high": 1, "medium": 2, "low": 3}, value=Requirement.priority
    ),
}


def _fill_choices(form):
    form.project_id.choices = [(p.id, f"{p.code} — {p.name}") for p in Project.query.order_by(Project.code)]
    form.type_id.choices = [(t.id, f"{t.code} — {t.name}") for t in RequirementType.query.order_by(RequirementType.level)]
    form.category_id.choices = [(0, "— без категории —")] + [
        (c.id, c.name) for c in RequirementCategory.query.order_by(RequirementCategory.name)
    ]


def _apply(form, req):
    return apply_form(form, req, FIELDS, zero_is_null=("category_id",))


@bp.route("/")
@login_required
@admin_required
def list_requirements():
    query = Requirement.query.join(Project).join(RequirementType)
    q = request.args.get("q", "").strip()
    project_id, type_id, category_id = arg_int("project"), arg_int("type"), arg_int("category")
    status, priority = request.args.get("status"), request.args.get("priority")

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Requirement.code.ilike(like), Requirement.title.ilike(like),
                                 Requirement.description.ilike(like)))
    if project_id:
        query = query.filter(Requirement.project_id == project_id)
    if type_id:
        query = query.filter(Requirement.type_id == type_id)
    if category_id:
        query = query.filter(Requirement.category_id == category_id)
    if status in REQ_STATUSES:
        query = query.filter(Requirement.status == status)
    if priority in REQ_PRIORITIES:
        query = query.filter(Requirement.priority == priority)

    sort = request.args.get("sort", "code")
    order = SORTS.get(sort, SORTS["code"])
    query = query.order_by(Project.code, order, Requirement.code)

    pagination = paginate(query)
    return render_template(
        "admin/requirements_list.html", pagination=pagination, items=pagination.items,
        projects=Project.query.order_by(Project.code).all(),
        types=RequirementType.query.order_by(RequirementType.level).all(),
        categories=RequirementCategory.query.order_by(RequirementCategory.name).all(),
        statuses=REQ_STATUSES, priorities=REQ_PRIORITIES, sort=sort,
        args=filter_args(), delete_form=DeleteForm(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_requirement():
    form = RequirementForm()
    _fill_choices(form)
    if request.method == "GET" and arg_int("project"):
        form.project_id.data = arg_int("project")

    if form.validate_on_submit():
        req = Requirement(author_id=current_user.id)
        _apply(form, req)
        db.session.add(req)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append("Такой код уже есть в этом проекте")
        else:
            log_action("create", "requirement", req.id, f"Создано требование {req.code} «{req.title}»")
            flash("Требование добавлено.", "success")
            return redirect(url_for("requirements.view_requirement", req_id=req.id))
    return render_template("admin/requirement_form.html", form=form, req=None)


@bp.route("/<int:req_id>")
@login_required
@admin_required
def view_requirement(req_id):
    req = db.session.get(Requirement, req_id) or abort(404)
    link_form = LinkForm()
    linked = {l.target_id for l in req.outgoing}
    candidates = (
        Requirement.query.join(RequirementType)
        .filter(Requirement.project_id == req.project_id, Requirement.id != req.id,
                RequirementType.level <= req.type.level)
        .order_by(RequirementType.level, Requirement.code).all()
    )
    link_form.target_id.choices = [
        (r.id, f"{r.code} — {r.title[:70]}") for r in candidates if r.id not in linked
    ]
    return render_template("admin/requirement_view.html", req=req, link_form=link_form,
                           delete_form=DeleteForm())


@bp.route("/<int:req_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_requirement(req_id):
    req = db.session.get(Requirement, req_id) or abort(404)
    form = RequirementForm(obj=req)
    _fill_choices(form)
    if request.method == "GET":
        form.category_id.data = req.category_id or 0

    if form.validate_on_submit():
        changes = _apply(form, req)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            form.code.errors.append("Такой код уже есть в этом проекте")
        else:
            log_action("update", "requirement", req.id, changes_text(req.code, changes))
            flash("Требование обновлено.", "success")
            return redirect(url_for("requirements.view_requirement", req_id=req.id))
    return render_template("admin/requirement_form.html", form=form, req=req)


@bp.route("/<int:req_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_requirement(req_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    req = db.session.get(Requirement, req_id) or abort(404)
    links = len(req.outgoing) + len(req.incoming)
    info = f"Удалено требование {req.code} «{req.title}», связей удалено: {links}"
    project_id = req.project_id
    db.session.delete(req)
    log_action("delete", "requirement", req_id, info)
    flash("Требование удалено.", "success")
    if request.form.get("back") == "list":
        return redirect(url_for("requirements.list_requirements", project=project_id))
    return redirect(url_for("requirements.list_requirements"))


@bp.route("/<int:req_id>/links", methods=["POST"])
@login_required
@admin_required
def add_link(req_id):
    req = db.session.get(Requirement, req_id) or abort(404)
    form = LinkForm()
    form.target_id.choices = [
        (r.id, r.code) for r in Requirement.query.filter(Requirement.project_id == req.project_id)
    ]
    if form.validate_on_submit():
        if form.target_id.data == req.id:
            flash("Требование не может ссылаться само на себя.", "error")
        else:
            link = TraceLink(source_id=req.id, target_id=form.target_id.data,
                             link_type=form.link_type.data, comment=form.comment.data or None,
                             created_by=current_user.id)
            db.session.add(link)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                flash("Такая связь уже существует.", "error")
            else:
                target = db.session.get(Requirement, link.target_id)
                log_action("create", "link", link.id,
                           f"{req.code} —[{link.type_label}]→ {target.code}")
                flash("Связь трассировки добавлена.", "success")
    else:
        flash("Выберите требование для связи.", "error")
    return redirect(url_for("requirements.view_requirement", req_id=req.id))


@bp.route("/links/<int:link_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_link(link_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    link = db.session.get(TraceLink, link_id) or abort(404)
    back_id = int(request.form.get("back", link.source_id))
    info = f"{link.source.code} —[{link.type_label}]→ {link.target.code}"
    db.session.delete(link)
    log_action("delete", "link", link_id, info)
    flash("Связь удалена.", "success")
    return redirect(url_for("requirements.view_requirement", req_id=back_id))


@bp.route("/matrix")
@login_required
@admin_required
def matrix():
    projects = Project.query.order_by(Project.code).all()
    project_id = arg_int("project") or (projects[0].id if projects else None)
    project = db.session.get(Project, project_id) if project_id else None

    rows, cols, cells, uncovered = [], [], {}, []
    if project:
        reqs = (Requirement.query.join(RequirementType)
                .filter(Requirement.project_id == project.id)
                .order_by(RequirementType.level, Requirement.code).all())
        top_level = min((r.type.level for r in reqs), default=1)
        rows = [r for r in reqs if r.type.level == top_level]
        cols = [r for r in reqs if r.type.level > top_level]
        ids = {r.id for r in reqs}
        links = TraceLink.query.filter(TraceLink.source_id.in_(ids)).all() if ids else []

        # прямые связи + транзитивные (через промежуточные требования)
        parents = {}
        for l in links:
            parents.setdefault(l.source_id, set()).add((l.target_id, l.link_type))

        def ancestors(rid, seen=None):
            seen = seen or set()
            for pid, _ in parents.get(rid, ()):
                if pid not in seen:
                    seen.add(pid)
                    ancestors(pid, seen)
            return seen

        for c in cols:
            direct = {pid: lt for pid, lt in parents.get(c.id, ())}
            for anc in ancestors(c.id):
                cells[(anc, c.id)] = direct.get(anc, "indirect")
        covered = {r for (r, _c) in cells}
        uncovered = [r for r in rows if r.id not in covered]

    return render_template("admin/matrix.html", projects=projects, project=project,
                           rows=rows, cols=cols, cells=cells, uncovered=uncovered)
