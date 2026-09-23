class AppException(Exception):
    """Base exception for application-level errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class AppointmentNotFoundError(AppException):
    """Raised when an appointment cannot be found."""
    pass

class AppointmentAlreadyCanceledError(AppException):
    """Raised when an operation is attempted on a canceled appointment."""
    pass

class AppointmentConflictError(AppException):
    """Raised when an appointment conflicts with another appointment."""
    pass

class AppointmentOwnershipError(AppException):
    """Raised when the provided phone number does not match the appointment."""
    pass

class InvalidTimezoneError(AppException):
    """Raised when an invalid timezone is provided."""
    pass