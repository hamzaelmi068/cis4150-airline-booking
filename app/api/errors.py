from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors import BookingError


def booking_error_handler(_request: Request, exc: BookingError) -> JSONResponse:
    body: dict[str, str] = {"error": exc.code, "detail": exc.message}
    if exc.booking_id is not None:
        body["booking_id"] = exc.booking_id
    return JSONResponse(status_code=exc.http_status, content=body)
