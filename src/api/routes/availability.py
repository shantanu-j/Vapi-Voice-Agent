from fastapi import APIRouter, Depends
from src.api.dependencies import verify_vapi_secret

from src.models.availability import (
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    AvailableSlotsRequest,
    AvailableSlotsResponse,
)

from src.services.availability_service import (
    check_availability,
    available_slots,
)


router = APIRouter()


@router.post(
    "/check_availability/",
    response_model=CheckAvailabilityResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def check_availability_route(request: CheckAvailabilityRequest):
    return check_availability(request)


@router.post(
    "/available_slots/",
    response_model=AvailableSlotsResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def available_slots_route(request: AvailableSlotsRequest):
    return available_slots(request)