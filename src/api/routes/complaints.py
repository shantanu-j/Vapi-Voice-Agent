from fastapi import APIRouter, Depends
from src.api.dependencies import verify_vapi_secret
from src.models.complaint import (
    NoteComplaintRequest,
    NoteComplaintResponse,
)
from src.services.complaint_service import note_complaint


router = APIRouter()


@router.post(
    "/note_complaint_request/",
    response_model=NoteComplaintResponse,
    dependencies=[Depends(verify_vapi_secret)],
)
def note_complaint_request_route(request: NoteComplaintRequest):
    return note_complaint(request)