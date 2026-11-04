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

"""Parse various AOI formats and normalize."""

import json
import logging
import warnings
from pathlib import Path

from psycopg import Connection
from psycopg.types.json import Jsonb

from geojson_aoi._sync.postgis import normalize
from geojson_aoi.normalize import GEOJSON_SOURCE, KML_SOURCE
from geojson_aoi.types import FeatureCollection, GeoJSON

ALLOWED_TYPES = (
    "Polygon",
    "MultiPolygon",
    "Feature",
    "FeatureCollection",
    "GeometryCollection",
)
VALID_CRS = (
    "urn:ogc:def:crs:OGC:1.3:CRS84",
    "urn:ogc:def:crs:EPSG::4326",
    "WGS 84",
)

log = logging.getLogger(__name__)


def warn(msg: str) -> None:
    """Log and emit a UserWarning."""
    log.warning(msg)
    warnings.warn(UserWarning(msg), stacklevel=3)


def validate_geojson(geojson: GeoJSON) -> None:
    """Check the GeoJSON type and CRS."""
    if not isinstance(geojson, dict):
        raise ValueError("GeoJSON input must be a valid dict, str, or bytes")
    if "type" not in geojson:
        raise ValueError("Provided GeoJSON is empty")
    if geojson["type"] not in ALLOWED_TYPES:
        raise ValueError(f"The GeoJSON type must be one of: {ALLOWED_TYPES}")

    crs = (geojson.get("crs") or {}).get("properties", {}).get("name")
    if crs and crs not in VALID_CRS:
        warn("Unsupported coordinate system. Use WGS84 (EPSG:4326).")


def parse_aoi(
    db: str | Connection, geojson_raw: str | bytes | dict, merge: bool = False
) -> FeatureCollection:
    """Parse a GeoJSON or KML AOI into a normalized FeatureCollection of Polygons.

    Non-Polygon geometries are skipped with a UserWarning.

    Args:
        db (str | Connection): Existing db connection, or connection string.
        geojson_raw (str | bytes | dict): GeoJSON or KML file path, string or
            file bytes, or a GeoJSON dict.
        merge (bool): Merge all Polygons into a single Polygon, without holes.
            Disjoint Polygons are joined by their convex hull.

    Returns:
        FeatureCollection: a FeatureCollection of Polygons.

    Raises:
        ValueError: If the input is invalid or contains no Polygons.
    """
    raw = geojson_raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    if isinstance(raw, str) and not raw.lstrip().startswith(("{", "<")):
        log.debug(f"Parsing AOI file: {raw}")
        raw = Path(raw).read_text(encoding="utf-8-sig")

    if isinstance(raw, str) and raw.lstrip().startswith("<"):
        source, data = KML_SOURCE, raw
    else:
        geojson = json.loads(raw) if isinstance(raw, str) else raw
        validate_geojson(geojson)
        source, data = GEOJSON_SOURCE, Jsonb(geojson)

    params = {"data": data, "merge": merge}
    skipped, in_bounds, featcol = normalize(db, source, params)

    if skipped:
        warn(f"Skipped {skipped} non-Polygon geometries in the AOI.")
    if not featcol["features"]:
        raise ValueError("No Polygon geometries found in the AOI.")
    if not in_bounds:
        warn("Coordinates are outside WGS84 (EPSG:4326) bounds.")

    return featcol
