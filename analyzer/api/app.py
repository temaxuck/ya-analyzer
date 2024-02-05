from aiohttp import web
from configargparse import Namespace

from analyzer.api.routes import routes
from analyzer.config import Config


def init_app(args: Namespace, cfg: Config) -> web.Application:
    """
    Initialize aiohttp web server
    """

    app = web.Application(client_max_size=args.api_max_request_size)
    app["config"] = cfg
    app.add_routes(routes)

    return app
