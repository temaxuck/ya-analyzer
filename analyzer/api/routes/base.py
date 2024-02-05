"""
    Resource `View` base classes
"""

from aiohttp import web
from asyncpgsa import PG


class BaseView(web.View):
    URL_PATH: str

    @property
    def pg(self) -> PG:
        return self.request.app["pg"]
