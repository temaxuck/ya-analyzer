import logging

from aiohttp import web, PAYLOAD_REGISTRY
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from datetime import date
from configargparse import Namespace
from types import AsyncGeneratorType, MappingProxyType
from typing import AsyncIterable, Mapping

from analyzer.api.routes import ROUTES
from analyzer.api.middleware import error_middleware, handle_validation_error
from analyzer.api.payload import AsyncGenJsonListPayload, JsonPayload
from analyzer.config import Config
from analyzer.utils.pg import setup_pg

logger = logging.getLogger(__name__)


def init_app(args: Namespace, cfg: Config) -> web.Application:
    """
    Initialize aiohttp web server
    """

    # in debug mode we want to report errors
    middlewares = [validation_middleware, error_middleware]
    if cfg.DEBUG:
        middlewares.pop()

    app = web.Application(
        client_max_size=args.api_max_request_size,
        middlewares=middlewares,
    )
    app["config"] = cfg
    app.cleanup_ctx.append(lambda _: setup_pg(app, args=args))

    # app.add_routes(routes)
    for route in ROUTES:
        logger.debug(f"Registering route {route} as {route.URL_PATH}")
        app.router.add_route("*", route.URL_PATH, route)

    setup_aiohttp_apispec(
        app=app,
        title="Ya-analyzer API",
        swagger_path="/",
        error_callback=handle_validation_error,
    )

    PAYLOAD_REGISTRY.register(
        AsyncGenJsonListPayload,
        (AsyncGeneratorType, AsyncIterable),
    )
    PAYLOAD_REGISTRY.register(JsonPayload, (Mapping, MappingProxyType, date))

    return app
