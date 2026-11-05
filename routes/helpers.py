"""Общие функции для маршрутов."""
from flask import current_app, request


def get_page():
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def paginate(query):
    return query.paginate(
        page=get_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )


def arg_int(name):
    """Безопасно прочитать целочисленный параметр фильтра."""
    try:
        value = int(request.args.get(name, ""))
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def filter_args(exclude=("page",)):
    """Текущие параметры фильтра — для ссылок пагинации."""
    return {k: v for k, v in request.args.items() if k not in exclude and v}
