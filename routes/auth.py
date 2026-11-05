"""Аутентификация: вход и выход."""
from datetime import datetime
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db, login_manager
from forms import LoginForm
from models import User
from services.audit import log_action

bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.is_active else None


def _safe_next(target):
    """Разрешаем редирект только внутри сайта (защита от open redirect)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return None
    return target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data.strip()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login_at = datetime.now()
            log_action("login", "session", user.id, "Успешный вход", user=user)
            if not user.is_admin:
                flash("Ваша роль не даёт доступа к панели администратора.", "warning")
            else:
                flash(f"Добро пожаловать, {user.full_name}!", "success")
            return redirect(_safe_next(request.args.get("next")) or url_for("dashboard.index"))

        log_action("login_fail", "session", user.id if user else None,
                   f"Неудачная попытка входа под логином «{form.login.data[:50]}»", user=user)
        flash("Неверный логин или пароль, либо учётная запись заблокирована.", "error")

    return render_template("login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_action("logout", "session", current_user.id, "Выход из системы")
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))
