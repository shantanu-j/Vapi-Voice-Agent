import datetime as dt

from src.integrations.bigquery import (
    find_appointments_between,
    find_appointments_for_day,
)


def test_find_appointments_between():
    start_dt = dt.datetime(
        2026,
        9,
        1,
        0,
        0,
        tzinfo=dt.timezone.utc,
    )

    end_dt = dt.datetime(
        2026,
        10,
        1,
        0,
        0,
        tzinfo=dt.timezone.utc,
    )

    appointments = find_appointments_between(
        start_dt,
        end_dt,
    )

    assert isinstance(appointments, list)

    for appointment in appointments:
        assert "appointment_id" in appointment
        assert "start_time" in appointment


def test_find_appointments_for_day():
    appointments = find_appointments_for_day(
        phone_number="0000000000",
        date_=dt.date(2026, 9, 15),
        only_active=True,
    )

    assert isinstance(appointments, list)

    for appointment in appointments:
        assert "appointment_id" in appointment
        assert "phone_number" in appointment
        assert "start_time" in appointment