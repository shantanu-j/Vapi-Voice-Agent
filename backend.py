import datetime as dt
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from bq_database import (
    insert_appointment,
    find_existing_appointment,
    find_conflicting_appointments,
    find_appointments_for_day,
    get_appointment_by_id,
    cancel_appointment_by_id,
    find_appointments_between,
    reschedule_appointment_by_id,
    insert_complaint,
    APPOINTMENT_DURATION_MINUTES,
)
# from email_processor import process_email as process_email_logic
from settings import VAPI_SERVER_SECRET, DELEGATED_USER
from calendar_service import create_meeting, cancel_meeting, update_meeting

from logging_config import get_logger
log = get_logger("statai.backend")

app = FastAPI()

def verify_vapi_secret(x_webhook_secret: str = Header(None)):
    if x_webhook_secret != VAPI_SERVER_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

class AppointmentRequest(BaseModel):
    name: str
    reason: str
    phone_number: str
    start_date_time: dt.datetime
    timezone: str

class AppointmentResponse(BaseModel):
    appointment_id: str
    email_id: str
    phone_number: str
    name: str | None
    reason: str | None
    start_time: dt.datetime
    canceled: bool
    meet_link: str | None = None
    timezone: str | None = None

class CheckAvailabilityRequest(BaseModel):
    start_date_time: dt.datetime

class CheckAvailabilityResponse(BaseModel):
    available: bool
    message: str

class FindAppointmentsRequest(BaseModel):
    phone_number: str
    date: dt.date | None = None

class AppointmentSummary(BaseModel):
    appointment_id: str
    start_time: dt.datetime
    name: str | None
    reason: str | None
    timezone: str | None = None

class FindAppointmentsResponse(BaseModel):
    appointments: list[AppointmentSummary]

class CancelAppointmentRequest(BaseModel):
    appointment_id: str
    name: str
    phone_number: str
    cancellation_reason: str

class CancelAppointmentResponse(BaseModel):
    success: bool
    message: str

class NoteComplaintRequest(BaseModel):
    name: str
    phone_number: str
    issue: str

class NoteComplaintResponse(BaseModel):
    complaint_id: str
    message: str

class AvailableSlotsRequest(BaseModel):
    date: dt.date
    timezone: str | None = None

class AvailableSlotsResponse(BaseModel):
    date: dt.date
    timezone: str
    has_availability: bool
    first_slot_display: str | None
    slots_display: list[str]
    message: str

# class ProcessEmailRequest(BaseModel):
#     email_id: str

# class ProcessEmailResponse(BaseModel):
#     status: str
#     original_email: str | None = None
#     normalized_email: str | None = None
#     mailbox_verified: bool
#     confirmation_required: bool
#     clarification_required: bool
#     natural_readback: str | None = None
#     spelling: str | None = None
#     safe_to_send: bool | None = None
#     reason: str

class RescheduleAppointmentRequest(BaseModel):
    appointment_id: str
    phone_number: str
    new_start_date_time: dt.datetime

class RescheduleAppointmentResponse(BaseModel):
    appointment_id: str
    start_time: dt.datetime
    message: str


# ---------- Endpoints ----------

