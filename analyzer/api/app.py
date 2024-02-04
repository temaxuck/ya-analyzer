from aiohttp import web
from configargparse import Namespace

from analyzer.api.routes import routes


def init_app(args: Namespace) -> web.Application:
    """
    Initialize aiohttp web server
    """

    app = web.Application(client_max_size=args.api_max_request_size)
    app.add_routes(routes)

    return app
