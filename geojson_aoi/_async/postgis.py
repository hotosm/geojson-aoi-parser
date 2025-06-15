# Copyright (c) Humanitarian OpenStreetMap Team
# This file is part of geojson-aoi-parser.
#
#     geojson-aoi-parser is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     geojson-aoi-parser is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with geojson-aoi-parser.  If not, see <https:#www.gnu.org/licenses/>.
#
"""Wrapper around PostGIS geometry functions."""

import logging
from uuid import uuid4

from psycopg import AsyncConnection, connect, sql
from psycopg.types.json import Jsonb

from geojson_aoi.normalize import Normalize
from geojson_aoi.types import GeoJSON

log = logging.getLogger(__name__)


class AsyncPostGis:
    """An asynchronous database connection.

    Can reuse an existing upstream connection.
    """

    async def __init__(
        self, db: str | AsyncConnection, geoms: list[GeoJSON], merge: bool = False
    ):
        """Initialise variables and compose classes."""
        self.table_id = uuid4().hex
        self.geoms = geoms
        self.db = db
        self.featcol = None

        self.normalize = Normalize()

        # NOTE: Pontential future polygon merging feature.
        # self.merge = merge

    async def __aenter__(self) -> "AsyncPostGis":
        """Initialise the database via context manager."""
        await self.create_connection()

        async with self.connection.cursor() as cur:
            await cur.execute(self.normalize.init_table(self.table_id))

            for geom in self.geoms:
                st_functions = self.normalize.get_transformation_funcs(geom)

                SQL = sql.SQL("""
                        INSERT INTO {} (geometry)
                        VALUES ({});
                    """).format(sql.Identifier(self.table_id), sql.SQL(st_functions))

                data = (Jsonb(geom),)

                await cur.execute(SQL, data)

            # NOTE: Potential future polygon merging feature.
            # if self.merge:
            #    cur.execute(self.normalize.merge_disjoints(self.geoms, self.table_id))

            await cur.execute(self.normalize.query_as_feature_collection(self.table_id))
            self.featcol = await cur.fetchall()[0][0]

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Execute the SQL and optionally close the db connection."""
        await self.close_connection()

    async def create_connection(self) -> None:
        """Get a new database connection."""
        # Create new connection
        if isinstance(self.db, str):
            self.connection = await connect(self.db)
            self.is_new_connection = True

        # Reuse existing connection
        elif isinstance(self.db, AsyncConnection):
            self.connection = self.db
            self.is_new_connection = False

        # Else, error
        else:
            msg = (
                "The `db` variable is not a valid string or "
                "existing psycopg connection."
            )
            log.error(msg)
            raise ValueError(msg)

    async def close_connection(self) -> None:
        """Close the database connection."""
        if not self.connection:
            return

        # Execute all commands in a transaction before closing
        try:
            await self.connection.commit()
        except Exception as e:
            log.error(e)
            log.error("Error committing psycopg transaction to db")
        finally:
            # Only close the connection if it was newly created
            if self.is_new_connection:
                await self.connection.close()
