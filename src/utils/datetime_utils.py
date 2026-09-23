import datetime as dt
from zoneinfo import ZoneInfo


def start_of_day(date_: dt.date, timezone: ZoneInfo,) -> dt.datetime:
    """
    Return the start of a day in the given timezone.
    """

    return dt.datetime.combine(
        date_,
        dt.time.min,
        tzinfo=timezone,
    )


def end_of_day(date_: dt.date, timezone: ZoneInfo,) -> dt.datetime:
    """
    Return the start of the next day in the given timezone.
    """

    return start_of_day(
        date_,
        timezone,
    ) + dt.timedelta(days=1)


def to_utc(value: dt.datetime,) -> dt.datetime:
    """
    Convert an aware datetime to UTC.
    """

    if value.tzinfo is None:
        raise ValueError(
            "Datetime must be timezone-aware."
        )

    return value.astimezone(dt.timezone.utc)


def format_time(value: dt.datetime, timezone: ZoneInfo,) -> str:
    """
    Format a datetime as a local time such as: 10:30 AM
    """

    return (
        value
        .astimezone(timezone)
        .strftime("%I:%M %p")
        .lstrip("0")
    )