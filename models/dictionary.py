from extensions import db


class RequirementCategory(db.Model):
    __tablename__ = "requirement_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    color = db.Column(db.String(7), nullable=False, default="#64748b")

    requirements = db.relationship("Requirement", back_populates="category", lazy="dynamic")


class RequirementType(db.Model):
    __tablename__ = "requirement_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    level = db.Column(db.SmallInteger, nullable=False, default=1)
    description = db.Column(db.String(255))

    requirements = db.relationship("Requirement", back_populates="type", lazy="dynamic")
