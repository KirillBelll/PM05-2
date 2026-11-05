"""Точка входа: панель администратора ИС «Инженерные требования и трассируемость»."""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import OperationalError

from config import Config
from extensions import csrf, db, login_manager


def configure_logging(app):
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(app.config["LOG_DIR"], "admin.log"),
        maxBytes=1_000_000, backupCount=5, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    for name in ("reqtrace.audit", app.logger.name):
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in log.handlers):
            log.addHandler(file_handler)


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/error.html", code=400, title="Некорректный запрос",
                               message="Сервер не смог обработать запрос. Проверьте введённые данные."), 400

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        app.logger.warning("CSRF: %s %s — %s", request.method, request.path, e.description)
        return render_template("errors/error.html", code=400, title="Форма устарела",
                               message="Токен защиты формы отсутствует или истёк. "
                                       "Обновите страницу и повторите действие."), 400

    @app.errorhandler(401)
    def unauthorized(e):
        flash("Войдите в систему, чтобы продолжить.", "info")
        return redirect(url_for("auth.login", next=request.full_path))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/error.html", code=403, title="Доступ запрещён",
                               message="Раздел доступен только пользователям с ролью «Администратор»."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/error.html", code=404, title="Страница не найдена",
                               message="Запрошенная страница или запись не существует."), 404

    @app.errorhandler(OperationalError)
    def db_unavailable(e):
        db.session.rollback()
        app.logger.error("Ошибка соединения с БД: %s", e)
        return render_template("errors/error.html", code=503, title="База данных недоступна",
                               message="Не удалось выполнить запрос к MySQL. Проверьте, что сервер "
                                       "запущен и параметры подключения в .env верны."), 503

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.exception("Внутренняя ошибка: %s", e)
        return render_template("errors/error.html", code=500, title="Внутренняя ошибка сервера",
                               message="Произошла непредвиденная ошибка. Сведения записаны в журнал."), 500


def register_template_helpers(app):
    from models.project import ACCESS_LEVELS, PROJECT_STATUSES
    from models.requirement import LINK_TYPES, REQ_PRIORITIES, REQ_STATUSES

    @app.template_filter("dt")
    def format_datetime(value, fmt="%d.%m.%Y %H:%M"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("d")
    def format_date(value):
        return value.strftime("%d.%m.%Y") if value else "—"

    @app.template_filter("filesize")
    def filesize(value):
        value = value or 0
        for unit in ("Б", "КБ", "МБ"):
            if value < 1024:
                return f"{value:.0f} {unit}" if unit == "Б" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} ГБ"

    @app.context_processor
    def labels():
        return {
            "REQ_STATUSES": REQ_STATUSES, "REQ_PRIORITIES": REQ_PRIORITIES,
            "LINK_TYPES": LINK_TYPES, "PROJECT_STATUSES": PROJECT_STATUSES,
            "ACCESS_LEVELS": ACCESS_LEVELS,
        }


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from routes import ALL_BLUEPRINTS
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    configure_logging(app)
    register_error_handlers(app)
    register_template_helpers(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.teardown_request
    def commit_or_rollback(exc):
        if exc is not None:
            db.session.rollback()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
