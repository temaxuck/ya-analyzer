from aiohttp import web

from analyzer.utils.argparse import get_arg_parser
from analyzer.utils.logging import set_logging
from analyzer.config import Config


routes = web.RouteTableDef()
app = None
cfg = Config()
parser = None


@routes.get(r"/next/{num:\d+}")
async def get_next_num(request: web.Request) -> web.Response:
    num = int(request.match_info["num"])
    return web.Response(text=f"Next number for number {num} is: {num + 1}")


def init_app() -> web.Application:
    parser = get_arg_parser(cfg)
    args = parser.parse_args()

    set_logging(args.log_level, args.log_format)

    app = web.Application()
    app.add_routes(routes)

    return app


def run_app() -> None:
    app = init_app()
    web.run_app(app, host=cfg.API_HOST, port=cfg.API_PORT)


if __name__ == "__main__":
    run_app()
