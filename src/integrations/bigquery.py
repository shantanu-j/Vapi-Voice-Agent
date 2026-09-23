import uuid
import datetime as dt
import logging
from google.cloud import bigquery
from config.settings import (
    PROJECT_ID,
    DATASET_ID,
    APPOINTMENTS_TABLE_ID,
    COMPLAINTS_TABLE_ID,
)
from src.core.logging import get_logger

log = get_logger("statai.bigquery")

client = bigquery.Client(project=PROJECT_ID)

APPOINTMENTS_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{APPOINTMENTS_TABLE_ID}"
COMPLAINTS_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{COMPLAINTS_TABLE_ID}"
APPOINTMENT_DURATION_MINUTES = 30


def _run_query(query: str, job_config: bigquery.QueryJobConfig, label: str,):
    """Execute a BigQuery query and log elapsed time."""

    start = dt.datetime.now()
    result = client.query(query, job_config=job_config,).result()

    elapsed_ms = (dt.datetime.now() - start).total_seconds() * 1000
    log.info("BQ query [%s] | elapsed_ms=%.0f", label, elapsed_ms,)

    return result


def insert_complaint(name: str, phone_number: str, issue: str,) -> str:
    complaint_id = str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc)

    query = f"""
        INSERT INTO `{COMPLAINTS_TABLE_REF}`
        (complaint_id, name, phone_number, issue, created_at)
        VALUES (@complaint_id, @name, @phone_number, @issue, @created_at)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("complaint_id", "STRING", complaint_id),
            bigquery.ScalarQueryParameter("name", "STRING", name),
            bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number),
            bigquery.ScalarQueryParameter("issue", "STRING", issue),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", now),
        ]
    )

    _run_query(query,job_config,"insert_complaint",)

    return complaint_id


def insert_appointment(email_id: str, phone_number: str, name: str, reason: str, start_time: dt.datetime, calendar_event_id: str, timezone: str, meet_link: str | None = None,) -> str:
    appointment_id = str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc)

    query = f"""
        INSERT INTO `{APPOINTMENTS_TABLE_REF}`
        (appointment_id, email_id, phone_number, name, reason, start_time, canceled, calendar_event_id, meet_link, timezone, created_at)
        VALUES (@appointment_id, @email_id, @phone_number, @name, @reason, @start_time, FALSE, @calendar_event_id, @meet_link, @timezone, @created_at)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("appointment_id", "STRING", appointment_id),
            bigquery.ScalarQueryParameter("email_id", "STRING", email_id),
            bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number),
            bigquery.ScalarQueryParameter("name", "STRING", name),
            bigquery.ScalarQueryParameter("reason", "STRING", reason),
            bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time),
            bigquery.ScalarQueryParameter("calendar_event_id", "STRING", calendar_event_id),
            bigquery.ScalarQueryParameter("meet_link", "STRING", meet_link),
            bigquery.ScalarQueryParameter("timezone", "STRING", timezone),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", now),
        ]
    )

    _run_query(query,job_config,"insert_appointment",)

    return appointment_id


def find_existing_appointment(phone_number: str, start_time: dt.datetime,) -> dict | None:
    """
    Finds an active appointment for the same phone number
    and start time.
    Used to make schedule_appointment idempotent.
    """

    query = f"""
        SELECT appointment_id, email_id, phone_number, name, reason, start_time, canceled, cancellation_reason, calendar_event_id, meet_link, timezone, created_at
        FROM `{APPOINTMENTS_TABLE_REF}`
        WHERE phone_number = @phone_number
          AND start_time = @start_time
          AND canceled = FALSE
        ORDER BY created_at DESC
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number,),
            bigquery.ScalarQueryParameter("start_time","TIMESTAMP",start_time,),
        ]
    )

    rows = [dict(row) for row in _run_query(query, job_config, "find_existing_appointment",)]

    return rows[0] if rows else None


def find_appointments_for_day(phone_number: str, date_: dt.date | None = None, only_active: bool = True,) -> list[dict]:
    """
    Finds appointments for a phone number.
    If date_ is provided, a one-day buffer is used on
    both sides to absorb timezone drift.
    If date_ is None, all matching appointments are returned.
    """

    conditions = ["phone_number = @phone_number"]

    params = [
        bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number,)
    ]

    if date_ is not None:
        start_dt = dt.datetime.combine(date_ - dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
        end_dt = dt.datetime.combine(date_ + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
        conditions.append("start_time >= @start_dt")
        conditions.append("start_time < @end_dt")
        params.append(bigquery.ScalarQueryParameter("start_dt", "TIMESTAMP", start_dt))
        params.append(bigquery.ScalarQueryParameter("end_dt", "TIMESTAMP", end_dt))

    if only_active:
        conditions.append("canceled = FALSE")

    query = f"""
        SELECT appointment_id, email_id, phone_number, name, reason, start_time, canceled, calendar_event_id, meet_link, timezone, created_at
        FROM `{APPOINTMENTS_TABLE_REF}`
        WHERE {' AND '.join(conditions)}
        ORDER BY start_time ASC
        LIMIT 20
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)

    return [dict(row) for row in _run_query(query, job_config, "find_appointments_for_day",)]


