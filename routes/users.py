"""Управление пользователями и ролями."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import DeleteForm, UserForm
from models import Role, User
from services.audit import apply_form, changes_text, log_action
from services.security import admin_required

from .helpers import arg_int, filter_args, paginate

bp = Blueprint("users", __name__, url_prefix="/users")


def _role_choices():
    return [(r.id, r.name) for r in Role.query.order_by(Role.id).all()]


@bp.route("/")
@login_required
@admin_required
def list_users():
    query = User.query
    q = request.args.get("q", "").strip()
    role_id = arg_int("role")
    status = request.args.get("status")

    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.login.ilike(like), User.full_name.ilike(like), User.email.ilike(like)))
    if role_id:
        query = query.filter(User.role_id == role_id)
    if status in ("active", "blocked"):
        query = query.filter(User.is_active == (status == "active"))

    pagination = paginate(query.order_by(User.full_name))
    return render_template(
        "admin/users_list.html", pagination=pagination, users=pagination.items,
        roles=Role.query.order_by(Role.id).all(), args=filter_args(), delete_form=DeleteForm(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    form = UserForm()
    form.role_id.choices = _role_choices()
    if request.method == "GET":
        form.is_active.data = True

    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Для нового пользователя пароль обязателен")
        else:
            user = User(
                login=form.login.data.strip(), full_name=form.full_name.data.strip(),
                email=form.email.data.strip().lower(), position=form.position.data or None,
                role_id=form.role_id.data, is_active=form.is_active.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                flash("Пользователь с таким логином или email уже существует.", "error")
            else:
                log_action("create", "user", user.id, f"Создан пользователь {user.login} ({user.full_name})")
                flash("Пользователь создан.", "success")
                return redirect(url_for("users.list_users"))

    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    form = UserForm(obj=user)
    form.role_id.choices = _role_choices()

    if form.validate_on_submit():
        if user.id == current_user.id and (not form.is_active.data or form.role_id.data != user.role_id):
            flash("Нельзя заблокировать себя или снять с себя роль администратора.", "error")
            return render_template("admin/user_form.html", form=form, user=user)

        form.email.data = (form.email.data or "").strip().lower()
        changes = apply_form(form, user, ("login", "full_name", "email", "position", "role_id", "is_active"))
        if form.password.data:
            user.set_password(form.password.data)
            changes.append("пароль изменён")
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Пользователь с таким логином или email уже существует.", "error")
        else:
            log_action("update", "user", user.id, changes_text(user.login, changes))
            flash("Изменения сохранены.", "success")
            return redirect(url_for("users.list_users"))

    return render_template("admin/user_form.html", form=form, user=user)


@bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        abort(400)
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("Нельзя удалить собственную учётную запись.", "error")
        return redirect(url_for("users.list_users"))

    info = f"Удалён пользователь {user.login} ({user.full_name})"
    db.session.delete(user)
    log_action("delete", "user", user_id, info)
    flash("Пользователь удалён.", "success")
    return redirect(url_for("users.list_users"))
