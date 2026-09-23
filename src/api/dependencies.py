from fastapi import Header, HTTPException
from config.settings import VAPI_SERVER_SECRET


def verify_vapi_secret(
    x_webhook_secret: str | None = Header(default=None),
):
    if x_webhook_secret != VAPI_SERVER_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )