"""
    Resource `View` base classes
"""

from aiohttp import web


class BaseView(web.View):
    URL_PATH: str

    @property
    def app(self) -> web.Application:
        return self.request.app

    @property
    def pg(self) -> "Pool":
        return self.request.app["pg"]
