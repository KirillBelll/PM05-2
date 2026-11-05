"""Журналирование действий администратора.

Каждое действие пишется в две точки:
  * таблица audit_log (просмотр в разделе «Журнал действий»);
  * файл logs/admin.log (технический лог приложения).
"""
import logging

from flask import request
from flask_login import current_user

from extensions import db
from models import AuditLog

logger = logging.getLogger("reqtrace.audit")


def _client_ip():
    if not request:
        return None
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() or request.remote_addr or "")[:45]


def log_action(action, entity, entity_id=None, details=None, user=None, commit=True):
    """Записать действие в журнал.

    action    — create / update / delete / login / logout / backup / check
    entity    — тип объекта (user, project, requirement ...)
    entity_id — идентификатор объекта
    details   — краткое описание изменения
    """
    actor = user
    if actor is None and current_user and current_user.is_authenticated:
        actor = current_user

    entry = AuditLog(
        user_id=actor.id if actor is not None else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=(details or "")[:500] or None,
        ip_address=_client_ip(),
    )
    db.session.add(entry)
    if commit:
        db.session.commit()

    logger.info(
        "user=%s action=%s entity=%s id=%s ip=%s details=%s",
        actor.login if actor is not None else "-",
        action, entity, entity_id, entry.ip_address, details or "",
    )
    return entry


def _display(field, value):
    """Значение поля в понятном человеку виде (для журнала)."""
    if value is None or value == "":
        return "—"
    if field.type == "SelectField":
        return str(dict(field.choices or []).get(value, value))
    if field.type == "BooleanField":
        return "да" if value else "нет"
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y")
    return str(value)


def apply_form(form, obj, fields, zero_is_null=()):
    """Перенести данные формы в объект и вернуть список изменений.

    zero_is_null — поля-списки, где значение 0 означает «не выбрано».
    """
    changes = []
    for name in fields:
        field = getattr(form, name)
        new = field.data
        if isinstance(new, str):
            new = new.strip() or None
        if name in zero_is_null and not new:
            new = None
        old = getattr(obj, name, None)
        if old != new:
            if field.type == "TextAreaField":
                changes.append(f"{field.label.text}: изменено")
            else:
                changes.append(f"{field.label.text}: «{_display(field, old)}» → «{_display(field, new)}»")
            setattr(obj, name, new)
    return changes


def changes_text(prefix, changes):
    return f"{prefix}: " + ("; ".join(changes) if changes else "без изменений")
