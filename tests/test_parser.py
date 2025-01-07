"""Test parser.parse_aoi functionality."""

import json
import warnings

import pytest

from geojson_aoi.parser import parse_aoi


def is_featcol_nested_polygon(geojson) -> bool:
    """Check if the data is a FeatureCollection with nested Polygon."""
    geojson_type = geojson["type"]
    geom_type = geojson["features"][0]["geometry"]["type"]
    if geojson_type == "FeatureCollection" and geom_type == "Polygon":
        return True
    return False


def test_polygon(polygon_geojson):
    """A single Polygon."""
    result = parse_aoi(polygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_polygon_with_holes(polygon_holes_geojson):
    """A single Polygon with holes, should remain unchanged."""
    result = parse_aoi(polygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    # We have three rings inside polygon (1 exterior, 2 interior)
    assert len(result["features"][0]["geometry"]["coordinates"]) == 3


def test_polygon_merge_with_holes(polygon_holes_geojson):
    """A single Polygon with holes, should be merged."""
    result = parse_aoi(polygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    # We have the single exterior ring remaining
    assert len(result["features"][0]["geometry"]["coordinates"]) == 1


def test_z_dimension_polygon(polygon_geojson):
    """A single Polygon, with z-dimension coord stripped out."""
    geojson_data = {
        "type": "Polygon",
        "coordinates": [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]]],
    }
    result = parse_aoi(geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert result == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": polygon_geojson,
                "properties": {},
            }
        ],
    }


def test_feature(feature_geojson):
    """A Polygon nested in a Feature."""
    result = parse_aoi(feature_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_feature_collection(featcol_geojson):
    """A Polygon nested in a Feature, inside a FeatureCollection."""
    result = parse_aoi(featcol_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_feature_collection_multiple_geoms(feature_geojson):
    """Multiple Polygon nested in Features, inside a FeatureCollection.

    Intentionally no merging in this test.
    """
    geojson_data = {
        "type": "FeatureCollection",
        "features": [feature_geojson, feature_geojson, feature_geojson],
    }
    result = parse_aoi(geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


def test_nested_geometrycollection(geomcol_geojson):
    """A GeometryCollection nested inside a FeatureCollection."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geomcol_geojson,
                "properties": {},
            }
        ],
    }
    result = parse_aoi(geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_multiple_nested_geometrycollection(geomcol_geojson):
    """Multiple GeometryCollection nested inside a FeatureCollection."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geomcol_geojson,
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": geomcol_geojson,
                "properties": {},
            },
        ],
    }
    result = parse_aoi(geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 2


# NOTE we do not support this, see the README
# def test_geometrycollection_multiple_geoms(polygon_geojson):
#     """A GeometryCollection with multiple geometries."""
#     geojson_data = {
#         "type": "GeometryCollection",
#         "geometries": [polygon_geojson, polygon_geojson, polygon_geojson],
#     }

#     result = parse_aoi(geojson_data)
#     assert is_featcol_nested_polygon(result)
#     assert len(result["features"]) == 3


def test_featcol_merge_multiple_polygons():
    """Merge multiple polygons inside a FeatureCollection."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
                },
                "properties": {},
            },
        ],
    }
    result = parse_aoi(geojson_data, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_featcol_no_merge_polygons():
    """Do not merge multiple polygons inside a FeatureCollection."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
                },
                "properties": {},
            },
        ],
    }
    result = parse_aoi(geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 2


def test_merge_multipolygon(multipolygon_geojson):
    """Merge multiple polygons inside a MultiPolygon."""
    result = parse_aoi(multipolygon_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1

    # print(json.dumps(multipolygon_geojson))
    # print("")
    # print(json.dumps(result))
    # assert False


def test_multipolygon_no_merge(multipolygon_geojson):
    """Do not merge multiple polygons inside a MultiPolygon."""
    result = parse_aoi(multipolygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


def test_multipolygon_with_holes(multipolygon_holes_geojson):
    """MultiPolygon --> Polygon, with no holes."""
    result = parse_aoi(multipolygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


def test_multipolygon_with_holes_merged(multipolygon_holes_geojson):
    """Merge multipolygon, including holes."""
    result = parse_aoi(multipolygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_invalid_input():
    """Invalud input for parse_aoi function."""
    with pytest.raises(
        ValueError, match="GeoJSON input must be a valid dict, str, or bytes"
    ):
        parse_aoi(123)

    with pytest.raises(ValueError, match="Provided GeoJSON is empty"):
        parse_aoi("{}")

    with pytest.raises(ValueError, match="The GeoJSON type must be one of:"):
        parse_aoi({"type": "Point"})


def test_file_input(tmp_path):
    """GeoJSON file input for parse_aoi function."""
    geojson_file = tmp_path / "test.geojson"
    geojson_data = {
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
    geojson_file.write_text(json.dumps(geojson_data))

    result = parse_aoi(str(geojson_file))
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_no_warnings_valid_crs():
    """Test including a valid CRS."""
    geojson_data = {
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
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
    }

    with warnings.catch_warnings(record=True) as recorded_warnings:
        result = parse_aoi(geojson_data)
    if recorded_warnings:
        raise AssertionError(
            f"Warnings should not be raised here: {recorded_warnings[0].message}"
        )

    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


def test_warnings_raised_invalid_crs():
    """Test including an invalid CRS, raising warnings."""
    geojson_data = {
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
        "crs": {"type": "name", "properties": {"name": "invalid!!"}},
    }
    with pytest.warns(UserWarning):
        parse_aoi(geojson_data)


def test_warnings_raised_invalid_coords():
    """Test including an invalid coordinates, raising warnings."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[600, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {},
            }
        ],
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
    }
    with pytest.warns(UserWarning):
        parse_aoi(geojson_data)
