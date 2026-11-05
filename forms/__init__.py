"""Формы WTForms. Каждая форма содержит скрытый CSRF-токен (hidden_tag)."""
import re

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DateField, PasswordField, SelectField, StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional, Regexp,
    ValidationError,
)
from wtforms.fields import IntegerField

from models.project import ACCESS_LEVELS, PROJECT_STATUSES
from models.requirement import LINK_TYPES, REQ_PRIORITIES, REQ_STATUSES

REQUIRED = "Поле обязательно для заполнения"


def _choices(mapping):
    return list(mapping.items())


class LoginForm(FlaskForm):
    login = StringField("Логин", validators=[DataRequired(REQUIRED), Length(min=3, max=50)])
    password = PasswordField("Пароль", validators=[DataRequired(REQUIRED), Length(min=3, max=128)])
    remember = BooleanField("Запомнить меня")


class DeleteForm(FlaskForm):
    """Пустая форма — нужна только ради CSRF-токена в кнопках удаления."""


class UserForm(FlaskForm):
    login = StringField("Логин", validators=[
        DataRequired(REQUIRED), Length(min=3, max=50),
        Regexp(r"^[a-zA-Z0-9_.-]+$", message="Только латиница, цифры и символы _ . -"),
    ])
    full_name = StringField("ФИО", validators=[DataRequired(REQUIRED), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(REQUIRED), Email("Некорректный email"), Length(max=150)])
    position = StringField("Должность", validators=[Optional(), Length(max=120)])
    role_id = SelectField("Роль", coerce=int, validators=[DataRequired(REQUIRED)])
    is_active = BooleanField("Учётная запись активна", default=True)
    password = PasswordField("Пароль", validators=[Optional(), Length(min=8, max=128, message="Не менее 8 символов")])
    password_confirm = PasswordField("Повтор пароля", validators=[EqualTo("password", message="Пароли не совпадают")])

    def validate_password(self, field):
        if field.data and not (re.search(r"\d", field.data) and re.search(r"[A-Za-zА-Яа-я]", field.data)):
            raise ValidationError("Пароль должен содержать буквы и цифры")


class ProjectForm(FlaskForm):
    code = StringField("Шифр проекта", validators=[
        DataRequired(REQUIRED), Length(max=20),
        Regexp(r"^[A-ZА-Я0-9-]+$", message="Заглавные буквы, цифры и дефис"),
    ])
    name = StringField("Наименование", validators=[DataRequired(REQUIRED), Length(max=200)])
    description = TextAreaField("Описание", validators=[Optional(), Length(max=5000)])
    status = SelectField("Статус", choices=_choices(PROJECT_STATUSES))
    manager_id = SelectField("Руководитель", coerce=int)
    start_date = DateField("Дата начала", validators=[Optional()])
    end_date = DateField("Дата окончания", validators=[Optional()])

    def validate_end_date(self, field):
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError("Дата окончания раньше даты начала")


class MemberForm(FlaskForm):
    user_id = SelectField("Пользователь", coerce=int, validators=[DataRequired(REQUIRED)])
    access_level = SelectField("Права доступа", choices=_choices(ACCESS_LEVELS))


class RequirementForm(FlaskForm):
    project_id = SelectField("Проект", coerce=int, validators=[DataRequired(REQUIRED)])
    code = StringField("Код", validators=[
        DataRequired(REQUIRED), Length(max=30),
        Regexp(r"^[A-ZА-Я]{2,6}-\d{1,4}(\.\d{1,3})*$", message="Формат: ТИП-001 или ТИП-001.2"),
    ])
    title = StringField("Формулировка", validators=[DataRequired(REQUIRED), Length(max=255)])
    description = TextAreaField("Описание / критерий приёмки", validators=[Optional(), Length(max=5000)])
    type_id = SelectField("Тип", coerce=int, validators=[DataRequired(REQUIRED)])
    category_id = SelectField("Категория", coerce=int)
    priority = SelectField("Приоритет", choices=_choices(REQ_PRIORITIES), default="medium")
    status = SelectField("Статус", choices=_choices(REQ_STATUSES), default="draft")
    source = StringField("Источник", validators=[Optional(), Length(max=255)])


class LinkForm(FlaskForm):
    target_id = SelectField("Вышестоящее требование", coerce=int, validators=[DataRequired(REQUIRED)])
    link_type = SelectField("Тип связи", choices=_choices(LINK_TYPES), default="derives")
    comment = StringField("Комментарий", validators=[Optional(), Length(max=255)])


class CategoryForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired(REQUIRED), Length(max=100)])
    description = StringField("Описание", validators=[Optional(), Length(max=255)])
    color = StringField("Цвет метки", default="#64748b", validators=[
        DataRequired(REQUIRED), Regexp(r"^#[0-9a-fA-F]{6}$", message="Цвет в формате #RRGGBB"),
    ])


class TypeForm(FlaskForm):
    code = StringField("Код", validators=[
        DataRequired(REQUIRED), Length(max=10),
        Regexp(r"^[A-ZА-Я]{2,6}$", message="2–6 заглавных букв"),
    ])
    name = StringField("Название", validators=[DataRequired(REQUIRED), Length(max=100)])
    level = IntegerField("Уровень декомпозиции", default=1, validators=[
        DataRequired(REQUIRED), NumberRange(min=1, max=5, message="От 1 до 5"),
    ])
    description = StringField("Описание", validators=[Optional(), Length(max=255)])


class BackupForm(FlaskForm):
    comment = StringField("Комментарий", validators=[Optional(), Length(max=255)])
