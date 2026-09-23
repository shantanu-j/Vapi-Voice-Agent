from src.integrations.bigquery import insert_complaint
from src.models.complaint import (
    NoteComplaintRequest,
    NoteComplaintResponse,
)


def note_complaint(request: NoteComplaintRequest,) -> NoteComplaintResponse:
    """
    Record a complaint or feedback request.
    """

    complaint_id = insert_complaint(name=request.name, phone_number=request.phone_number, issue=request.issue,)

    return NoteComplaintResponse(
        complaint_id=complaint_id,
        message="Your feedback has been noted. Someone from our team will follow up if needed."
    )