from fastapi import Request

from app.services.booking_service import BookingService


def get_booking_service(request: Request) -> BookingService:
    return request.app.state.booking_service
