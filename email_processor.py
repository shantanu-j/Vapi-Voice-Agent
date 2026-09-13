from email_validator import EmailNotValidError, validate_email
from mailbox_verifier import verify_mailbox


def validate_email_address(email: str) -> dict:
    """Validate the email value supplied by Vapi."""
    try:
        result = validate_email(
            email.strip(),
            check_deliverability=False,
        )
        return {
            "valid": True,
            "normalized": result.normalized,
            "reason": None,
        }
    except EmailNotValidError as exc:
        return {
            "valid": False,
            "normalized": None,
            "reason": str(exc),
        }


def determine_problem_area(email: str) -> str:
    """Identify the likely section needing correction."""
    if "@" not in email or email.count("@") != 1:
        return "entire_email"

    local, domain = email.split("@", 1)

    if not local:
        return "local_part"
    if not domain:
        return "domain"

    return "unknown"


def create_natural_readback(email: str) -> str:
    """Create speech-friendly wording for confirmation."""
    return (
        email.replace("@", " at ")
        .replace(".", " dot ")
        .replace("_", " underscore ")
        .replace("-", " hyphen ")
        .replace("+", " plus ")
    )


def create_spelling(text: str) -> str:
    """Create character-by-character spelling when explicitly needed."""
    result = []

    for char in text:
        if char == "@":
            result.append("at the rate")
        elif char == ".":
            result.append("dot")
        elif char == "_":
            result.append("underscore")
        elif char == "-":
            result.append("hyphen")
        elif char == "+":
            result.append("plus")
        else:
            result.append(char.upper())

    return " ".join(result)


def _base_result_fields(verification: dict) -> dict:
    return {
        "verification_result": verification.get("result"),
        "verification_reason": verification.get("reason"),
        "did_you_mean": verification.get("did_you_mean"),
        "safe_to_send": verification.get("safe_to_send"),
        "disposable": verification.get("disposable"),
        "accept_all": verification.get("accept_all"),
        "role": verification.get("role"),
        "free": verification.get("free"),
    }


def _build_result(
    *,
    status: str,
    original_email: str,
    normalized_email: str | None,
    mailbox_verified: bool,
    confirmation_required: bool,
    clarification_required: bool,
    problem_area: str | None,
    natural_readback: str | None,
    spelling: str | None,
    verification: dict | None,
    reason: str,
) -> dict:
    """Build a consistent response for the Vapi tool."""
    qev_fields = _base_result_fields(verification or {})

    return {
        "status": status,
        "original_email": original_email,
        "normalized_email": normalized_email,
        "mailbox_verified": mailbox_verified,
        "confirmation_required": confirmation_required,
        "clarification_required": clarification_required,
        "problem_area": problem_area,
        "natural_readback": natural_readback,
        "spelling": spelling,
        **qev_fields,
        "reason": reason,
    }


def process_email(email: str) -> dict:
    """
    Status meanings:
    - valid: syntax and mailbox verification passed.
    - invalid: syntax validation failed.
    - mailbox_unverified: syntax passed.
    - unknown: verification service could not determine the mailbox status.
    """
    if not email or not email.strip():
        return _build_result(
            status="invalid",
            original_email=email,
            normalized_email=None,
            mailbox_verified=False,
            confirmation_required=False,
            clarification_required=True,
            problem_area="entire_email",
            natural_readback=None,
            spelling=None,
            verification=None,
            reason="No email address was provided.",
        )

    email = email.strip()
    validation = validate_email_address(email)

    if not validation["valid"]:
        return _build_result(
            status="invalid",
            original_email=email,
            normalized_email=None,
            mailbox_verified=False,
            confirmation_required=False,
            clarification_required=True,
            problem_area=determine_problem_area(email),
            natural_readback=None,
            spelling=None,
            verification=None,
            reason=validation["reason"],
        )

    final_email = validation["normalized"]
    verification = verify_mailbox(final_email)
    result = verification.get("result", "unknown")

    readback = create_natural_readback(final_email)
    spelling = create_spelling(final_email)

    if result == "valid":
        return _build_result(
            status="valid",
            original_email=email,
            normalized_email=final_email,
            mailbox_verified=True,
            confirmation_required=True,
            clarification_required=False,
            problem_area=None,
            natural_readback=readback,
            spelling=spelling,
            verification=verification,
            reason="Email passed syntax validation and mailbox verification.",
        )

    if result == "invalid":
        return _build_result(
            status="mailbox_unverified",
            original_email=email,
            normalized_email=final_email,
            mailbox_verified=False,
            confirmation_required=False,
            clarification_required=True,
            problem_area=None,
            natural_readback=readback,
            spelling=spelling,
            verification=verification,
            reason=verification.get(
                "reason_message",
                "The email address failed mailbox verification.",
            ),
        )

    return _build_result(
        status="unknown",
        original_email=email,
        normalized_email=final_email,
        mailbox_verified=False,
        confirmation_required=False,
        clarification_required=True,
        problem_area=None,
        natural_readback=readback,
        spelling=spelling,
        verification=verification,
        reason=verification.get(
            "reason_message",
            "The email address could not be confidently verified.",
        ),
    )
