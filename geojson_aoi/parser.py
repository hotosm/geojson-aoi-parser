"""Parse various AOI GeoJSON formats and normalize."""

import json
import logging
import warnings
from itertools import chain
from pathlib import Path
from typing import Any

AllowedInputTypes = [
    "Polygon",
    "MultiPolygon",
    "Feature",
    "FeatureCollection",
    "GeometryCollection",
]
Coordinate = float | int
PointGeom = tuple[Coordinate, Coordinate]
PolygonGeom = list[list[PointGeom]]

Properties = dict[str, Any]
Feature = dict[str, Any]
FeatureCollection = dict[str, Any]

log = logging.getLogger(__name__)


### Normalise Funcs ###


def _normalize_featcol(featcol: FeatureCollection) -> FeatureCollection:
    """Normalize a FeatureCollection into a standardised format.

    The final FeatureCollection will only contain:
    - Polygon
    - LineString
    - Point

    Processed:
    - MultiPolygons will be divided out into individual polygons.
    - GeometryCollections wrappers will be stripped out.
    - Removes any z-dimension coordinates, e.g. [43, 32, 0.0]

    Args:
        featcol: A parsed FeatureCollection.

    Returns:
        FeatureCollection: A normalized FeatureCollection.
    """
    for feat in featcol.get("features", []):
        geom = feat.get("geometry")
        if not geom or "type" not in geom:
            continue  # Skip invalid features

        # Strip out GeometryCollection wrappers
        if (
            geom.get("type") == "GeometryCollection"
            and len(geom.get("geometries", [])) == 1
        ):
            feat["geometry"] = geom.get("geometries")[0]

        # Remove any z-dimension coordinates
        coords = geom.get("coordinates")
        if coords:
            geom["coordinates"] = _remove_z_dimension(coords)

    # Convert MultiPolygon type --> individual Polygons
    return _multigeom_to_singlegeom(featcol)


def _remove_z_dimension(coords: Any) -> Any:
    """Recursively remove the Z dimension from coordinates."""
    if isinstance(coords[0], (list, tuple)):
        # If the first element is a list, recurse into each sub-list
        return [_remove_z_dimension(sub_coord) for sub_coord in coords]
    else:
        # If the first element is not a list, it's a coordinate pair (x, y, z)
        return coords[:2]  # Return only [x, y]


def _multigeom_to_singlegeom(featcol: FeatureCollection) -> FeatureCollection:
    """Converts any Multi(xxx) geometry types to list of individual geometries.

    Args:
        featcol : A GeoJSON FeatureCollection of geometries.

    Returns:
        FeatureCollection: A GeoJSON FeatureCollection containing
            single geometry types only: Polygon, LineString, Point.
    """

    def split_multigeom(
        geom: dict[str, Any], properties: dict[str, Any]
    ) -> list[Feature]:
        """Splits multi-geometries into individual geometries."""
        geom_type = geom["type"]
        coordinates = geom["coordinates"]

        # Handle MultiPolygon correctly
        if geom_type == "MultiPolygon":
            return [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": polygon},
                    "properties": properties,
                }
                for polygon in coordinates
            ]

        # Handle other MultiXXX types
        return [
            {
                "type": "Feature",
                "geometry": {"type": geom_type[5:], "coordinates": coord},
                "properties": properties,
            }
            for coord in coordinates
        ]

    final_features = []

    for feature in featcol.get("features", []):
        properties = feature.get("properties", {})
        geom = feature.get("geometry")
        if not geom or "type" not in geom:
            continue

        if geom["type"].startswith("Multi"):
            # Handle all MultiXXX types
            final_features.extend(split_multigeom(geom, properties))
        else:
            # Handle single geometry types
            final_features.append(feature)

    return {"type": "FeatureCollection", "features": final_features}


### CRS Funcs ###