def find_appointments_between(start_dt_utc: dt.datetime, end_dt_utc: dt.datetime,) -> list[dict]:
    """
    Returns active appointments whose start_time falls
    within [start_dt_utc, end_dt_utc).
    """

    query = f"""
        SELECT appointment_id, start_time
        FROM `{APPOINTMENTS_TABLE_REF}`
        WHERE canceled = FALSE
          AND start_time >= @start_dt
          AND start_time < @end_dt
        ORDER BY start_time ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_dt", "TIMESTAMP", start_dt_utc),
            bigquery.ScalarQueryParameter("end_dt", "TIMESTAMP", end_dt_utc),
        ]
    )

    return [dict(row) for row in _run_query(query, job_config, "find_appointments_between",)]


def get_appointment_by_id(appointment_id: str,) -> dict | None:

    query = f"""
        SELECT appointment_id,email_id,phone_number,name,reason,start_time,canceled,cancellation_reason,calendar_event_id,meet_link,timezone,created_at
        FROM `{APPOINTMENTS_TABLE_REF}`
        WHERE appointment_id = @appointment_id
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("appointment_id", "STRING", appointment_id)]
    )

    rows = [dict(row) for row in _run_query(query,job_config,"get_appointment_by_id",)]

    return rows[0] if rows else None


def cancel_appointment_by_id(appointment_id: str, phone_number: str, cancellation_reason: str | None = None,) -> int:
    """
    Cancels exactly one appointment by its ID.
    Returns 1 if canceled,
    0 if not found or already canceled.
    """
    query = f"""
        UPDATE `{APPOINTMENTS_TABLE_REF}`
        SET canceled = TRUE, cancellation_reason = @cancellation_reason
        WHERE appointment_id = @appointment_id AND phone_number = @phone_number AND canceled = FALSE
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("appointment_id", "STRING", appointment_id),
            bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number),
            bigquery.ScalarQueryParameter("cancellation_reason", "STRING", cancellation_reason),
        ]
    )

    result = _run_query(query, job_config, "cancel_appointment_by_id",)

    return result.num_dml_affected_rows or 0


def find_conflicting_appointments(start_time: dt.datetime, duration_minutes: int = APPOINTMENT_DURATION_MINUTES, exclude_appointment_id: str | None = None,) -> list[dict]:
    """
    Returns active appointments that overlap
    the requested appointment window.
    """

    end_time = start_time + dt.timedelta(
        minutes=duration_minutes
    )


    conditions = [
        "canceled = FALSE",
        "start_time < @requested_end",
        "TIMESTAMP_ADD(start_time, INTERVAL @duration_minutes MINUTE) > @requested_start",
    ]

    params = [
        bigquery.ScalarQueryParameter("requested_start", "TIMESTAMP", start_time),
        bigquery.ScalarQueryParameter("requested_end", "TIMESTAMP", end_time),
        bigquery.ScalarQueryParameter("duration_minutes", "INT64", duration_minutes),
    ]

    if exclude_appointment_id:
        conditions.append("appointment_id != @exclude_appointment_id")
        params.append(bigquery.ScalarQueryParameter("exclude_appointment_id","STRING", exclude_appointment_id,))

    query = f"""
        SELECT appointment_id,name,start_time
        FROM `{APPOINTMENTS_TABLE_REF}`
        WHERE {' AND '.join(conditions)}
    """

    job_config = bigquery.QueryJobConfig(query_parameters=params)

    return [dict(row) for row in _run_query(query,job_config,"find_conflicting_appointments",)]


def reschedule_appointment_by_id(appointment_id: str, phone_number: str, new_start_time: dt.datetime,) -> int:
    """
    Moves an active appointment to a new start time.
    Keeps the same appointment_id, calendar_event_id,
    and meet_link.
    Returns 1 if updated, otherwise 0.
    """

    query = f"""
        UPDATE `{APPOINTMENTS_TABLE_REF}`
        SET start_time = @new_start_time
        WHERE appointment_id = @appointment_id
          AND phone_number = @phone_number
          AND canceled = FALSE
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("appointment_id", "STRING", appointment_id),
            bigquery.ScalarQueryParameter("phone_number", "STRING", phone_number),
            bigquery.ScalarQueryParameter("new_start_time", "TIMESTAMP", new_start_time),
        ]
    )

    result = _run_query(query, job_config, "reschedule_appointment_by_id",)

    return result.num_dml_affected_rows or 0