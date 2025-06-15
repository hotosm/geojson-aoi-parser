#!/usr/bin/env python
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
# The code is this file was originally developed by
# Emir Fabio Cognigni (https://github.com/emirfabio),
# Sam Woodcock (https://github.com/spwoodcock), and
# Stephen Garland (https://github.com/stephanGarland)
# for the HOT pg-nearest-city module (https://github.com/hotosm/pg-nearest-city).

"""Database config for Postgres."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DbConfig:
    """Database config for Postgres.

    Allows overriding values via constructor parameters, fallback to env vars.


    Args:
        dbname(str): Database name.
        user(str): Database user.
        password(str): Database password.
        host(str): Database host.
        port(str): Database port.
    """

    dbname: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None

    def __post_init__(self):
        """Ensures env variables are read at runtime, not at class definition."""
        self.dbname = self.dbname or os.getenv("GEOJSON_AOI_DB_NAME")
        self.user = self.user or os.getenv("GEOJSON_AOI_DB_USER")
        self.password = self.password or os.getenv("GEOJSON_AOI_DB_PASSWORD")
        self.host = self.host or os.getenv("GEOJSON_AOI_DB_HOST", "db")
        self.port = self.port or int(os.getenv("GEOJSON_AOI_DB_PORT", "5432"))

        # Raise error if any required field is missing
        missing_fields = [
            field
            for field in ["dbname", "user", "password"]
            if not getattr(self, field)
        ]
        if missing_fields:
            raise ValueError(
                f"Missing required database config fields: {', '.join(missing_fields)}"
            )

    def get_connection_string(self) -> str:
        """Connection string that psycopg accepts."""
        return (
            f"dbname={self.dbname} user={self.user} password={self.password} "
            f"host={self.host} port={self.port}"
        )
