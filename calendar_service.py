import datetime as dt
import google.auth
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from settings import TARGET_SERVICE_ACCOUNT, DELEGATED_USER

from logging_config import get_logger
log = get_logger("statai.calendar")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


def _get_calendar_service():
    base_credentials, _ = google.auth.default()

    delegated_credentials = ImpersonatedCredentials(
        source_credentials=base_credentials,
        target_principal=TARGET_SERVICE_ACCOUNT,
        target_scopes=SCOPES,
        lifetime=3600,
        subject=DELEGATED_USER,
    )

    return build("calendar", "v3", credentials=delegated_credentials)


def create_meeting(
    email_id: str,
    phone_number: str,
    name: str,
    reason: str,
    start_time: dt.datetime,
    timezone: str,
    duration_minutes: int = 30,
) -> tuple[str | None, str | None]:
    """
    Creates the event on DELEGATED_USER's calendar.
    """
    try:
        service = _get_calendar_service()
        end_time = start_time + dt.timedelta(minutes=duration_minutes)

        event_body = {
            "summary": f"Appointment - {name}" if name else "Appointment",
            "description": (
                f"Reason: {reason or 'Scheduled via StatAI voice agent'}\n"
                f"Phone Number: {phone_number}"
            ),
            "start": {"dateTime": start_time.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": timezone},
            "attendees": [{"email": email_id}],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"statai-{int(start_time.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute()

        meet_link = event.get("hangoutLink")
        return event["id"], meet_link

    except HttpError as e:
        log.warning("Calendar API error during event creation: %s", e)
        return None, None
    except Exception as e:
        log.warning("Unexpected error during calendar event creation: %s", e)
        return None, None

def cancel_meeting(event_id: str | None) -> None:
    """
    Deletes the event from DELEGATED_USER's calendar.
    """
    if not event_id:
        return
    try:
        service = _get_calendar_service()
        service.events().delete(
            calendarId="primary",
            eventId=event_id,
            sendUpdates="all",
        ).execute()
    except HttpError as e:
        log.warning("Could not cancel calendar event %s: %s", event_id, e)
    except Exception as e:
        log.warning("Unexpected error cancelling calendar event %s: %s", event_id, e)

def update_meeting(
    event_id: str | None,
    start_time: dt.datetime,
    timezone: str,
    duration_minutes: int = 30,
) -> bool:
    """
    Patches the existing event's start/end time in place — same event ID, same
    Meet link, same attendee. Returns True on success, False on failure.
    """
    if not event_id:
        return False
    try:
        service = _get_calendar_service()
        end_time = start_time + dt.timedelta(minutes=duration_minutes)

        event_body = {
            "start": {"dateTime": start_time.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": timezone},
        }

        service.events().patch(
            calendarId="primary",
            eventId=event_id,
            body=event_body,
            sendUpdates="all",
        ).execute()
        return True

    except HttpError as e:
        log.warning("Calendar API error during event reschedule: %s", e)
        return False
    except Exception as e:
        log.warning("Unexpected error during calendar event reschedule: %s", e)
        return False