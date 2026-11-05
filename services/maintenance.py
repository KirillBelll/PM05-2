"""Резервное копирование и проверка целостности данных."""
import json
import os
from datetime import date, datetime
from decimal import Decimal

from flask import current_app
from sqlalchemy import text

from extensions import db

BACKUP_TABLES = [
    "roles", "users", "requirement_categories", "requirement_types", "projects",
    "project_members", "requirements", "trace_links",
]


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    raise TypeError(f"Тип {type(value)} не сериализуется")


def create_backup_file():
    """Выгрузить содержимое основных таблиц в JSON-файл.

    Возвращает (имя файла, размер в байтах, число таблиц, число строк).
    """
    backup_dir = current_app.config["BACKUP_DIR"]
    os.makedirs(backup_dir, exist_ok=True)

    payload = {"created_at": datetime.now().isoformat(sep=" ", timespec="seconds"), "tables": {}}
    rows_total = 0
    for table in BACKUP_TABLES:
        result = db.session.execute(text(f"SELECT * FROM `{table}`"))
        rows = [dict(r._mapping) for r in result]
        payload["tables"][table] = rows
        rows_total += len(rows)

    filename = f"reqtrace_{datetime.now():%Y%m%d_%H%M%S}.json"
    path = os.path.join(backup_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_json_default)

    return filename, os.path.getsize(path), len(BACKUP_TABLES), rows_total


# Каждая проверка — (код, описание, SQL, который возвращает «проблемные» строки)
INTEGRITY_CHECKS = [
    (
        "links_cross_project",
        "Связи трассировки между требованиями разных проектов",
        """SELECT l.id, CONCAT(s.code, ' → ', t.code) AS info
           FROM trace_links l
           JOIN requirements s ON s.id = l.source_id
           JOIN requirements t ON t.id = l.target_id
           WHERE s.project_id <> t.project_id""",
    ),
    (
        "req_no_category",
        "Требования без категории",
        """SELECT r.id, CONCAT(r.code, ' — ', r.title) AS info
           FROM requirements r WHERE r.category_id IS NULL""",
    ),
    (
        "req_orphan_low_level",
        "Требования нижнего уровня без связи с вышестоящим требованием",
        """SELECT r.id, CONCAT(r.code, ' — ', r.title) AS info
           FROM requirements r
           JOIN requirement_types t ON t.id = r.type_id
           WHERE t.level > 1
             AND NOT EXISTS (SELECT 1 FROM trace_links l WHERE l.source_id = r.id)""",
    ),
    (
        "req_approved_no_children",
        "Утверждённые требования заказчика, которые ещё не детализированы",
        """SELECT r.id, CONCAT(r.code, ' — ', r.title) AS info
           FROM requirements r
           JOIN requirement_types t ON t.id = r.type_id
           WHERE t.level = 1 AND r.status IN ('approved','implemented','verified')
             AND NOT EXISTS (SELECT 1 FROM trace_links l WHERE l.target_id = r.id)""",
    ),
    (
        "projects_no_manager",
        "Проекты без руководителя",
        """SELECT p.id, CONCAT(p.code, ' — ', p.name) AS info
           FROM projects p WHERE p.manager_id IS NULL""",
    ),
    (
        "inactive_members",
        "Заблокированные пользователи, состоящие в проектах",
        """SELECT m.id, CONCAT(u.login, ' в ', p.code) AS info
           FROM project_members m
           JOIN users u ON u.id = m.user_id
           JOIN projects p ON p.id = m.project_id
           WHERE u.is_active = 0""",
    ),
]


def run_integrity_checks():
    results = []
    for code, title, sql in INTEGRITY_CHECKS:
        rows = db.session.execute(text(sql)).fetchall()
        results.append({
            "code": code,
            "title": title,
            "count": len(rows),
            "rows": [r.info for r in rows[:8]],
        })
    return results
