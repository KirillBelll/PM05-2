from datetime import datetime

from extensions import db

PROJECT_STATUSES = {
    "planning": "Планирование",
    "active": "В работе",
    "on_hold": "Приостановлен",
    "closed": "Завершён",
}

ACCESS_LEVELS = {
    "read": "Чтение",
    "write": "Редактирование",
    "manage": "Управление",
}


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="planning")
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    manager = db.relationship("User")
    members = db.relationship(
        "ProjectMember", back_populates="project",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    requirements = db.relationship(
        "Requirement", back_populates="project", lazy="dynamic",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    @property
    def status_label(self):
        return PROJECT_STATUSES.get(self.status, self.status)


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (db.UniqueConstraint("project_id", "user_id", name="uq_member"),)

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_level = db.Column(db.String(10), nullable=False, default="read")
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User")

    @property
    def access_label(self):
        return ACCESS_LEVELS.get(self.access_level, self.access_level)
