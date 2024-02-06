import logging

from aiohttp import web
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware
from configargparse import Namespace

from analyzer.api.routes import ROUTES
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

    for route in ROUTES:
        logger.debug(f"Registering route {route} as {route.URL_PATH}")
        app.router.add_route("*", route.URL_PATH, route)

    setup_aiohttp_apispec(app=app, title="Ya-analyzer API", swagger_path="/")

    # app.add_routes(routes)

    return app
