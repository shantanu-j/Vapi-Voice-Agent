from pydantic import BaseModel

class NoteComplaintRequest(BaseModel):
    name: str
    phone_number: str
    issue: str


class NoteComplaintResponse(BaseModel):
    complaint_id: str
    message: str