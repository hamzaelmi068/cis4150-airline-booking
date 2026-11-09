from fastapi import APIRouter, Depends

from app.api.bookings import router as bookings_router
from app.api.deps import get_booking_service
from app.api.flights import router as flights_router
from app.schemas import ExpireHoldsResponse
from app.services.booking_service import BookingService

api_router = APIRouter()
api_router.include_router(flights_router)
api_router.include_router(bookings_router)


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.post(
    "/maintenance/expire-holds",
    response_model=ExpireHoldsResponse,
    tags=["system"],
)
def expire_holds(
    service: BookingService = Depends(get_booking_service),
) -> ExpireHoldsResponse:
    return ExpireHoldsResponse(expired=service.expire_elapsed_holds())
