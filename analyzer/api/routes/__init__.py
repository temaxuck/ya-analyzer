from aiohttp import web

routes = web.RouteTableDef()


@routes.get(r"/next/{num:\d+}")
async def get_next_num(request: web.Request) -> web.Response:
    num = int(request.match_info["num"])
    return web.Response(text=f"Next number for number {num} is: {num + 1}")
