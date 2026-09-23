import datetime as dt
from pydantic import BaseModel

class AppointmentRequest(BaseModel):
    name: str
    reason: str
    phone_number: str
    start_date_time: dt.datetime
    timezone: str


class AppointmentResponse(BaseModel):
    appointment_id: str
    email_id: str
    phone_number: str
    name: str
    reason: str
    start_time: dt.datetime
    canceled: bool
    meet_link: str | None = None
    timezone: str | None = None


class FindAppointmentsRequest(BaseModel):
    phone_number: str
    date: dt.date | None = None

class AppointmentSummary(BaseModel):
    appointment_id: str
    start_time: dt.datetime
    name: str
    reason: str
    timezone: str | None = None


class FindAppointmentsResponse(BaseModel):
    appointments: list[AppointmentSummary]


class CancelAppointmentRequest(BaseModel):
    appointment_id: str
    name: str
    phone_number: str
    cancellation_reason: str


class CancelAppointmentResponse(BaseModel):
    success: bool
    message: str


class RescheduleAppointmentRequest(BaseModel):
    appointment_id: str
    phone_number: str
    new_start_date_time: dt.datetime


class RescheduleAppointmentResponse(BaseModel):
    appointment_id: str
    start_time: dt.datetime
    message: str