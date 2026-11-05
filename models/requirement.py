from datetime import datetime

from extensions import db

REQ_STATUSES = {
    "draft": "Черновик",
    "review": "На согласовании",
    "approved": "Утверждено",
    "implemented": "Реализовано",
    "verified": "Проверено",
    "rejected": "Отклонено",
}

REQ_PRIORITIES = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
    "critical": "Критический",
}

LINK_TYPES = {
    "derives": "Выводится из",
    "refines": "Уточняет",
    "satisfies": "Удовлетворяет",
    "verifies": "Проверяет",
    "depends": "Зависит от",
}


class Requirement(db.Model):
    __tablename__ = "requirements"
    __table_args__ = (db.UniqueConstraint("project_id", "code", name="uq_req_code"),)

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("requirement_categories.id", ondelete="SET NULL"))
    type_id = db.Column(db.Integer, db.ForeignKey("requirement_types.id"), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    status = db.Column(db.String(15), nullable=False, default="draft")
    source = db.Column(db.String(255))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    project = db.relationship("Project", back_populates="requirements")
    category = db.relationship("RequirementCategory", back_populates="requirements")
    type = db.relationship("RequirementType", back_populates="requirements")
    author = db.relationship("User")

    outgoing = db.relationship(
        "TraceLink", foreign_keys="TraceLink.source_id", back_populates="source",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    incoming = db.relationship(
        "TraceLink", foreign_keys="TraceLink.target_id", back_populates="target",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    @property
    def status_label(self):
        return REQ_STATUSES.get(self.status, self.status)

    @property
    def priority_label(self):
        return REQ_PRIORITIES.get(self.priority, self.priority)


class TraceLink(db.Model):
    __tablename__ = "trace_links"
    __table_args__ = (
        db.UniqueConstraint("source_id", "target_id", "link_type", name="uq_link"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    link_type = db.Column(db.String(10), nullable=False, default="derives")
    comment = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    source = db.relationship("Requirement", foreign_keys=[source_id], back_populates="outgoing")
    target = db.relationship("Requirement", foreign_keys=[target_id], back_populates="incoming")

    @property
    def type_label(self):
        return LINK_TYPES.get(self.link_type, self.link_type)
