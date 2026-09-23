from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "America/Los_Angeles"

def get_timezone(timezone_name: str | None = None,) -> ZoneInfo:
    """
    Return a timezone from an IANA timezone name.
    Defaults to America/Los_Angeles.
    """

    timezone_name = timezone_name or DEFAULT_TIMEZONE

    try:
        return ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(
            f"Unrecognized timezone: {timezone_name}"
        ) from exc