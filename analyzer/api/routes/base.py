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


class BaseImportView(BaseView):
    @property
    def import_id(self) -> int:
        return int(self.request.match_info.get("import_id"))

    async def check_if_import_exists(self) -> bool:
        async with self.pg.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT import_id FROM import WHERE import_id=%s", self.import_id
                )
                import_id = await cur.fetchone()

                if not import_id:
                    raise web.HTTPNotFound()

        return True
