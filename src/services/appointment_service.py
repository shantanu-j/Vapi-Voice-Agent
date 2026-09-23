import logging
from fastapi import HTTPException
from config.settings import DELEGATED_USER

from src.integrations.bigquery import (
    find_existing_appointment,
    find_appointments_for_day,
    get_appointment_by_id,
    insert_appointment,
    cancel_appointment_by_id,
    find_conflicting_appointments,
    reschedule_appointment_by_id,
)

from src.integrations.google_calendar import (
    create_meeting,
    cancel_meeting,
    update_meeting,
)

from src.models.appointment import (
    AppointmentRequest,
    AppointmentResponse,
    FindAppointmentsRequest,
    FindAppointmentsResponse,
    AppointmentSummary,
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
)

from src.core.logging import get_logger

log = get_logger("statai.appointment_service")


def schedule_appointment(request: AppointmentRequest,) -> AppointmentResponse:
    """
    Schedule an appointment.
    The appointment is first checked for an existing matching
    record to make the operation idempotent.
    """

    phone_number = request.phone_number

    log.info("schedule_appointment called | phone=%s | start_time=%s | timezone=%s | name=%s", phone_number, request.start_date_time, request.timezone, request.name,)

    # Check for an existing appointment.
    existing = find_existing_appointment(
        phone_number=phone_number,
        start_time=request.start_date_time,
    )

    if existing:
        log.info(
            "Existing appointment found | appointment_id=%s | phone=%s | start_time=%s",
            existing["appointment_id"],
            phone_number,
            request.start_date_time,
        )

        return AppointmentResponse(
            appointment_id=existing["appointment_id"],
            email_id=existing["email_id"],
            phone_number=existing["phone_number"],
            name=existing["name"],
            reason=existing["reason"],
            start_time=existing["start_time"],
            canceled=existing["canceled"],
            meet_link=existing.get("meet_link"),
            timezone=existing.get("timezone"),
        )

    # Create Google Calendar event.
    log.info(
        "Creating calendar meeting | phone=%s | start_time=%s | timezone=%s",
        phone_number,
        request.start_date_time,
        request.timezone,
    )

    event_id, meet_link = create_meeting(
        email_id=DELEGATED_USER,
        phone_number=phone_number,
        name=request.name,
        reason=request.reason,
        start_time=request.start_date_time,
        timezone=request.timezone,
    )

    if event_id is None:
        log.error(
            "Calendar meeting creation failed | phone=%s | start_time=%s",
            phone_number,
            request.start_date_time,
        )

        raise HTTPException(
            status_code=500,
            detail="I couldn't complete the appointment booking at the moment.",
        )

    log.info(
        "Calendar meeting created | event_id=%s | phone=%s",
        event_id,
        phone_number,
    )

    # Save appointment in BigQuery.
    appointment_id = insert_appointment(
        email_id=DELEGATED_USER,
        phone_number=phone_number,
        name=request.name,
        reason=request.reason,
        start_time=request.start_date_time,
        calendar_event_id=event_id,
        timezone=request.timezone,
        meet_link=meet_link,
    )

    log.info(
        "Appointment saved | appointment_id=%s | event_id=%s | phone=%s",
        appointment_id,
        event_id,
        phone_number,
    )

    return AppointmentResponse(
        appointment_id=appointment_id,
        email_id=DELEGATED_USER,
        phone_number=phone_number,
        name=request.name,
        reason=request.reason,
        start_time=request.start_date_time,
        canceled=False,
        meet_link=meet_link,
        timezone=request.timezone,
    )


def find_appointments(request: FindAppointmentsRequest,) -> FindAppointmentsResponse:
    """
    Find active appointments for a phone number.
    """

    matches = find_appointments_for_day(phone_number=request.phone_number, date_=request.date, only_active=True,)

    return FindAppointmentsResponse(
        appointments=[
            AppointmentSummary(
                appointment_id=appointment["appointment_id"],
                start_time=appointment["start_time"],
                name=appointment["name"],
                reason=appointment["reason"],
                timezone=appointment.get("timezone"),
            )
            for appointment in matches
        ]
    )


def cancel_appointment(request: CancelAppointmentRequest,) -> CancelAppointmentResponse:
    """
    Cancel an existing appointment.
    The appointment must exist, be active, and belong to
    the provided phone number.
    """

    appointment = get_appointment_by_id(request.appointment_id)

    if appointment is None or appointment["canceled"]:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    canceled_count = cancel_appointment_by_id(appointment_id=request.appointment_id, phone_number=request.phone_number, cancellation_reason=request.cancellation_reason,)

    if canceled_count == 0:
        raise HTTPException(status_code=409, detail="Appointment could not be canceled — it may have just been canceled already.",)

    cancel_meeting(appointment.get("calendar_event_id"))

    log.info("Appointment canceled | appointment_id=%s | phone=%s", request.appointment_id, request.phone_number,)

    return CancelAppointmentResponse(
        success=True,
        message=(
            f"Appointment on "
            f"{appointment['start_time'].strftime('%b %d, %Y at %I:%M %p')} "
            f"has been canceled."
        ),
    )


def reschedule_appointment(
    request: RescheduleAppointmentRequest,
) -> RescheduleAppointmentResponse:
    """
    Reschedule an existing appointment.
    The same appointment ID and Calendar event are retained.
    """

    appointment = get_appointment_by_id(request.appointment_id)

    if appointment is None or appointment["canceled"]:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    # Verify appointment ownership.
    if appointment["phone_number"] != request.phone_number:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    # Idempotency: appointment is already at the requested time.
    if appointment["start_time"] == request.new_start_date_time:
        return RescheduleAppointmentResponse(
            appointment_id=appointment["appointment_id"],
            start_time=appointment["start_time"],
            message="Your appointment is already scheduled for that time.",
        )

    # Check whether the new time conflicts with another appointment.
    conflicts = find_conflicting_appointments(
        request.new_start_date_time,
        exclude_appointment_id=request.appointment_id,
    )

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail="That new time is already booked. Please suggest a different time."
        )

    timezone = (
        appointment.get("timezone")
        or "America/Los_Angeles"
    )

    # Update Google Calendar event first.
    calendar_updated = update_meeting(
        event_id=appointment.get("calendar_event_id"),
        start_time=request.new_start_date_time,
        timezone=timezone,
    )

    if not calendar_updated:
        raise HTTPException(
            status_code=500,
            detail="I couldn't reschedule the appointment at the moment.",
        )

    # Update BigQuery after Calendar succeeds.
    updated_count = reschedule_appointment_by_id(
        appointment_id=request.appointment_id,
        phone_number=request.phone_number,
        new_start_time=request.new_start_date_time,
    )

    if updated_count == 0:
        log.error("BigQuery appointment update failed after Calendar update | appointment_id=%s", request.appointment_id,)
        raise HTTPException(
            status_code=500,
            detail="I couldn't complete the appointment reschedule.",
        )

    log.info(
        "Appointment rescheduled | appointment_id=%s | old_start=%s | new_start=%s",
        request.appointment_id,
        appointment["start_time"],
        request.new_start_date_time,
    )

    return RescheduleAppointmentResponse(
        appointment_id=appointment["appointment_id"],
        start_time=request.new_start_date_time,
        message="SUCCESS: Your appointment has been rescheduled successfully.",
    )