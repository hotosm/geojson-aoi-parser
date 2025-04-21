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

"""Parse various AOI GeoJSON formats and normalize."""

import json
import logging
import warnings
from pathlib import Path

from psycopg import Connection

from geojson_aoi.postgis import PostGis
from geojson_aoi.types import Feature, FeatureCollection, GeoJSON

AllowedInputTypes = [
    "Polygon",
    "MultiPolygon",
    "Feature",
    "FeatureCollection",
    "GeometryCollection",
]

log = logging.getLogger(__name__)


def check_crs(geojson: GeoJSON) -> None:
    """Warn the user if an invalid CRS is detected.

    Also does a rough check for one geometry, to determine if the
    coordinates are range 90/180 degree range.

    Args:
        geojson (GeoJSON): a GeoJSON.

    Returns:
        None
    """

    def is_valid_crs(crs_name: str) -> bool:
        valid_crs_list = [
            "urn:ogc:def:crs:OGC:1.3:CRS84",
            "urn:ogc:def:crs:EPSG::4326",
            "WGS 84",
        ]
        return crs_name in valid_crs_list

    def is_valid_coordinate(coord: list[float]) -> bool:
        return len(coord) == 2 and -180 <= coord[0] <= 180 and -90 <= coord[1] <= 90

    crs = geojson.get("crs", {}).get("properties", {}).get("name")
    if crs and not is_valid_crs(crs):
        warning_msg = (
            "Unsupported coordinate system. Use WGS84 (EPSG 4326) for best results."
        )
        log.warning(warning_msg)
        warnings.warn(UserWarning(warning_msg), stacklevel=2)

    geom = geojson.get("geometry") or geojson.get("features", [{}])[-1].get(
        "geometry", {}
    )
    coordinates = geom.get("coordinates", [])

    # Drill down into nested coordinates to find the first coordinate
    while isinstance(coordinates, list) and len(coordinates) > 0:
        coordinates = coordinates[0]

    if not is_valid_coordinate(coordinates):
        warning_msg = "Invalid coordinates in GeoJSON. Ensure the file is not empty."
        log.warning(warning_msg)
        warnings.warn(UserWarning(warning_msg), stacklevel=2)


def strip_featcol(geojson_obj: GeoJSON | Feature | FeatureCollection) -> list[GeoJSON]:
    """Remove FeatureCollection and Feature wrapping.

    Args:
        geojson_obj (dict): a parsed geojson.

    Returns:
        list[GeoJSON]: a list of geometries.
    """
    # TODO: add logic to retain and existing properties?
    properties = ""
    if geojson_obj.get("type") in ["FeatureCollection", "Feature"]:
        properties = geojson_obj.get("properties")

    if geojson_obj.get("crs"):
        # Warn the user if invalid CRS detected
        check_crs(geojson_obj)

    geojson_type = geojson_obj.get("type")

    if geojson_type == "FeatureCollection":
        geoms = [feature["geometry"] for feature in geojson_obj.get("features", [])]

        # Drill in and check if each feature is a GeometryCollection. 
        # If so, our work isn't done.
        temp_geoms = []
        for geom in geoms:
            if geom["type"] == "GeometryCollection":

                for item in geom["geometries"]:
                    temp_geoms.append(item)

                geoms = temp_geoms

    elif geojson_type == "Feature":
        geoms = [geojson_obj.get("geometry")]

    elif geojson_type == "MultiPolygon":

        # MultiPolygon should parse out into List of Polygons and maintain properties.
        temp_geoms = []
        for coordinate in geojson_obj.get("coordinates"):

            # Build a Polygon from scratch out of the coordinates.
            polygon = {"type": "Polygon",
                       "coordinates": coordinate}
            temp_geoms.append(polygon)

        geoms = temp_geoms

    else:
        geoms = [geojson_obj]
    
    if(properties):
        geoms["properties"] = properties

    return geoms


def parse_aoi(
    db: str | Connection, geojson_raw: str | bytes | dict, merge: bool = False
) -> FeatureCollection:
    """Parse a GeoJSON file or data struc into a normalized FeatureCollection.

    Args:
        db (str | Connection): Existing db connection, or connection string.
        geojson_raw (str | bytes | dict): GeoJSON file path, JSON string, dict,
            or file bytes.
        merge (bool): If any nested Polygons / MultiPolygon should be merged.

    Returns:
        FeatureCollection: a FeatureCollection.
    """
    # Parse different input types
    if isinstance(geojson_raw, bytes):
        geojson_parsed = json.loads(geojson_raw)

    if isinstance(geojson_raw, str):
        if Path(geojson_raw).exists():
            log.debug(f"Parsing geojson file: {geojson_raw}")
            with open(geojson_raw, "rb") as geojson_file:
                geojson_parsed = json.load(geojson_file)
        else:
            geojson_parsed = json.loads(geojson_raw)

    elif isinstance(geojson_raw, dict):
        geojson_parsed = geojson_raw
    else:
        raise ValueError("GeoJSON input must be a valid dict, str, or bytes")

    # Throw error if no data
    if geojson_parsed is None or geojson_parsed == {} or "type" not in geojson_parsed:
        raise ValueError("Provided GeoJSON is empty")

    # Throw error if wrong geometry type
    if geojson_parsed["type"] not in AllowedInputTypes:
        raise ValueError(f"The GeoJSON type must be one of: {AllowedInputTypes}")

    # Extract from FeatureCollection
    geoms = strip_featcol(geojson_parsed)

    with PostGis(db, geoms, merge) as result:
        print(result.featcol)
        return result.featcol
