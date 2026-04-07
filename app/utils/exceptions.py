from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.core.exceptions import ValidationError


class ConflictError(Exception):
    """
    Exception to raise when a conflict occurs, resulting in a 409 Conflict response.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def contains_error_code(exception: ValidationError, code: str) -> bool:
    """Return True if the given exception contains an error with the given error code."""
    if hasattr(exception, "code") and exception.code == code:
        return True

    # Iterating over the messages does not work here because the messages do not
    # contain the error codes of the validation.
    if hasattr(exception, "error_dict"):
        for errors_field in exception.error_dict.values():
            for error in errors_field:
                if error.code == code:
                    return True
    elif hasattr(exception, "error_list"):
        for error in exception.error_list:
            if error.code == code:
                return True
    return False


def extract_error_messages(exception: ValidationError) -> list[str]:
    """Returns the error messages in the given object as a list of strings."""
    messages = []
    for message in exception:
        if isinstance(message, tuple):
            non_empty = [m for m in message[1] if m != "None"]
            messages.extend(non_empty)
        elif message != "None":
            messages.append(message)
    return messages
