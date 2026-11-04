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
"""Run the normalise query in PostGIS."""

from typing import Any

from psycopg import AsyncConnection, sql

from geojson_aoi.normalize import NORMALIZE
from geojson_aoi.types import FeatureCollection


async def normalize_async(
    db: str | AsyncConnection, source: sql.SQL, params: dict[str, Any]
) -> tuple[int, bool, FeatureCollection]:
    """Return the skipped geometry count, if within bounds, and FeatureCollection."""
    if isinstance(db, str):
        async with await AsyncConnection.connect(db) as connection:
            return await _execute(connection, source, params)
    if isinstance(db, AsyncConnection):
        return await _execute(db, source, params)
    raise ValueError("The `db` must be a connection string or psycopg connection.")


async def _execute(
    connection: AsyncConnection, source: sql.SQL, params: dict[str, Any]
) -> tuple[int, bool, FeatureCollection]:
    async with connection.cursor() as cur:
        await cur.execute(NORMALIZE.format(source=source), params)
        return await cur.fetchone()
