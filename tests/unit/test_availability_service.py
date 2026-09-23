import datetime as dt
from src.models.availability import CheckAvailabilityRequest, AvailableSlotsRequest
from src.services.availability_service import check_availability, available_slots


def test_check_availability_when_slot_is_free(monkeypatch):
    monkeypatch.setattr(
        "src.services.availability_service.find_conflicting_appointments",
        lambda start_time: [],
    )

    request = CheckAvailabilityRequest(
        start_date_time=dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,)
    )

    response = check_availability(request)

    assert response.available is True
    assert response.message == "That time is available."


def test_check_availability_when_slot_is_booked(monkeypatch):
    monkeypatch.setattr(
        "src.services.availability_service.find_conflicting_appointments",
        lambda start_time: [{"appointment_id": "123", "start_time": start_time,}],)

    request = CheckAvailabilityRequest(start_date_time=dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,))

    response = check_availability(request)

    assert response.available is False
    assert "already booked" in response.message


def test_available_slots_when_no_appointments(monkeypatch):
    monkeypatch.setattr(
        "src.services.availability_service.find_appointments_between",
        lambda start_dt, end_dt: [],
    )

    request = AvailableSlotsRequest(date=dt.date(2026, 9, 15), timezone="America/Los_Angeles",)

    response = available_slots(request)

    assert response.has_availability is True
    assert response.timezone == "America/Los_Angeles"
    assert response.first_slot_display == "12:00 AM"
    assert len(response.slots_display) == 1


def test_available_slots_excludes_booked_period(monkeypatch):
    monkeypatch.setattr(
        "src.services.availability_service.find_appointments_between",
        lambda start_dt, end_dt: [{"appointment_id": "123", "start_time": dt.datetime(2026, 9, 15, 10, 0, tzinfo=dt.timezone.utc,),}],
    )

    request = AvailableSlotsRequest(
        date=dt.date(2026, 9, 15),
        timezone="UTC",
    )

    response = available_slots(request)

    assert response.has_availability is True
    assert len(response.slots_display) == 2
    assert response.slots_display[0] == "12:00 AM to 10:00 AM"
    assert response.slots_display[1] == "10:30 AM to 12:00 AM"