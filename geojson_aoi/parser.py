"""Parse various AOI GeoJSON formats and normalize."""

import json
import logging
from pathlib import Path
from typing import Any, Literal

AllowedInputTypes = Literal[
    "Polygon", "MultiPolygon", "Feature", "FeatureCollection", "GeometryCollection"
]
Coordinate = float | int
PointGeom = tuple[Coordinate, Coordinate]
PolygonGeom = list[list[PointGeom]]

Properties = dict[str, Any]
Feature = dict[str, Any]
FeatureCollection = dict[str, Any]

log = logging.getLogger(__name__)


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
    """Remove the Z dimension from coordinates."""
    if isinstance(coords, list):
        if all(isinstance(coord, (list, tuple)) and len(coord) > 2 for coord in coords):
            # Only process if three elements [x, y, z]
            return [coord[:2] for coord in coords]
        # Recursively process nested lists
        return [_remove_z_dimension(coord) for coord in coords]
    return coords


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
        return [
            {
                "type": "Feature",
                "geometry": {"type": geom["type"][5:], "coordinates": coord},
                "properties": properties,
            }
            for coord in geom["coordinates"]
        ]

    final_features = []

    for feature in featcol.get("features", []):
        properties = feature["properties"]
        geom = feature["geometry"]
        if not geom or "type" not in geom:
            continue

        if geom["type"].startswith("Multi"):
            # Handle all MultiXXX types
            final_features.extend(split_multigeom(geom, properties))
        else:
            # Handle single geometry types
            final_features.append(feature)

    return {"type": "FeatureCollection", "features": final_features}


def _ensure_right_hand_rule(
    coordinates: list[list[PointGeom]],
) -> list[list[PointGeom]]:
    """Ensure the outer ring follows the right-hand rule (clockwise)."""

    def is_clockwise(ring: list[PointGeom]) -> bool:
        return (
            sum(
                (ring[i][0] - ring[i - 1][0]) * (ring[i][1] + ring[i - 1][1])
                for i in range(len(ring))
            )
            > 0
        )

    if not is_clockwise(coordinates[0]):
        coordinates[0] = coordinates[0][::-1]

    for i in range(1, len(coordinates)):  # Reverse holes to counter-clockwise
        if is_clockwise(coordinates[i]):
            coordinates[i] = coordinates[i][::-1]

    return coordinates


def _create_convex_hull(polygons: list[list[PointGeom]]) -> list[PointGeom]:
    """Create a convex hull from a list of polygons."""
    from itertools import chain

    points = list(chain.from_iterable(chain.from_iterable(polygons)))

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


# def _polygons_disjoint(poly1: list[list[float]], poly2: list[list[float]]) -> bool:
#     """Check if two polygons are disjoint.

#     Test bounding boxes and edge intersections.
#     """

#     def bounding_box(polygon: list[list[float]]) -> tuple:
#         """Compute the bounding box of a polygon."""
#         xs, ys = zip(*polygon, strict=False)
#         return min(xs), min(ys), max(xs), max(ys)

#     def bounding_boxes_overlap(bb1: tuple, bb2: tuple) -> bool:
#         """Check if two bounding boxes overlap."""
#         return not (
#             bb1[2] < bb2[0] or bb2[2] < bb1[0] or bb1[3] < bb2[1] or bb2[3] < bb1[1]
#         )

#     def line_segments_intersect(p1, p2, q1, q2) -> bool:
#         """Check if two line segments (p1->p2 and q1->q2) intersect."""

#         def ccw(a, b, c):
#             return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

#         return (
#             ccw(p1, q1, q2) != ccw(p2, q1, q2)
#             and
#             ccw(p1, p2, q1) != ccw(p1, p2, q2)
#         )

#     # Check bounding boxes
#     bb1, bb2 = bounding_box(poly1), bounding_box(poly2)
#     if not bounding_boxes_overlap(bb1, bb2):
#         return True

#     # Check for edge intersections
#     for i in range(len(poly1)):
#         p1, p2 = poly1[i], poly1[(i + 1) % len(poly1)]
#         for j in range(len(poly2)):
#             q1, q2 = poly2[j], poly2[(j + 1) % len(poly2)]
#             if line_segments_intersect(p1, p2, q1, q2):
#                 return False

#     return True


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
    return [polygon[0]]  # Only keep the exterior ring


def merge_polygons(
    featcol: FeatureCollection, dissolve_polygon: bool = False
) -> FeatureCollection:
    """Merge multiple Polygons or MultiPolygons into a single Polygon.

    It is used to create a single polygon boundary.

    Automatically determine whether to use union (for overlapping polygons)
    or convex hull (for disjoint polygons).

    Args:
        featcol: a FeatureCollection containing geometries.
        dissolve_polygon: True to dissolve polygons to single polygon.

    Returns:
        FeatureCollection: a FeatureCollection of a single Polygon.
    """
    merged_coordinates = []

    for feature in featcol.get("features", []):
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            # Remove holes from the polygon
            polygon_without_holes = _remove_holes(geom["coordinates"])
            merged_coordinates.append(_ensure_right_hand_rule(polygon_without_holes))
        elif geom["type"] == "MultiPolygon":
            # Remove holes from each polygon in the MultiPolygon
            for polygon in geom["coordinates"]:
                polygon_without_holes = _remove_holes(polygon)
                merged_coordinates.append(
                    _ensure_right_hand_rule(polygon_without_holes)
                )

    if dissolve_polygon:
        # Combine all disjoint (i.e. non-overlapping) polygons into
        # a single convex hull-like structure
        # TODO ideally do this automatically using function like _polygons_disjoint
        merged_coordinates = _create_convex_hull(merged_coordinates)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": merged_coordinates},
            }
        ],
    }


def geojson_to_featcol(geojson_obj: dict) -> FeatureCollection:
    """Enforce GeoJSON is wrapped in FeatureCollection.

    The type check is done directly from the GeoJSON to allow parsing
    from different upstream libraries (e.g. geojson_pydantic).
    """
    geojson_type = geojson_obj.get("type")

    if geojson_type == "FeatureCollection":
        log.debug("Already in FeatureCollection format, reparsing")
        features = geojson_obj.get("features", [])
    elif geojson_type == "Feature":
        log.debug("Converting Feature to FeatureCollection")
        features = [geojson_obj]
    else:
        log.debug("Converting Geometry to FeatureCollection")
        features = [{"type": "Feature", "geometry": geojson_obj, "properties": {}}]

    return {"type": "FeatureCollection", "features": features}


def parse_aoi(
    geojson_raw: str | bytes | dict, merge: bool = False
) -> FeatureCollection:
    """Parse a GeoJSON file or data struc into a normalized FeatureCollection."""
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
    if geojson_parsed is None or geojson_parsed == {}:
        raise ValueError("Provided GeoJSON is empty")

    # Convert to FeatureCollection
    featcol = geojson_to_featcol(geojson_parsed)
    if not featcol.get("features", []):
        raise ValueError("Failed parsing geojson")

    if not merge:
        return _normalize_featcol(featcol)
    return merge_polygons(_normalize_featcol(featcol))
