from asyncio import AbstractEventLoop
from configparser import ConfigParser
from typing import NamedTuple, Optional

import asyncpg

config = ConfigParser()
config.read("config.ini")


class postgresql(NamedTuple):
    user = config["DATABASE"]["username"]
    password = config["DATABASE"]["password"]
    server = config["DATABASE"]["server"]
    host = config["DATABASE"]["host"]

    configuration = {
        "user": user,
        "password": password,
        "database": server,
        "host": host,
    }


class Database:
    def __init__(self, loop: AbstractEventLoop):
        self.loop = loop
        self.pool = self.loop.run_until_complete(self.create_asyncpg_pool())

    @staticmethod
    async def create_asyncpg_pool() -> Optional[asyncpg.pool.Pool]:
        try:
            return await asyncpg.create_pool(
                **postgresql.configuration, command_timeout=60
            )
        except Exception as error:
            print("Failed to connect to Postgresql database: ", error)
