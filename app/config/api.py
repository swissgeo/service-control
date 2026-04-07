from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError
from ninja.errors import ValidationError as NinjaValidationError

from config.logging import LoggedNinjaAPI
from organization.api import router as organization_router
from user.api import router as user_router
from utils.exceptions import ConflictError, contains_error_code, extract_error_messages

api = LoggedNinjaAPI()

api.add_router("", organization_router)
api.add_router("", user_router)


@api.exception_handler(DjangoValidationError)
def handle_django_validation_error(
    request: HttpRequest,
    exception: DjangoValidationError,
) -> HttpResponse:
    """Convert the given validation error to a response with corresponding status."""
    error_code_unique_constraint_violated = "unique"

    status = 409 if contains_error_code(exception, error_code_unique_constraint_violated) else 400

    messages = extract_error_messages(exception)
    return api.create_response(
        request,
        {
            "code": status,
            "description": messages,
        },
        status=status,
    )


@api.exception_handler(ConflictError)
def handle_conflict_error(
    request: HttpRequest,
    exception: ConflictError,
) -> HttpResponse:
    return api.create_response(
        request,
        {
            "code": 409,
            "description": exception.message,
        },
        status=409,
    )


@api.exception_handler(Http404)
@api.exception_handler(ObjectDoesNotExist)
def handle_404_not_found(
    request: HttpRequest,
    exception: Http404,  # noqa: ARG001 unused argument
) -> HttpResponse:
    return api.create_response(
        request,
        {
            "code": 404,
            "description": "Resource not found",
        },
        status=404,
    )


@api.exception_handler(Exception)
def handle_exception(
    request: HttpRequest,
    exception: Exception,  # noqa: ARG001 unused argument
) -> HttpResponse:
    return api.create_response(
        request,
        {
            "code": 500,
            "description": "Internal Server Error",
        },
        status=500,
    )


@api.exception_handler(HttpError)
def handle_http_error(request: HttpRequest, exception: HttpError) -> HttpResponse:
    return api.create_response(
        request,
        {
            "code": exception.status_code,
            "description": exception.message,
        },
        status=exception.status_code,
    )


@api.exception_handler(AuthenticationError)
def handle_unauthorized(
    request: HttpRequest,
    exception: AuthenticationError,  # noqa: ARG001 unused argument
) -> HttpResponse:
    return api.create_response(
        request,
        {
            "code": 401,
            "description": "Unauthorized",
        },
        status=401,
    )


@api.exception_handler(NinjaValidationError)
def handle_ninja_validation_error(
    request: HttpRequest,
    exception: NinjaValidationError,
) -> HttpResponse:
    messages: list[str] = []
    for error in exception.errors:
        messages.extend(error.values())

    return api.create_response(
        request,
        {
            "code": 400,
            "description": messages,
        },
        status=400,
    )


root = NinjaAPI(urls_namespace="root")


@root.get("/checker")
def checker(request: HttpRequest) -> dict[str, bool | str]:  # noqa: ARG001 unused argument
    return {"success": True, "message": "OK"}
