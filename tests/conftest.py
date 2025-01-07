"""Test fixtures."""

import pytest


@pytest.fixture
def polygon_geojson():
    """Polygon."""
    return {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }


@pytest.fixture
def multipolygon_geojson():
    """MultiPolygon."""
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]],  # Polygon 1
            ],
            [
                [[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]],  # Polygon 2
            ],
            [
                [[4, 4], [5, 4], [5, 5], [4, 5], [4, 4]],  # Polygon 3
            ],
        ],
    }


@pytest.fixture
def feature_geojson():
    """Feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        "properties": {},
    }


@pytest.fixture
def featcol_geojson():
    """FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {},
            }
        ],
    }


@pytest.fixture
def geomcol_geojson():
    """GeometryCollection."""
    return {
        "type": "GeometryCollection",
        "geometries": [
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            }
        ],
    }
