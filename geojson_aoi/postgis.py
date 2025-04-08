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

import json
import logging
from uuid import uuid4

from psycopg import Connection, connect

from geojson_aoi.types import FeatureCollection, GeoJSON

log = logging.getLogger(__name__)


class Normalize:
    """Normalise the geometry.

    - Strip z-dimension (force 2D).
    - Remove geoms from GeometryCollection.
    - Multi geometries to single geometries.
    """

    @staticmethod
    def init_table(table_id: str) -> str:
        """Create the table for geometry processing."""
        return f"""
            CREATE TEMP TABLE "{table_id}" (
                id SERIAL PRIMARY KEY,
                geometry GEOMETRY(Polygon, 4326)
            );
        """

    @staticmethod
    def insert(geoms: list[GeoJSON], table_id: str, merge: bool) -> str:
        """Insert geometries into db, normalising where possible."""
        values = []
        for geom in geoms:
            # ST_Force2D strings z-coordinates
            val = (
                "ST_Force2D(ST_SetSRID("
                f"ST_GeomFromGeoJSON('{json.dumps(geom)}'), 4326))"
            )

            # ST_CollectionExtract converts any GeometryCollections
            # into MultiXXX geoms
            if geom.get("type") == "GeometryCollection":
                val = f"ST_CollectionExtract({val})"

            # ST_Dump extracts all MultiXXX geoms to single geom equivalents
            # TODO ST_Dump (complex, as it returns multiple geometries!)

            # ST_ForcePolygonCW forces clockwise orientation for
            # their exterior ring
            if geom.get("type") == "Polygon" or geom.get("type") == "MultiPolygon":
                val = f"ST_ForcePolygonCW({val})"

            values.append(val)

        value_string = ", ".join(values)
        return f"""
            INSERT INTO "{table_id}" (geometry)
            VALUES ({value_string});
        """

    @staticmethod
    def query_as_feature_collection(table_id: str) -> FeatureCollection:
        """Build the query string to get all of our geometries into a nice FeatureCollection."""
        val = f"""SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', json_agg(ST_AsGeoJSON(t.*)::json)
                    )
                FROM "{table_id}" as t(id, geom);"""

        return val

    # TODO: Consider merging interior rings as future feature should the need appear.
    # Will have a an extra flag to do this.
    # TODO: Also do not use this in a function.
    @staticmethod
    def merge_disjoints(geoms: list[GeoJSON], table_id: str) -> str:
        """Check whether a Polygon contains holes. If it does, do a ST_ConvexHull on the geom
        """
        val = f"""
            CREATE OR REPLACE FUNCTION merge_disjoints() RETURNS SETOF "{table_id}" AS
            $BODY$
            DECLARE
                i "{table_id}"%rowtype;
            BEGIN
                FOR i IN
                    SELECT * FROM "{table_id}"
                LOOP
                    -- Using ST_NRings with ST_NumGeometries rather than ST_Disjoint
                    -- This method seems to work for our use case for simply
                    UPDATE "{table_id}"
                    SET geometry = ST_ConvexHull(i.geometry)
                    WHERE ST_NRings(i.geometry) - ST_NumGeometries(i.geometry) > 0;

                    RETURN NEXT i;
                END LOOP;
                RETURN;
            END;
            $BODY$
            LANGUAGE plpgsql;

            SELECT * FROM merge_disjoints();
        """

        return val
    
    # TODO: Consider merging overlaps are a future feature.
    @staticmethod
    def merge_overlaps(geoms: list[GeoJSON], table_id: str) -> str:
        """Check whether each MultiGeometry contains overlapping Polygons. Preform an ST_UnaryUnion
        if they overlap.
        """
        val = f"""

        """
        return val


class PostGis:
    """A synchronous database connection.

    Typically called standalone.
    Can reuse an existing upstream connection.
    """

    def __init__(self, db: str | Connection, geoms: list[GeoJSON], merge: bool = False):
        """Initialise variables and compose classes."""
        self.table_id = uuid4().hex
        self.geoms = geoms
        self.db = db
        self.featcol = None

        self.normalize = Normalize()
        self.merge = merge

    def __enter__(self) -> "PostGis":
        """Initialise the database via context manager."""
        self.create_connection()

        with self.connection.cursor() as cur:
            cur.execute(self.normalize.init_table(self.table_id))
            cur.execute(self.normalize.insert(self.geoms, self.table_id, self.merge))

            if self.merge:
                cur.execute(self.normalize.merge_disjoints(self.geoms, self.table_id))

            cur.execute(self.normalize.query_as_feature_collection(self.table_id))
            self.featcol = cur.fetchall()[0][0]

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Execute the SQL and optionally close the db connection."""
        self.close_connection()

    def create_connection(self) -> None:
        """Get a new database connection."""
        # Create new connection
        if isinstance(self.db, str):
            self.connection = connect(self.db)
            self.is_new_connection = True
        # Reuse existing connection
        elif isinstance(self.db, Connection):
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

    def close_connection(self) -> None:
        """Close the database connection."""
        if not self.connection:
            return

        # Execute all commands in a transaction before closing
        try:
            self.connection.commit()
        except Exception as e:
            log.error(e)
            log.error("Error committing psycopg transaction to db")
        finally:
            # Only close the connection if it was newly created
            if self.is_new_connection:
                self.connection.close()


class PostGisAsync:
    """An asynchronous database connection.

    Typically called from an async web server.
    Can reuse an existing upstream connection.
    """
