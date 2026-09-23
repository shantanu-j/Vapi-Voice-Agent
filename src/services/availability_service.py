import datetime as dt
from src.integrations.bigquery import (
    find_conflicting_appointments,
    find_appointments_between,
    APPOINTMENT_DURATION_MINUTES,
)

from src.models.availability import (
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    AvailableSlotsRequest,
    AvailableSlotsResponse,
)

from src.utils.datetime_utils import (
    start_of_day,
    end_of_day,
    to_utc,
    format_time,
)

from src.utils.timezone_utils import get_timezone


DEFAULT_TIMEZONE = "America/Los_Angeles"


def check_availability(request: CheckAvailabilityRequest,) -> CheckAvailabilityResponse:
    """
    Check whether an appointment can be scheduled
    at the requested start time.
    """

    conflicts = find_conflicting_appointments(request.start_date_time)

    if conflicts:
        return CheckAvailabilityResponse(
            available=False,
            message="That time is already booked. Please suggest a different time."
        )

    return CheckAvailabilityResponse(
        available=True,
        message="That time is available.",
    )


def available_slots(request: AvailableSlotsRequest,) -> AvailableSlotsResponse:
    """
    Return free windows for the requested date and timezone.
    Note: The full calendar day is considered
    """

    timezone_name = request.timezone or DEFAULT_TIMEZONE

    try:
        timezone = get_timezone(timezone_name)
    except ValueError:
        raise ValueError(
            "Unrecognized timezone."
        )

    day_start_local = start_of_day(request.date, timezone)
    day_end_local = end_of_day(request.date, timezone)

    window_start = to_utc(day_start_local)
    window_end = to_utc(day_end_local)

    booked = sorted(
        find_appointments_between(
            window_start,
            window_end,
        ),
        key=lambda appointment: appointment["start_time"],
    )

    booked = sorted(find_appointments_between(window_start, window_end), key=lambda appointment: appointment["start_time"])

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

    # def format_time(value: dt.datetime,) -> str:
    #     return (
    #         value
    #         .astimezone(timezone)
    #         .strftime("%I:%M %p")
    #         .lstrip("0")
    #     )

    slots_display = [
        (
            f"{format_time(start, timezone)} "
            f"to "
            f"{format_time(end, timezone)}"
        )
        for start, end in free_windows
    ]


    if not free_windows:
        message = "No availability on that date."
    elif len(free_windows) == 1:
        message = (
            f"Available from {slots_display[0]}"
        )
    else:
        message = "Multiple free windows available"

    return AvailableSlotsResponse(
        date=request.date,
        timezone=timezone_name,
        has_availability=bool(free_windows),
        first_slot_display=(
            format_time(free_windows[0][0], timezone,)
            if free_windows else None
        ),
        slots_display=slots_display,
        message=message,
    )