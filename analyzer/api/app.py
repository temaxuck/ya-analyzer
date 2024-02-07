import logging

from aiohttp import web, PAYLOAD_REGISTRY
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from configargparse import Namespace
from types import AsyncGeneratorType, MappingProxyType
from typing import AsyncIterable, Mapping

from analyzer.api.routes import ROUTES
from analyzer.api.payload import AsyncGenJsonListPayload, JsonPayload
from analyzer.config import Config
from analyzer.utils.pg import setup_pg

logger = logging.getLogger(__name__)


def init_app(args: Namespace, cfg: Config) -> web.Application:
    """
    Initialize aiohttp web server
    """

    app = web.Application(
        client_max_size=args.api_max_request_size,
        middlewares=[validation_middleware],
    )
    app["config"] = cfg
    app.cleanup_ctx.append(lambda _: setup_pg(app, args=args))

    # app.add_routes(routes)
    for route in ROUTES:
        logger.debug(f"Registering route {route} as {route.URL_PATH}")
        app.router.add_route("*", route.URL_PATH, route)

    setup_aiohttp_apispec(app=app, title="Ya-analyzer API", swagger_path="/")

    PAYLOAD_REGISTRY.register(
        AsyncGenJsonListPayload, (AsyncGeneratorType, AsyncIterable)
    )
    PAYLOAD_REGISTRY.register(
        JsonPayload, (Mapping, MappingProxyType)
    )

    return app
