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

from psycopg import Connection, sql

from geojson_aoi.normalize import NORMALIZE
from geojson_aoi.types import FeatureCollection


def normalize(
    db: str | Connection, source: sql.SQL, params: dict[str, Any]
) -> tuple[int, bool, FeatureCollection]:
    """Return the skipped geometry count, if within bounds, and FeatureCollection."""
    if isinstance(db, str):
        with Connection.connect(db) as connection:
            return _execute(connection, source, params)
    if isinstance(db, Connection):
        return _execute(db, source, params)
    raise ValueError("The `db` must be a connection string or psycopg connection.")


def _execute(
    connection: Connection, source: sql.SQL, params: dict[str, Any]
) -> tuple[int, bool, FeatureCollection]:
    with connection.cursor() as cur:
        cur.execute(NORMALIZE.format(source=source), params)
        return cur.fetchone()
