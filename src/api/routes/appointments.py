from fastapi import APIRouter, Depends
from src.api.dependencies import verify_vapi_secret

from src.models.appointment import (
    AppointmentRequest,
    AppointmentResponse,
    FindAppointmentsRequest,
    FindAppointmentsResponse,
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
)

from src.services.appointment_service import (
    schedule_appointment,
    find_appointments,
    cancel_appointment,
    reschedule_appointment,
)


router = APIRouter()


@router.post(
    "/schedule_appointment/",
    response_model=AppointmentResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def schedule_appointment_route(request: AppointmentRequest):
    return schedule_appointment(request)


@router.post(
    "/find_appointments/",
    response_model=FindAppointmentsResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def find_appointments_route(request: FindAppointmentsRequest):
    return find_appointments(request)


@router.post(
    "/cancel_appointment/",
    response_model=CancelAppointmentResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def cancel_appointment_route(request: CancelAppointmentRequest):
    return cancel_appointment(request)


@router.post(
    "/reschedule_appointment/",
    response_model=RescheduleAppointmentResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def reschedule_appointment_route(request: RescheduleAppointmentRequest):
    return reschedule_appointment(request)