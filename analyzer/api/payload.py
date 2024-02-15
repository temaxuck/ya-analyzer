import json

from aiohttp import Payload
from aiohttp.payload import JsonPayload as BaseJsonPayload
from aiohttp.typedefs import JSONEncoder
from datetime import date
from functools import singledispatch, partial
from typing import Any

from analyzer.config import Config


@singledispatch
def convert(value: Any) -> Any:
    raise TypeError(f"Unserializable value: {value!r}")


@convert.register(date)
def convert_date(value: date) -> str:
    return value.strftime(Config.BIRTH_DATE_FORMAT)


dumps = partial(json.dumps, default=convert, ensure_ascii=False)


class JsonPayload(BaseJsonPayload):
    def __init__(
        self,
        value: Any,
        encoding: str = "utf-8",
        content_type: str = "application/json",
        dumps: JSONEncoder = dumps,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(value, encoding, content_type, dumps, *args, **kwargs)


class AsyncGenJsonListPayload(Payload):
    """
    Iterate over AsyncIterable instances to serialize
    the data by parts and send to client
    """

    def __init__(
        self,
        value: Any,
        encoding: str = "utf-8",
        content_type: str = "application/json",
        root_object: str = "data",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.root_object = root_object
        super().__init__(value, encoding, content_type, *args, **kwargs)

    async def write(self, writer):
        await writer.write(('{"%s": [' % self.root_object).encode(self._encoding))

        first = True
        async for row in self._value:
            if not first:
                await writer.write(b",")
            else:
                first = False

            await writer.write(dumps(row).encode(self._encoding))

        await writer.write(b"]}")


__all__ = ("JsonPayload", "AsyncGenJsonListPayload")
