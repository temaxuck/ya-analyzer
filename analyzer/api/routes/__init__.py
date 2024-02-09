"""
from aiohttp import web

# Not using `routes` anymore
routes = web.RouteTableDef()


# Test handler
@routes.get(r"/next/{num:\d+}")
async def get_next_num(request: web.Request) -> web.Response:
    num = int(request.match_info["num"])
    return web.Response(text=f"Next number for number {num} is: {num + 1}")
"""

from .imports import ImportsView
from .citizens import CitizensView
from .citizen import CitizenView
from .citizen_presents import CitizenPresentsView
from .age_stats import AgeStatsView

ROUTES = (
    ImportsView,
    CitizensView,
    CitizenView,
    CitizenPresentsView,
    AgeStatsView,
)
