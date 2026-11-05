"""Резервное копирование и контроль целостности БД."""
import os

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template, send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from extensions import db
from forms import BackupForm, DeleteForm
from models import Backup
from services.audit import log_action
from services.maintenance import create_backup_file, run_integrity_checks
from services.security import admin_required

bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


@bp.route("/")
@login_required
@admin_required
def index():
    backups = Backup.query.order_by(Backup.created_at.desc()).limit(20).all()
    return render_template("admin/maintenance.html", backups=backups, form=BackupForm(),
                           delete_form=DeleteForm(), checks=None)


@bp.route("/backup", methods=["POST"])
@login_required
@admin_required
def make_backup():
    form = BackupForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        filename, size, tables, rows = create_backup_file()
    except OSError as exc:
        current_app.logger.exception("Ошибка резервного копирования")
        flash(f"Не удалось сохранить резервную копию: {exc}", "error")
        return redirect(url_for("maintenance.index"))

    backup = Backup(filename=filename, size_bytes=size, tables_cnt=tables, rows_cnt=rows,
                    comment=form.comment.data or None, created_by=current_user.id)
    db.session.add(backup)
    db.session.flush()
    log_action("backup", "backup", backup.id, f"Создана копия {filename}: {tables} таблиц, {rows} строк")
    flash(f"Резервная копия {filename} создана.", "success")
    return redirect(url_for("maintenance.index"))


@bp.route("/backup/<int:backup_id>/download")
@login_required
@admin_required
def download_backup(backup_id):
    backup = db.session.get(Backup, backup_id) or abort(404)
    directory = current_app.config["BACKUP_DIR"]
    if not os.path.isfile(os.path.join(directory, backup.filename)):
        abort(404)
    return send_from_directory(directory, backup.filename, as_attachment=True)


@bp.route("/backup/<int:backup_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_backup(backup_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    backup = db.session.get(Backup, backup_id) or abort(404)
    path = os.path.join(current_app.config["BACKUP_DIR"], backup.filename)
    if os.path.isfile(path):
        os.remove(path)
    name = backup.filename
    db.session.delete(backup)
    log_action("delete", "backup", backup_id, f"Удалена копия {name}")
    flash("Резервная копия удалена.", "success")
    return redirect(url_for("maintenance.index"))


@bp.route("/check", methods=["POST"])
@login_required
@admin_required
def check():
    if not DeleteForm().validate_on_submit():
        abort(400)
    checks = run_integrity_checks()
    problems = sum(c["count"] for c in checks)
    log_action("check", "database", None, f"Проверка целостности: замечаний {problems}")
    backups = Backup.query.order_by(Backup.created_at.desc()).limit(20).all()
    return render_template("admin/maintenance.html", backups=backups, form=BackupForm(),
                           delete_form=DeleteForm(), checks=checks, problems=problems)
