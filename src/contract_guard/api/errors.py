"""Consistent, request-correlated HTTP error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("contract_guard.errors")


_STATUS_CODES = {
    400: "INVALID_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _payload(
    request: Request,
    *,
    status_code: int,
    message: str,
    detail: Any = None,
    code: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "code": code or _STATUS_CODES.get(status_code, "REQUEST_FAILED"),
        "message": message,
        # ``requestId`` is the stable public field; ``detail`` remains during
        # the v1 compatibility window for existing API and UI clients.
        "requestId": _request_id(request),
        "detail": detail if detail is not None else message,
    }


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, str):
            message = detail
        elif isinstance(detail, dict) and isinstance(detail.get("message"), str):
            message = detail["message"]
        else:
            message = "请求未能完成"
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(
                request,
                status_code=exc.status_code,
                message=message,
                detail=detail,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "location": [str(item) for item in error.get("loc", ())],
                "message": str(error.get("msg", "输入不符合要求")),
                "type": str(error.get("type", "validation_error")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_payload(
                request,
                status_code=422,
                message="请检查填写内容",
                detail=errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled request error request_id=%s error_type=%s",
            _request_id(request),
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=_payload(
                request,
                status_code=500,
                message="服务暂时无法完成请求，请稍后重试",
            ),
        )


__all__ = ["install_exception_handlers"]
