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
"""Support methods to nomalize GeoJSON inputs."""

from geojson_aoi.types import GeoJSON


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
    def get_transformation_funcs(geom: GeoJSON) -> str:
        """Construct and return string of functions that correspond with given geom."""
        # ST_Force2D strings z-coordinates
        val = "ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
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

        return val

    @staticmethod
    def query_as_feature_collection(table_id: str) -> str:
        """Query all geometries as FeatureCollection."""
        val = f"""SELECT json_build_object(
                    'type', 'FeatureCollection',
                    'features', json_agg(ST_AsGeoJSON(t.*)::json)
                    )
                FROM "{table_id}" as t(id, geom);"""

        return val

    # TODO: Consider merging interior rings as future feature should the need appear.
    # Will have a an extra flag to do this.
    # TODO: Also do not use this in a function.
    # @staticmethod
    # def merge_disjoints(geoms: list[GeoJSON], table_id: str) -> str:
    #    """Check whether a Polygon contains holes.
    #    If it does, do a ST_ConvexHull on the geom.
    #    """
    #    val = f"""
    #        CREATE OR REPLACE FUNCTION merge_disjoints() RETURNS SETOF "{table_id}" AS
    #        $BODY$
    #        DECLARE
    #            i "{table_id}"%rowtype;
    #        BEGIN
    #            FOR i IN
    #                SELECT * FROM "{table_id}"
    #            LOOP
    #                -- Using ST_NRings with ST_NumGeometries rather than ST_Disjoint
    #                -- This method seems to work for our use case for simply
    #                UPDATE "{table_id}"
    #                SET geometry = ST_ConvexHull(i.geometry)
    #                WHERE ST_NRings(i.geometry) - ST_NumGeometries(i.geometry) > 0;
    #
    #                RETURN NEXT i;
    #            END LOOP;
    #            RETURN;
    #        END;
    #        $BODY$
    #        LANGUAGE plpgsql;
    #
    #        SELECT * FROM merge_disjoints();
    #    """
    #
    #    return val
    #
    ## TODO: Consider merging overlaps are a future feature.
    # @staticmethod
    # def merge_overlaps(geoms: list[GeoJSON], table_id: str) -> str:
    #    """Check whether each MultiGeometry contains overlapping Polygons.
    #    Preform an ST_UnaryUnion if they overlap.
    #    """
    #    val = f"""
    #
    #    """
    #    return val
