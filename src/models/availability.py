import datetime as dt
from pydantic import BaseModel


class CheckAvailabilityRequest(BaseModel):
    start_date_time: dt.datetime


class CheckAvailabilityResponse(BaseModel):
    available: bool
    message: str


class AvailableSlotsRequest(BaseModel):
    date: dt.datetime
    timezone: str | None = None


class AvailableSlotsResponse(BaseModel):
    date: dt.datetime
    timezone: str
    has_availability: bool
    first_slot_display: str | None = None
    slots_display: list[str]
    message: str