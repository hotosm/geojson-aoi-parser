"""Test fixtures."""

import pytest


@pytest.fixture(scope="session")
def db():
    """Database URI."""
    # return "postgresql://aoi:dummycipassword@db:5432/aoi"
    return "dbname=test user=luke"


@pytest.fixture
def polygon_geojson():
    """Polygon."""
    return {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }


@pytest.fixture
def polygon_holes_geojson():
    """Polygon with holes."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-47.900390625, -14.944784875088372],
                [-51.591796875, -19.91138351415555],
                [-41.11083984375, -21.309846141087192],
                [-43.39599609375, -15.390135715305204],
                [-47.900390625, -14.944784875088372],
            ],
            [
                [-46.6259765625, -17.14079039331664],
                [-47.548828125, -16.804541076383455],
                [-46.23046874999999, -16.699340234594537],
                [-45.3515625, -19.31114335506464],
                [-46.6259765625, -17.14079039331664],
            ],
            [
                [-44.40673828125, -18.375379094031825],
                [-44.4287109375, -20.097206227083888],
                [-42.9345703125, -18.979025953255267],
                [-43.52783203125, -17.602139123350838],
                [-44.40673828125, -18.375379094031825],
            ],
        ],
    }


@pytest.fixture
def multipolygon_geojson():
    """MultiPolygon, three separate polygons."""
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
def multipolygon_holes_geojson():
    """MultiPolygon with holes.

    NOTE this only contains a single nested polygon with holes for testing.
    """
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [-47.900390625, -14.944784875088372],
                    [-51.591796875, -19.91138351415555],
                    [-41.11083984375, -21.309846141087192],
                    [-43.39599609375, -15.390135715305204],
                    [-47.900390625, -14.944784875088372],
                ],
                [
                    [-46.6259765625, -17.14079039331664],
                    [-47.548828125, -16.804541076383455],
                    [-46.23046874999999, -16.699340234594537],
                    [-45.3515625, -19.31114335506464],
                    [-46.6259765625, -17.14079039331664],
                ],
                [
                    [-44.40673828125, -18.375379094031825],
                    [-44.4287109375, -20.097206227083888],
                    [-42.9345703125, -18.979025953255267],
                    [-43.52783203125, -17.602139123350838],
                    [-44.40673828125, -18.375379094031825],
                ],
            ]
        ],
    }


@pytest.fixture
def polygon_overlaps_geojson():
    """Polygon with overlapping polygons"""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    [-95.35344876103062, 44.648248534472387],
                    [-95.342139435324228, 44.449983069601899],
                    [-95.025478315544717, 44.35302314349245],
                    [-94.645484971809324, 44.591900278777103],
                    [-94.677151083787265, 44.796103145261007],
                    [-95.018692720120853, 44.86668264415642],
                    [-95.35344876103062, 44.648248534472387],
                ],
                [
                    [-95.226784313118841, 44.853856436888876],
                    [-94.980241012719077, 44.74150524265962],
                    [-94.683936679211101, 44.865079524506541],
                    [-94.62512818553779, 45.06831851031248],
                    [-94.962146091588806, 45.106644979633437],
                    [-95.226784313118841, 44.853856436888876],
                ],
            ]
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
