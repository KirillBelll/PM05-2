"""Справочники: категории и типы требований."""
from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms import CategoryForm, DeleteForm, TypeForm
from models import Requirement, RequirementCategory, RequirementType
from services.audit import apply_form, changes_text, log_action
from services.security import admin_required

bp = Blueprint("dictionaries", __name__, url_prefix="/dictionaries")


def _counts(column):
    return dict(db.session.query(column, func.count(Requirement.id)).group_by(column).all())


@bp.route("/")
@login_required
@admin_required
def index():
    return render_template(
        "admin/dictionaries.html",
        categories=RequirementCategory.query.order_by(RequirementCategory.name).all(),
        types=RequirementType.query.order_by(RequirementType.level, RequirementType.code).all(),
        cat_counts=_counts(Requirement.category_id), type_counts=_counts(Requirement.type_id),
        delete_form=DeleteForm(),
    )


# ---------- generic helpers ----------

def _save(model, form, obj, entity, fields, template, title):
    is_new = obj is None
    if form.validate_on_submit():
        obj = obj or model()
        changes = apply_form(form, obj, fields)
        db.session.add(obj)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Запись с таким названием или кодом уже существует.", "error")
        else:
            if is_new:
                log_action("create", entity, obj.id, f"Добавлено: {obj.name}")
            else:
                log_action("update", entity, obj.id, changes_text(obj.name, changes))
            flash("Справочник обновлён.", "success")
            return redirect(url_for("dictionaries.index"))
    return render_template(template, form=form, obj=obj, title=title)


@bp.route("/categories/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_category():
    return _save(RequirementCategory, CategoryForm(), None, "category",
                 ("name", "description", "color"), "admin/dictionary_form.html", "Новая категория")


@bp.route("/categories/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_category(item_id):
    obj = db.session.get(RequirementCategory, item_id) or abort(404)
    return _save(RequirementCategory, CategoryForm(obj=obj), obj, "category",
                 ("name", "description", "color"), "admin/dictionary_form.html", "Категория требований")


@bp.route("/categories/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_category(item_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    obj = db.session.get(RequirementCategory, item_id) or abort(404)
    used = obj.requirements.count()
    name = obj.name
    db.session.delete(obj)
    log_action("delete", "category", item_id, f"Удалена категория «{name}», требований без категории: {used}")
    flash("Категория удалена." + (f" У {used} требований категория сброшена." if used else ""), "success")
    return redirect(url_for("dictionaries.index"))


@bp.route("/types/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_type():
    return _save(RequirementType, TypeForm(), None, "type",
                 ("code", "name", "level", "description"), "admin/dictionary_form.html", "Новый тип требования")


@bp.route("/types/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_type(item_id):
    obj = db.session.get(RequirementType, item_id) or abort(404)
    return _save(RequirementType, TypeForm(obj=obj), obj, "type",
                 ("code", "name", "level", "description"), "admin/dictionary_form.html", "Тип требования")


@bp.route("/types/<int:item_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_type(item_id):
    if not DeleteForm().validate_on_submit():
        abort(400)
    obj = db.session.get(RequirementType, item_id) or abort(404)
    used = obj.requirements.count()
    if used:
        flash(f"Тип «{obj.name}» используется в {used} требованиях — удаление запрещено.", "error")
        return redirect(url_for("dictionaries.index"))
    name = obj.name
    db.session.delete(obj)
    log_action("delete", "type", item_id, f"Удалён тип «{name}»")
    flash("Тип требования удалён.", "success")
    return redirect(url_for("dictionaries.index"))
