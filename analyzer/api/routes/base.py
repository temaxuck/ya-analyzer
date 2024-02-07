"""
    Resource `View` base classes
"""

from aiohttp import web

from analyzer.db.schema import import_table


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

    async def check_if_import_exists(self) -> None:
        async with self.pg.acquire() as conn:
            result = await conn.execute(
                import_table.select().where(import_table.c.import_id == self.import_id)
            )
            import_id = await result.scalar()

            if not import_id:
                raise web.HTTPNotFound()