def _check_crs(featcol: FeatureCollection) -> None:
    """Warn the user if an invalid CRS is detected.

    Also does a rough check for one geometry, to determine if the
    coordinates are range 90/180 degree range.
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


### Geom Merging Funcs ###


def _ensure_right_hand_rule(
    coordinates: PolygonGeom,
) -> PolygonGeom:
    """Ensure the outer ring follows the right-hand rule (clockwise)."""

    def is_clockwise(ring: list[PointGeom]) -> bool:
        """Check coords are in clockwise direction."""
        return (
            sum(
                (ring[i][0] - ring[i - 1][0]) * (ring[i][1] + ring[i - 1][1])
                for i in range(len(ring))
            )
            > 0
        )

    # Validate input
    if not isinstance(coordinates[0], list) or not all(
        isinstance(pt, list) and len(pt) == 2 for pt in coordinates[0]
    ):
        raise ValueError(
            "Invalid input: coordinates[0] must be a list "
            f"of [x, y] points. Got: {coordinates[0]}"
        )

    # Ensure the first ring is the exterior ring and follows clockwise direction
    if not is_clockwise(coordinates[0]):
        coordinates[0] = coordinates[0][::-1]

    # Ensure any holes follow counter-clockwise direction
    for i in range(1, len(coordinates)):
        if is_clockwise(coordinates[i]):
            coordinates[i] = coordinates[i][::-1]

    return coordinates


def _remove_holes(polygon: list) -> list:
    """Remove holes from a polygon by keeping only the exterior ring.

    Args:
        polygon: A list of coordinate rings, where the first is the exterior
                 and subsequent ones are interior holes.

    Returns:
        list: A list containing only the exterior ring coordinates.
    """
    if not polygon:
        return []  # Return an empty list if the polygon is empty
    return polygon[0]  # Only return the exterior ring


def _create_convex_hull(points: list[PointGeom]) -> list[PointGeom]:
    """Create a convex hull from a list of polygons.

    This essentially draws a boundary around the outside of the polygons.

    Most appropriate when the boundaries are not touching (disjoint).
    """

    def cross(o: PointGeom, a: PointGeom, b: PointGeom) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    points = sorted(set(points))
    if len(points) <= 1:
        return points

    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def _polygons_disjoint(poly1: list[list[float]], poly2: list[list[float]]) -> bool:
    """Check if two polygons are disjoint.

    Test bounding boxes and edge intersections.
    """

    def bounding_box(polygon: list[list[float]]) -> tuple:
        xs, ys = zip(*polygon, strict=False)
        return min(xs), min(ys), max(xs), max(ys)

    def bounding_boxes_overlap(bb1: tuple, bb2: tuple) -> bool:
        return not (
            bb1[2] < bb2[0] or bb2[2] < bb1[0] or bb1[3] < bb2[1] or bb2[3] < bb1[1]
        )

    bb1, bb2 = bounding_box(poly1), bounding_box(poly2)
    if not bounding_boxes_overlap(bb1, bb2):
        return True

    def line_segments_intersect(p1, p2, q1, q2) -> bool:
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)

    for i in range(len(poly1)):
        p1, p2 = poly1[i], poly1[(i + 1) % len(poly1)]
        for j in range(len(poly2)):
            q1, q2 = poly2[j], poly2[(j + 1) % len(poly2)]
            if line_segments_intersect(p1, p2, q1, q2):
                return False

    return True


def _create_unary_union(polygons: list[list[list[float]]]) -> list[list[list[float]]]:
    """Create a unary union from a list of polygons.

    This merges the polygons by their boundaries exactly.
    Most appropriate when the boundaries are touching (not disjoint).
    """
    # Pure Python union implementation is non-trivial, so this is simplified:
    # Merge all coordinates into a single outer ring.
    all_points = chain.from_iterable(polygon[0] for polygon in polygons)
    return [list(set(all_points))]


def merge_polygons(featcol: FeatureCollection) -> FeatureCollection:
    """Merge multiple Polygons or MultiPolygons into a single Polygon.

    It is used to create a single polygon boundary.

    Automatically determine whether to use union (for overlapping polygons)
    or convex hull (for disjoint polygons).

    As a result of the processing, any Feature properties will be lost.

    Args:
        featcol (FeatureCollection): a FeatureCollection containing geometries.

    Returns:
        FeatureCollection: a FeatureCollection of a single Polygon.
    """
    if not featcol.get("features"):
        raise ValueError("FeatureCollection must contain at least one feature")

    polygons = []
    for feature in featcol.get("features", []):
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            polygons.append([_remove_holes(geom["coordinates"])])
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                polygons.append([_remove_holes(polygon)])

    polygons = [_ensure_right_hand_rule(polygon[0]) for polygon in polygons]

    if all(
        _polygons_disjoint(p1[0], p2[0])
        for i, p1 in enumerate(polygons)
        for p2 in polygons[i + 1 :]
    ):
        merged_coordinates = _create_convex_hull(
            list(chain.from_iterable(chain.from_iterable(polygons)))
        )
    else:
        merged_coordinates = _create_unary_union(polygons)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [merged_coordinates]},
                "properties": {},
            }
        ],
    }


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
    _check_crs(featcol)

    if not merge:
        return _normalize_featcol(featcol)
    return merge_polygons(_normalize_featcol(featcol))
