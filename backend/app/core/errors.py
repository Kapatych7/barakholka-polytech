"""Единый формат ошибок API (контракт, раздел 2.3).

{"error": {"code": "AD_NOT_FOUND", "message": "Объявление не найдено", "details": {}}}
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


# Коды по умолчанию для ошибок, которые FastAPI/Starlette выбрасывают сами
_DEFAULT_CODES = {
    400: ("BAD_REQUEST", "Некорректный формат запроса"),
    401: ("UNAUTHORIZED", "Пользователь не авторизован или токен недействителен"),
    403: ("FORBIDDEN", "Недостаточно прав для выполнения действия"),
    404: ("NOT_FOUND", "Ресурс не найден"),
    405: ("METHOD_NOT_ALLOWED", "Метод не поддерживается"),
    409: ("CONFLICT", "Конфликт с текущим состоянием данных"),
    413: ("FILE_TOO_LARGE", "Загруженный файл слишком большой"),
    415: ("UNSUPPORTED_FILE_TYPE", "Неподдерживаемый формат файла"),
    422: ("VALIDATION_ERROR", "Данные не прошли проверку"),
    500: ("INTERNAL_ERROR", "Внутренняя ошибка сервера"),
}


def _validation_details(exc: RequestValidationError) -> dict[str, Any]:
    errors = exc.errors()
    if not errors:
        return {}
    first = errors[0]
    loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path")]
    details: dict[str, Any] = {"field": ".".join(loc) if loc else None, "reason": first.get("msg")}
    ctx = first.get("ctx") or {}
    if first.get("type") == "string_too_short" and "min_length" in ctx:
        details["min_length"] = ctx["min_length"]
    if first.get("type") == "extra_forbidden":
        details["reason"] = "Поле нельзя изменять через этот запрос"
    return details


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        code, message = _DEFAULT_CODES[422]
        return JSONResponse(status_code=422, content=error_body(code, message, _validation_details(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _DEFAULT_CODES.get(exc.status_code, ("ERROR", str(exc.detail)))
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message),
            headers=getattr(exc, "headers", None),
        )
