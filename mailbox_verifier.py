import quickemailverification
from settings import QUICKEMAILVERIFICATION_API_KEY


def _as_bool(value):
    """Convert QuickEmailVerification boolean-like values to bool/None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _get_body(response) -> dict:
    """Read response.body returned by the QuickEmailVerification SDK."""
    body = getattr(response, "body", response)

    if isinstance(body, dict):
        return body

    try:
        return dict(body)
    except (TypeError, ValueError):
        return {}


def _reason_message(result: str, reason: str | None, message: str) -> str:
    """Return a short, voice-agent-safe verification explanation."""
    if result == "valid":
        return "Email passed mailbox verification."

    if reason == "rejected_email":
        return "The recipient mail server rejected the email address."

    if reason == "invalid_email":
        return "The email address failed mailbox verification."

    if reason == "invalid_domain":
        return "The email domain could not be verified."

    if reason in {
        "no_connect",
        "timeout",
        "unavailable_smtp",
        "temporarily_blocked",
    }:
        return "The email address could not be confidently verified."

    if message:
        return str(message)

    return reason or "The email address could not be confidently verified."


def _unknown_result(reason: str, message: str):
    """Return a consistent unknown result."""
    return {
        "result": "unknown",
        "reason": reason,
        "reason_message": message,
        "did_you_mean": None,
        "safe_to_send": None,
        "disposable": None,
        "accept_all": None,
        "role": None,
        "free": None,
    }


def verify_mailbox(email: str) -> dict:
    """Verify one email using QuickEmailVerification."""
    if not QUICKEMAILVERIFICATION_API_KEY:
        return _unknown_result(
            "missing_api_key",
            "The email verification service is not configured.",
        )

    try:
        client = quickemailverification.Client(
            QUICKEMAILVERIFICATION_API_KEY
        )
        service = client.quickemailverification()
        response = service.verify(email)
        body = _get_body(response)

        result = str(body.get("result", "unknown")).strip().lower()

        if result not in {"valid", "invalid", "unknown"}:
            result = "unknown"

        qev_reason = body.get("reason") or None
        message = body.get("message") or ""

        return {
            "result": result,
            "reason": qev_reason,
            "reason_message": _reason_message(
                result,
                qev_reason,
                message,
            ),
            "did_you_mean": body.get("did_you_mean") or None,
            "safe_to_send": _as_bool(body.get("safe_to_send")),
            "disposable": _as_bool(body.get("disposable")),
            "accept_all": _as_bool(body.get("accept_all")),
            "role": _as_bool(body.get("role")),
            "free": _as_bool(body.get("free")),
        }

    except Exception:
        return _unknown_result(
            "verification_service_error",
            "The email address could not be verified because the verification service was unavailable.",
        )
