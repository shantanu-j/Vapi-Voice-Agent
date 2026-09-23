import datetime as dt
import pytest
from fastapi import HTTPException
from src.models.appointment import (
    AppointmentRequest,
    CancelAppointmentRequest,
    FindAppointmentsRequest,
    RescheduleAppointmentRequest,
)
from src.services.appointment_service import (
    schedule_appointment,
    find_appointments,
    cancel_appointment,
    reschedule_appointment,
)


def test_schedule_appointment_creates_new_appointment(monkeypatch):
    monkeypatch.setattr(
        "src.services.appointment_service.find_existing_appointment",
        lambda phone_number, start_time: None,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.create_meeting",
        lambda **kwargs: ("event-123", "https://meet.google.com/test"),
    )

    monkeypatch.setattr(
        "src.services.appointment_service.insert_appointment",
        lambda **kwargs: "appointment-123",
    )

    start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)

    request = AppointmentRequest(
        name="John Doe",
        reason="Consultation",
        phone_number="1234567890",
        start_date_time=start_time,
        timezone="America/Los_Angeles",
    )

    response = schedule_appointment(request)

    assert response.appointment_id == "appointment-123"
    assert response.phone_number == "1234567890"
    assert response.name == "John Doe"
    assert response.reason == "Consultation"
    assert response.start_time == start_time
    assert response.canceled is False
    assert response.meet_link == "https://meet.google.com/test"
    assert response.timezone == "America/Los_Angeles"


def test_schedule_appointment_returns_existing_appointment(
    monkeypatch,
):
    start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)

    existing_appointment = {
        "appointment_id": "appointment-123",
        "email_id": "test@example.com",
        "phone_number": "1234567890",
        "name": "John Doe",
        "reason": "Consultation",
        "start_time": start_time,
        "canceled": False,
        "meet_link": "https://meet.google.com/test",
        "timezone": "America/Los_Angeles",
    }

    monkeypatch.setattr(
        "src.services.appointment_service.find_existing_appointment",
        lambda phone_number, start_time: existing_appointment,
    )

    def fail_create_meeting(**kwargs):
        pytest.fail("create_meeting should not be called for an existing appointment")

    monkeypatch.setattr(
        "src.services.appointment_service.create_meeting",
        fail_create_meeting,
    )

    request = AppointmentRequest(
        name="John Doe",
        reason="Consultation",
        phone_number="1234567890",
        start_date_time=start_time,
        timezone="America/Los_Angeles",
    )

    response = schedule_appointment(request)

    assert response.appointment_id == "appointment-123"
    assert response.email_id == "test@example.com"
    assert response.phone_number == "1234567890"
    assert response.name == "John Doe"
    assert response.reason == "Consultation"
    assert response.start_time == start_time
    assert response.canceled is False
    assert response.meet_link == "https://meet.google.com/test"
    assert response.timezone == "America/Los_Angeles"


def test_schedule_appointment_raises_when_calendar_creation_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.services.appointment_service.find_existing_appointment",
        lambda phone_number, start_time: None,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.create_meeting",
        lambda **kwargs: (None, None),
    )

    request = AppointmentRequest(
        name="John Doe",
        reason="Consultation",
        phone_number="1234567890",
        start_date_time=dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,),
        timezone="America/Los_Angeles",
    )

    with pytest.raises(
        HTTPException,
        match="couldn't complete the appointment booking",
    ) as exc_info:
        schedule_appointment(request)

    assert exc_info.value.status_code == 500


def test_find_appointments(monkeypatch):
    start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)

    monkeypatch.setattr(
        "src.services.appointment_service.find_appointments_for_day",
        lambda phone_number, date_, only_active: [
            {
                "appointment_id": "appointment-123",
                "start_time": start_time,
                "name": "John Doe",
                "reason": "Consultation",
                "timezone": "America/Los_Angeles",
            }
        ],
    )

    request = FindAppointmentsRequest(
        phone_number="1234567890",
        date=dt.date(2026, 9, 15),
    )

    response = find_appointments(request)

    assert len(response.appointments) == 1
    assert response.appointments[0].appointment_id == "appointment-123"
    assert response.appointments[0].start_time == start_time
    assert response.appointments[0].name == "John Doe"
    assert response.appointments[0].reason == "Consultation"
    assert response.appointments[0].timezone == "America/Los_Angeles"


def test_find_appointments_returns_empty_list(monkeypatch):
    monkeypatch.setattr(
        "src.services.appointment_service.find_appointments_for_day",
        lambda phone_number, date_, only_active: [],
    )

    request = FindAppointmentsRequest(
        phone_number="1234567890",
        date=dt.date(2026, 9, 15),
    )

    response = find_appointments(request)

    assert response.appointments == []


def test_cancel_appointment(monkeypatch):
    start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)

    appointment = {
        "appointment_id": "appointment-123",
        "phone_number": "1234567890",
        "name": "John Doe",
        "start_time": start_time,
        "canceled": False,
        "calendar_event_id": "event-123",
    }

    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: appointment,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.cancel_appointment_by_id",
        lambda **kwargs: 1,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.cancel_meeting",
        lambda event_id: None,
    )

    request = CancelAppointmentRequest(
        appointment_id="appointment-123",
        name="John Doe",
        phone_number="1234567890",
        cancellation_reason="No longer needed",
    )

    response = cancel_appointment(request)

    assert response.success is True
    assert "has been canceled" in response.message


def test_cancel_appointment_when_not_found(monkeypatch):
    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: None,
    )

    request = CancelAppointmentRequest(
        appointment_id="appointment-123",
        name="John Doe",
        phone_number="1234567890",
        cancellation_reason="No longer needed",
    )

    with pytest.raises(HTTPException) as exc_info:
        cancel_appointment(request)

    assert exc_info.value.status_code == 404


def test_cancel_appointment_when_already_canceled(monkeypatch):
    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: {
            "appointment_id": "appointment-123",
            "canceled": True,
        },
    )

    request = CancelAppointmentRequest(
        appointment_id="appointment-123",
        name="John Doe",
        phone_number="1234567890",
        cancellation_reason="No longer needed",
    )

    with pytest.raises(HTTPException) as exc_info:
        cancel_appointment(request)

    assert exc_info.value.status_code == 404


def test_reschedule_appointment(monkeypatch):
    old_start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)
    new_start_time = dt.datetime(2026, 9, 16, 11, 0, tzinfo=dt.timezone.utc,)

    appointment = {
        "appointment_id": "appointment-123",
        "phone_number": "1234567890",
        "start_time": old_start_time,
        "canceled": False,
        "calendar_event_id": "event-123",
        "timezone": "America/Los_Angeles",
    }

    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: appointment,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.find_conflicting_appointments",
        lambda *args, **kwargs: [],
    )

    monkeypatch.setattr(
        "src.services.appointment_service.update_meeting",
        lambda **kwargs: True,
    )

    monkeypatch.setattr(
        "src.services.appointment_service.reschedule_appointment_by_id",
        lambda **kwargs: 1,
    )

    request = RescheduleAppointmentRequest(
        appointment_id="appointment-123",
        phone_number="1234567890",
        new_start_date_time=new_start_time,
    )

    response = reschedule_appointment(request)

    assert response.appointment_id == "appointment-123"
    assert response.start_time == new_start_time
    assert response.message == (
        "Your appointment has been rescheduled successfully."
    )


def test_reschedule_appointment_when_not_found(monkeypatch):
    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: None,
    )

    request = RescheduleAppointmentRequest(
        appointment_id="appointment-123",
        phone_number="1234567890",
        new_start_date_time=dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,),
    )

    with pytest.raises(HTTPException) as exc_info:
        reschedule_appointment(request)

    assert exc_info.value.status_code == 404


def test_reschedule_appointment_when_phone_number_does_not_match(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: {
            "appointment_id": "appointment-123",
            "phone_number": "9999999999",
            "start_time": dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,),
            "canceled": False,
        },
    )

    request = RescheduleAppointmentRequest(
        appointment_id="appointment-123",
        phone_number="1234567890",
        new_start_date_time=dt.datetime(2026, 9, 16, 11, 0, tzinfo=dt.timezone.utc,),
    )

    with pytest.raises(HTTPException) as exc_info:
        reschedule_appointment(request)

    assert exc_info.value.status_code == 404


def test_reschedule_appointment_when_new_time_is_already_booked(
    monkeypatch,
):
    old_start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)
    new_start_time = dt.datetime(2026, 9, 16, 11, 0, tzinfo=dt.timezone.utc,)

    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: {
            "appointment_id": "appointment-123",
            "phone_number": "1234567890",
            "start_time": old_start_time,
            "canceled": False,
        },
    )

    monkeypatch.setattr(
        "src.services.appointment_service.find_conflicting_appointments",
        lambda *args, **kwargs: [
            {
                "appointment_id": "appointment-456",
                "name": "Jane Doe",
                "start_time": new_start_time,
            }
        ],
    )

    request = RescheduleAppointmentRequest(
        appointment_id="appointment-123",
        phone_number="1234567890",
        new_start_date_time=new_start_time,
    )

    with pytest.raises(HTTPException) as exc_info:
        reschedule_appointment(request)

    assert exc_info.value.status_code == 409


def test_reschedule_appointment_when_same_time(monkeypatch):
    start_time = dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)

    monkeypatch.setattr(
        "src.services.appointment_service.get_appointment_by_id",
        lambda appointment_id: {
            "appointment_id": "appointment-123",
            "phone_number": "1234567890",
            "start_time": start_time,
            "canceled": False,
        },
    )

    request = RescheduleAppointmentRequest(
        appointment_id="appointment-123",
        phone_number="1234567890",
        new_start_date_time=start_time,
    )

    response = reschedule_appointment(request)

    assert response.appointment_id == "appointment-123"
    assert response.start_time == start_time
    assert response.message == (
        "Your appointment is already scheduled for that time."
    )