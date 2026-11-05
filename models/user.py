from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Role(db.Model):
    __tablename__ = "roles"

    ADMIN = "admin"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self):
        return f"<Role {self.code}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    position = db.Column(db.String(120))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    last_login_at = db.Column(db.DateTime)

    role = db.relationship("Role", back_populates="users")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except ValueError:
            return False

    @property
    def is_admin(self) -> bool:
        return self.role is not None and self.role.code == Role.ADMIN

    @property
    def initials(self) -> str:
        parts = (self.full_name or self.login).split()
        return "".join(p[0] for p in parts[:2]).upper()

    def __repr__(self):
        return f"<User {self.login}>"
