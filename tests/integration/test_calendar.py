from src.integrations.google_calendar import (
    _get_calendar_service,
)


def test_calendar_service_authentication():
    service = _get_calendar_service()

    assert service is not None