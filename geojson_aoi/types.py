"""Types for use in this package."""

from typing import Any

# Coordinates
Coordinate = float | int
PointCoords = tuple[Coordinate, Coordinate]
PolygonCoords = list[list[PointCoords]]

# GeoJSON
Geometry = dict[str, Any]
Properties = dict[str, Any]

# Features
Feature = dict[str, Any]
FeatureCollection = dict[str, Any]
