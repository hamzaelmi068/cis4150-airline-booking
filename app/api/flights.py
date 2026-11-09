from fastapi import APIRouter, Depends

from app.api.deps import get_booking_service
from app.domain.enums import SeatStatus
from app.schemas import FlightResponse, SeatResponse
from app.services.booking_service import BookingService

router = APIRouter(tags=["flights"])


@router.get("/flights", response_model=list[FlightResponse])
def list_flights(
    service: BookingService = Depends(get_booking_service),
) -> list[FlightResponse]:
    return [FlightResponse.model_validate(flight) for flight in service.list_flights()]


@router.get("/flights/{flight_id}", response_model=FlightResponse)
def get_flight(
    flight_id: str,
    service: BookingService = Depends(get_booking_service),
) -> FlightResponse:
    return FlightResponse.model_validate(service.get_flight(flight_id))


@router.get("/flights/{flight_id}/seats", response_model=list[SeatResponse])
def list_seats(
    flight_id: str,
    status: SeatStatus | None = None,
    service: BookingService = Depends(get_booking_service),
) -> list[SeatResponse]:
    seats = service.list_seats(flight_id, status)
    return [SeatResponse.model_validate(seat) for seat in seats]