@app.get("/")
@app.post("/")
def root():
    return {
        "status": "ok",
        "message": "Statfinity AI backend is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# @app.post("/process_email/", response_model=ProcessEmailResponse, dependencies=[Depends(verify_vapi_secret)])
# def process_email(request: ProcessEmailRequest):
#     """
#     Validate the email value supplied by VapiAI.
#     This endpoint validates the resulting email value and performs
#     mailbox verification through QuickEmailVerification.
#     """
#     log.info("process_email called | email=%s", request.email_id)
#     result = process_email_logic(request.email_id)
#     log.info(
#         "process_email result | email=%s | status=%s | mailbox_verified=%s",
#         request.email_id, result.get("status"), result.get("mailbox_verified"),
#     )
#     return ProcessEmailResponse(**result)


@app.post("/check_availability/", response_model=CheckAvailabilityResponse, dependencies=[Depends(verify_vapi_secret)])
def check_availability(request: CheckAvailabilityRequest):
    """
    Call this endpoint BEFORE schedule_appointment. 
    """
    conflicts = find_conflicting_appointments(request.start_date_time)
    if conflicts:
        return CheckAvailabilityResponse(
            available=False,
            message="That time is already booked. Please suggest a different time.",
        )
    return CheckAvailabilityResponse(
        available=True,
        message="That time is available.",
    )

@app.post("/available_slots/", response_model=AvailableSlotsResponse, dependencies=[Depends(verify_vapi_secret)])
def available_slots(request: AvailableSlotsRequest):
    """
    Returns the free windows on request.date, across the full 24-hour calendar day PST by default.
    """
    tz_name = request.timezone or "America/Los_Angeles"  # PST/PDT, DST-aware
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail="Unrecognized timezone.")

    day_start_local = dt.datetime.combine(request.date, dt.time.min, tzinfo=tz)
    day_end_local = day_start_local + dt.timedelta(days=1)

    window_start = day_start_local.astimezone(dt.timezone.utc)
    window_end = day_end_local.astimezone(dt.timezone.utc)

    booked = sorted(find_appointments_between(window_start, window_end), key=lambda a: a["start_time"])

    free_windows: list[tuple[dt.datetime, dt.datetime]] = []
    cursor = window_start
    for appt in booked:
        appt_start = appt["start_time"]
        if appt_start > cursor:
            free_windows.append((cursor, appt_start))
        appt_end = appt_start + dt.timedelta(minutes=APPOINTMENT_DURATION_MINUTES)
        cursor = max(cursor, appt_end)
    if cursor < window_end:
        free_windows.append((cursor, window_end))

    def fmt(t: dt.datetime) -> str:
        return t.astimezone(tz).strftime("%I:%M %p").lstrip("0")

    slots_display = [f"{fmt(s)} to {fmt(e)}" for s, e in free_windows]

    if not free_windows:
        message = "No availability on that date."
    elif len(free_windows) == 1:
        message = f"Available from {slots_display[0]}"
    else:
        message = "Multiple free windows available"

    return AvailableSlotsResponse(
        date=request.date,
        timezone=tz_name,
        has_availability=bool(free_windows),
        first_slot_display=fmt(free_windows[0][0]) if free_windows else None,
        slots_display=slots_display,
        message=message,
    )


@app.post("/schedule_appointment/", response_model=AppointmentResponse, dependencies=[Depends(verify_vapi_secret)])
def schedule_appointment(request: AppointmentRequest):
    """
    Schedule an appointment after availability has already been confirmed.
    This endpoint assumes /check_availability/ was called first and only reaches
    this endpoint if available=True was returned.
    """
    phone_number = request.phone_number

    log.info(
        "schedule_appointment called | phone=%s | start_time=%s | name=%s",   # 3 placeholders
        phone_number, request.start_date_time, request.name, request.timezone,  # 4 args
    )


    # Check whether this appointment already exists
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


    # No existing appointment → create Google Calendar event
    log.info(
        "Creating calendar meeting | phone=%s | start_time=%s",   # 2 placeholders
        phone_number, request.start_date_time, request.timezone,   # 3 args
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
            detail="I couldn't complete the appointment booking at the moment."
        )

    log.info(
        "Calendar meeting created | event_id=%s | phone=%s",
        event_id,
        phone_number,
    )

    # Save appointment in BigQuery
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


    # Return successful appointment
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


@app.post("/find_appointments/", response_model=FindAppointmentsResponse, dependencies=[Depends(verify_vapi_secret)])
def find_appointments(request: FindAppointmentsRequest):
    """
    Cancellation. It returns every active appointment.
    """
    # email = request.email_id
    matches = find_appointments_for_day(phone_number=request.phone_number, date_=request.date, only_active=True)

    return FindAppointmentsResponse(
        appointments=[
            AppointmentSummary(
                appointment_id=a["appointment_id"],
                start_time=a["start_time"],
                name=a["name"],
                reason=a["reason"],
                timezone=a.get("timezone"),
            )
            for a in matches
        ]
    )


