from datetime import datetime

from extensions import db

AUDIT_ACTIONS = {
    "create": "Создание",
    "update": "Изменение",
    "delete": "Удаление",
    "login": "Вход",
    "logout": "Выход",
    "login_fail": "Неудачный вход",
    "backup": "Резервная копия",
    "check": "Проверка целостности",
}

AUDIT_ENTITIES = {
    "user": "Пользователь",
    "project": "Проект",
    "member": "Участник проекта",
    "requirement": "Требование",
    "link": "Связь трассировки",
    "category": "Категория",
    "type": "Тип требования",
    "backup": "Резервная копия",
    "session": "Сессия",
    "database": "База данных",
}


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(20), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship("User")

    @property
    def action_label(self):
        return AUDIT_ACTIONS.get(self.action, self.action)

    @property
    def entity_label(self):
        return AUDIT_ENTITIES.get(self.entity, self.entity)


class Backup(db.Model):
    __tablename__ = "backups"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    tables_cnt = db.Column(db.Integer, nullable=False, default=0)
    rows_cnt = db.Column(db.Integer, nullable=False, default=0)
    comment = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    author = db.relationship("User")
