"""Parse various AOI GeoJSON formats and normalize."""

import json
import logging
import warnings
from pathlib import Path

from geojson_aoi.merge import merge_polygons
from geojson_aoi.normalize import normalize_featcol
from geojson_aoi.types import FeatureCollection

AllowedInputTypes = [
    "Polygon",
    "MultiPolygon",
    "Feature",
    "FeatureCollection",
    "GeometryCollection",
]

log = logging.getLogger(__name__)


def check_crs(featcol: FeatureCollection) -> None:
    """Warn the user if an invalid CRS is detected.

    Also does a rough check for one geometry, to determine if the
    coordinates are range 90/180 degree range.

    Args:
        featcol (FeatureCollection): a FeatureCollection.

    Returns:
        FeatureCollection: a FeatureCollection.
    """

    def is_valid_crs(crs_name):
        valid_crs_list = [
            "urn:ogc:def:crs:OGC:1.3:CRS84",
            "urn:ogc:def:crs:EPSG::4326",
            "WGS 84",
        ]
        return crs_name in valid_crs_list

    def is_valid_coordinate(coord):
        if coord is None:
            return False
        return -180 <= coord[0] <= 180 and -90 <= coord[1] <= 90

    if "crs" in featcol:
        crs = featcol.get("crs", {}).get("properties", {}).get("name")
        if not is_valid_crs(crs):
            warning_msg = (
                "Unsupported coordinate system, it is recommended to use a "
                "GeoJSON file in WGS84(EPSG 4326) standard."
            )
            log.warning(warning_msg)
            warnings.warn(UserWarning(warning_msg), stacklevel=2)

    features = featcol.get("features", [])
    coordinates = (
        features[-1].get("geometry", {}).get("coordinates", []) if features else []
    )

    first_coordinate = None
    if coordinates:
        while isinstance(coordinates, list):
            first_coordinate = coordinates
            coordinates = coordinates[0]

    if not is_valid_coordinate(first_coordinate):
        warning_msg = (
            "The coordinates within the GeoJSON file are not valid. "
            "Is the file empty?"
        )
        log.warning(warning_msg)
        warnings.warn(UserWarning(warning_msg), stacklevel=2)


def geojson_to_featcol(geojson_obj: dict) -> FeatureCollection:
    """Enforce GeoJSON is wrapped in FeatureCollection.

    The type check is done directly from the GeoJSON to allow parsing
    from different upstream libraries (e.g. geojson_pydantic).

    Args:
        geojson_obj (dict): a parsed geojson, to wrap in a FeatureCollection.

    Returns:
        FeatureCollection: a FeatureCollection.
    """
    geojson_type = geojson_obj.get("type")
    geojson_crs = geojson_obj.get("crs")

    if geojson_type == "FeatureCollection":
        log.debug("Already in FeatureCollection format, reparsing")
        features = geojson_obj.get("features", [])
    elif geojson_type == "Feature":
        log.debug("Converting Feature to FeatureCollection")
        features = [geojson_obj]
    else:
        log.debug("Converting Geometry to FeatureCollection")
        features = [{"type": "Feature", "geometry": geojson_obj, "properties": {}}]

    featcol = {"type": "FeatureCollection", "features": features}
    if geojson_crs:
        featcol["crs"] = geojson_crs
    return featcol


def parse_aoi(
    geojson_raw: str | bytes | dict, merge: bool = False
) -> FeatureCollection:
    """Parse a GeoJSON file or data struc into a normalized FeatureCollection.

    Args:
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

    # Convert to FeatureCollection
    featcol = geojson_to_featcol(geojson_parsed)
    if not featcol.get("features", []):
        raise ValueError("Failed parsing geojson")

    # Warn the user if invalid CRS detected
    check_crs(featcol)

    if not merge:
        return normalize_featcol(featcol)
    return merge_polygons(normalize_featcol(featcol))
