from fastapi import APIRouter, Depends

from app.api.deps import get_booking_service
from app.schemas import BookingResponse, ConfirmRequest, HoldRequest
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/holds", response_model=BookingResponse, status_code=201)
def hold_seat(
    body: HoldRequest,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    booking = service.hold_seat(
        flight_id=body.flight_id,
        seat_id=body.seat_id,
        passenger_name=body.passenger_name,
        passenger_email=body.passenger_email,
    )
    return BookingResponse.model_validate(booking)


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
def confirm_booking(
    booking_id: str,
    body: ConfirmRequest,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    booking = service.confirm_booking(booking_id, body.payment_token)
    return BookingResponse.model_validate(booking)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: str,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    return BookingResponse.model_validate(service.cancel_booking(booking_id))


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: str,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    return BookingResponse.model_validate(service.get_booking(booking_id))
