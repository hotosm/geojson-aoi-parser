"""Functions for Polygon merging."""

from itertools import chain

from geojson_aoi.types import FeatureCollection, PointCoords, PolygonCoords


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
        _polygons_disjoint(p1, p2)
        for i, p1 in enumerate(polygons)
        for p2 in polygons[i + 1 :]
    ):
        merged_coordinates = _create_convex_hull(list(chain.from_iterable(polygons)))
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


def _ensure_right_hand_rule(
    coordinates: PolygonCoords,
) -> PolygonCoords:
    """Ensure the outer ring follows the right-hand rule (clockwise)."""

    def is_clockwise(ring: list[PointCoords]) -> bool:
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

    # Ensure the first ring is clockwise
    if not is_clockwise(coordinates[0]):
        coordinates[0] = coordinates[0][::-1]

    # Ensure holes are counter-clockwise
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


def _create_convex_hull(points: list[PointCoords]) -> list[PointCoords]:
    """Create a convex hull from a list of polygons.

    This essentially draws a boundary around the outside of the polygons.

    Most appropriate when the boundaries are not touching (disjoint).
    """

    def cross(o: PointCoords, a: PointCoords, b: PointCoords) -> float:
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


class LineString:
    def __init__(self, coordinates: list[list[float]]):
        self.coordinates = coordinates

    def is_closed(self) -> bool:
        return self.coordinates[0] == self.coordinates[-1]

    def winding_order(self) -> str:
        # Calculate signed area to determine winding order
        area = 0
        for i in range(len(self.coordinates) - 1):
            x1, y1 = self.coordinates[i]
            x2, y2 = self.coordinates[i + 1]
            area += (x2 - x1) * (y2 + y1)
        return "clockwise" if area > 0 else "counterclockwise"


class Polygon:
    def __init__(self, exterior: LineString, interiors: list[LineString] = None):
        self.exterior = exterior
        self.interiors = interiors or []

    def rings(self):
        yield self.exterior
        yield from self.interiors


class MultiPolygon:
    def __init__(self, polygons: list[Polygon]):
        self.polygons = polygons

    def rings(self):
        for polygon in self.polygons:
            yield from polygon.rings()


class BooleanOpsCoord:
    def __init__(self, coord):
        self.coord = coord


def ring_to_shape_path(line_string: LineString) -> list[BooleanOpsCoord]:
    if not line_string.is_closed():
        raise ValueError("LineString must be closed.")

    coords = line_string.coordinates[
        :-1
    ]  # Skip the last coordinate for implicit closure
    return [BooleanOpsCoord(coord) for coord in coords]


def multi_polygon_from_shapes(shapes: list[list[list[float]]]) -> dict:
    feature_collection = {"type": "FeatureCollection", "features": []}

    for shape in shapes:
        # Ensure the first and last points are the same for each linear ring
        for ring in shape:
            if ring[0] != ring[-1]:
                ring.append(ring[0])

        feature_collection["features"].append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": shape},
                "properties": {},
            }
        )

    return feature_collection


def _create_unary_union(boppables: list[Polygon | MultiPolygon]) -> dict:
    """Create a unary union from a list of polygons.

    This merges the polygons by their boundaries exactly.
    Most appropriate when the boundaries are touching (not disjoint).
    """
    subject = []

    for boppable in boppables:
        for ring in boppable.rings():
            subject.append(ring_to_shape_path(ring))

    # Placeholder: Replace FloatOverlay and overlay logic with actual implementation
    fill_rule = (
        "positive"
        if all(
            ring.winding_order() == "clockwise"
            for boppable in boppables
            for ring in boppable.rings()
        )
        else "negative"
    )

    shapes = [[[coord.coord for coord in path] for path in subject]]

    return multi_polygon_from_shapes(shapes)
