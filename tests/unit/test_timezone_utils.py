from zoneinfo import ZoneInfo
import pytest

from src.utils.timezone_utils import (
    DEFAULT_TIMEZONE,
    get_timezone,
)


def test_get_timezone_returns_requested_timezone():
    timezone = get_timezone("America/Los_Angeles")

    assert isinstance(timezone, ZoneInfo)
    assert timezone.key == "America/Los_Angeles"


def test_get_timezone_uses_default_timezone():
    timezone = get_timezone()

    assert timezone.key == DEFAULT_TIMEZONE


def test_get_timezone_raises_for_invalid_timezone():
    with pytest.raises(
        ValueError,
        match="Unrecognized timezone",
    ):
        get_timezone("Invalid/Timezone")