@app.post("/cancel_appointment/", response_model=CancelAppointmentResponse, dependencies=[Depends(verify_vapi_secret)])
def cancel_appointment(request: CancelAppointmentRequest):
    """
    Step 2 of cancellation. The agent calls this ONLY after the caller has
    confirmed which specific appointment_id to cancel (from find_appointments).
    """
    appointment = get_appointment_by_id(request.appointment_id)
    if appointment is None or appointment["canceled"]:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    canceled_count = cancel_appointment_by_id(request.appointment_id, request.phone_number, request.cancellation_reason)

    if canceled_count == 0:
        raise HTTPException(status_code=409, detail="Appointment could not be canceled — it may have just been canceled already.")

    cancel_meeting(appointment.get("calendar_event_id"))

    return CancelAppointmentResponse(
        success=True,
        message=f"Appointment on {appointment['start_time'].strftime('%b %d, %Y at %I:%M %p')} has been canceled.",
    )
    # print(f"[cancel_appointment] request={request!r} | type={type(request)}")
    # print(f"[cancel_appointment] request.dict()={request.dict()}")
    # pass

@app.post("/note_complaint_request/", response_model=NoteComplaintResponse, dependencies=[Depends(verify_vapi_secret)])
def note_complaint_request(request: NoteComplaintRequest):
    """
    Logs a complaint or feedback request. No lookup or confirmation step needed beforehand — just record it.
    """
    complaint_id = insert_complaint(name=request.name, phone_number=request.phone_number, issue=request.issue)
 
    return NoteComplaintResponse(
        complaint_id=complaint_id,
        message="Your feedback has been noted. Someone from our team will follow up if needed.",
    )
    # print(f"[note_complaint_request] request={request!r} | type={type(request)}")
    # print(f"[note_complaint_request] request.dict()={request.dict()}")
    # pass

@app.post("/reschedule_appointment/", response_model=AppointmentResponse, dependencies=[Depends(verify_vapi_secret)])
def reschedule_appointment(request: RescheduleAppointmentRequest):
    """
    Rescheduling. The agent calls this ONLY after:
      1. find_appointments was used to get the appointment_id being moved, AND
      2. check_availability confirmed the new time is free.
    """
    appointment = get_appointment_by_id(request.appointment_id)
    if appointment is None or appointment["canceled"]:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    if appointment["phone_number"] != request.phone_number:
        raise HTTPException(
            status_code=404,
            detail="That appointment was not found or has already been canceled.",
        )

    if appointment["start_time"] == request.new_start_date_time:
        return RescheduleAppointmentResponse(
            appointment_id=appointment["appointment_id"],
            start_time=appointment["start_time"],
            message="SUCCESS: The appointment is already scheduled for that time.",
        )

    conflicts = find_conflicting_appointments(
        request.new_start_date_time,
        exclude_appointment_id=request.appointment_id,
    )
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail="That new time is already booked. Please suggest a different time.",
        )

    calendar_updated = update_meeting(appointment.get("calendar_event_id"), request.new_start_date_time, appointment.get("timezone") or "Asia/Kolkata",)
    if not calendar_updated:
        raise HTTPException(
            status_code=500,
            detail="I couldn't reschedule the appointment at the moment.",
        )

    changed_count = reschedule_appointment_by_id(
        appointment_id=request.appointment_id,
        phone_number=request.phone_number,
        new_start_time=request.new_start_date_time,
    )
    if changed_count == 0:
        raise HTTPException(
            status_code=409,
            detail="Appointment could not be rescheduled — it may have just been changed already.",
        )

    return RescheduleAppointmentResponse(
        appointment_id=appointment["appointment_id"],
        start_time=request.new_start_date_time,
        message=(
            f"SUCCESS: Appointment has been successfully rescheduled to "
            f"{request.new_start_date_time.strftime('%B %d, %Y at %I:%M %p')}."
        ),
    )


if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8080, reload=False, workers=1, timeout_keep_alive=300, log_level="info")