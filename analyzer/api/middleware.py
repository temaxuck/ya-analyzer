import logging

from aiohttp.web_exceptions import (
    HTTPException,
    HTTPBadRequest,
    HTTPInternalServerError,
)
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Handler
from http import HTTPStatus
from typing import Optional, Mapping
from marshmallow import ValidationError

from analyzer.api.payload import JsonPayload

logger = logging.getLogger(__name__)


def format_http_error(
    http_error_cls: HTTPException,
    message: Optional[str] = None,
    fields: Optional[Mapping] = None,
) -> HTTPException:
    status = HTTPStatus(http_error_cls.status_code)

    error = {
        "code": status.name.lower(),
        "message": message or status.description,
    }

    if fields:
        error["fields"] = fields

    return http_error_cls(body={"error": error})


def handle_validation_error(error: ValidationError, *_) -> HTTPException:
    raise format_http_error(
        HTTPBadRequest, "Request validation has failed", error.messages
    )


@middleware
async def error_middleware(request: Request, handler: Handler):
    try:
        return await handler(request)
    except HTTPException as err:
        if not isinstance(err.body, JsonPayload):
            err = format_http_error(err.__class__, err.text)

        raise err
    except ValidationError as err:
        raise handle_validation_error(err)

    except Exception:
        logger.exception("Unhandled exception")

        raise format_http_error(HTTPInternalServerError)
