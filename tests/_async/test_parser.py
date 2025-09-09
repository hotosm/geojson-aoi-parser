"""Test parser.parse_aoi_async functionality."""

import json
import warnings

import pytest

from geojson_aoi._async.parser import parse_aoi_async


def is_featcol_nested_polygon(geojson) -> bool:
    """Check if the data is a FeatureCollection with nested Polygon."""
    geojson_type = geojson["type"]
    geom_type = geojson["features"][0]["geometry"]["type"]
    if geojson_type == "FeatureCollection" and geom_type == "Polygon":
        return True
    return False


@pytest.mark.asyncio
async def test_polygon(db, polygon_geojson):
    """A single Polygon."""
    result = await parse_aoi_async(db, polygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_polygon_with_holes(db, polygon_holes_geojson):
    """A single Polygon with holes, should remain unchanged."""
    result = await parse_aoi_async(db, polygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    # We have three rings inside polygon (1 exterior, 2 interior)
    assert len(result["features"][0]["geometry"]["coordinates"]) == 3


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test case for future feature.")
async def test_polygon_merge_with_holes(db, polygon_holes_geojson):
    """A single Polygon with holes, where the holes should be removed."""
    result = await parse_aoi_async(db, polygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    # As we specify 'merge', only the exterior ring should be remaining
    assert len(result["features"][0]["geometry"]["coordinates"]) == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test case for future feature.")
async def test_polygon_with_overlaps_merged(db, polygon_overlaps_geojson):
    """Merge overlapping polygons within multipolygon."""
    result = await parse_aoi_async(db, polygon_overlaps_geojson, merge=True)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_z_dimension_polygon(db, polygon_geojson):
    """A single Polygon, with z-dimension coord stripped out."""
    geojson_data = {
        "type": "Polygon",
        "coordinates": [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]]],
    }
    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert result == {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "geometry": polygon_geojson}],
    }


@pytest.mark.asyncio
async def test_feature(db, feature_geojson):
    """A Polygon nested in a Feature."""
    result = await parse_aoi_async(db, feature_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_feature_collection(db, featcol_geojson):
    """A Polygon nested in a Feature, inside a FeatureCollection."""
    result = await parse_aoi_async(db, featcol_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_feature_collection_multiple_geoms(db, feature_geojson):
    """Multiple Polygon nested in Features, inside a FeatureCollection.

    Intentionally no merging in this test.
    """
    geojson_data = {
        "type": "FeatureCollection",
        "features": [feature_geojson, feature_geojson, feature_geojson],
    }
    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


@pytest.mark.asyncio
async def test_nested_geometrycollection(db, geomcol_geojson):
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
    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_multiple_nested_geometrycollection(db, geomcol_geojson):
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
    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 2


# NOTE we do not support this, see the README
# async def test_geometrycollection_multiple_geoms(polygon_geojson):
#     """A GeometryCollection with multiple geometries."""
#     geojson_data = {
#         "type": "GeometryCollection",
#         "geometries": [polygon_geojson, polygon_geojson, polygon_geojson],
#     }

#     result = parse_aoi_async(db, geojson_data)
#     assert is_featcol_nested_polygon(result)
#     assert len(result["features"]) == 3


@pytest.mark.asyncio
@pytest.mark.skip(reason="We are not doing the merge feature for now.")
async def test_featcol_merge_multiple_polygons(db):
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
    result = await parse_aoi_async(db, geojson_data, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_featcol_no_merge_polygons(db):
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
    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="We are not doing the merge feature for now.")
async def test_merge_multipolygon(db, multipolygon_geojson):
    """Merge multiple polygons inside a MultiPolygon."""
    result = await parse_aoi_async(db, multipolygon_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1

    # print(json.dumps(multipolygon_geojson))
    # print("")
    # print(json.dumps(result))
    # assert False


@pytest.mark.asyncio
async def test_multipolygon_no_merge(db, multipolygon_geojson):
    """Do not merge multiple polygons inside a MultiPolygon."""
    result = await parse_aoi_async(db, multipolygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


@pytest.mark.asyncio
async def test_multipolygon_with_holes(db, multipolygon_holes_geojson):
    """MultiPolygon --> Polygon, with holes remaining."""
    # FIXME this should not removed the holes from the polygon geom
    # FIXME Instead the polygon should simply be extrated from the MultiPolygon
    # FIXME (we only remove holes if merge=True)
    result = await parse_aoi_async(db, multipolygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="We are not doing the merge feature for now.")
async def test_multipolygon_with_holes_merged(db, multipolygon_holes_geojson):
    """Merge multipolygon, including holes."""
    result = await parse_aoi_async(db, multipolygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_feature_with_property(db, feature_with_property_geojson):
    """Test a Feature with a single property."""
    result = await parse_aoi_async(db, feature_with_property_geojson)

    for feature in result["features"]:
        print(feature)
        assert feature["properties"] == feature_with_property_geojson["properties"]


@pytest.mark.asyncio
async def test_featcol_different_properties(
    db, feature_with_property_geojson, feature_with_properties_geojson
):
    """Test a FeatureCollection with differing properties in the Features."""
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            feature_with_property_geojson,
            feature_with_properties_geojson,
        ],
    }

    result = await parse_aoi_async(db, geojson_data)

    assert (
        result["features"][0]["properties"]
        == feature_with_property_geojson["properties"]
    )
    assert (
        result["features"][1]["properties"]
        == feature_with_properties_geojson["properties"]
    )


@pytest.mark.asyncio
async def test_geometrycollection_mixed_geoms(db, geometrycollection_mixed_geoms):
    """Test a GeometryCollection that contains all kinds of geoms."""
    result = await parse_aoi_async(db, geometrycollection_mixed_geoms)

    assert result == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[40.0, 40.0], [45.0, 30.0], [20.0, 45.0], [40.0, 40.0]]
                    ],
                },
            }
        ],
    }


@pytest.mark.asyncio
async def test_featurecollection_mixed_geoms(db, featurecollection_mixed_geoms):
    """Test a FeatureCollection that contains all kinds of geoms."""
    result = await parse_aoi_async(db, featurecollection_mixed_geoms)

    assert result == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [100.0, 0.0],
                            [100.0, 1.0],
                            [101.0, 1.0],
                            [101.0, 0.0],
                            [100.0, 0.0],
                        ]
                    ],
                },
                "properties": {"prop0": "value0", "prop1": {"this": "that"}},
            }
        ],
    }


@pytest.mark.asyncio
async def test_invalid_input(db):
    """Invalud input for parse_aoi_async function."""
    with pytest.raises(
        ValueError, match="GeoJSON input must be a valid dict, str, or bytes"
    ):
        await parse_aoi_async(db, 123)

    with pytest.raises(ValueError, match="Provided GeoJSON is empty"):
        await parse_aoi_async(db, "{}")

    with pytest.raises(ValueError, match="The GeoJSON type must be one of:"):
        await parse_aoi_async(db, {"type": "Point"})


@pytest.mark.asyncio
async def test_file_input(db, tmp_path):
    """GeoJSON file input for parse_aoi_async function."""
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

    result = await parse_aoi_async(db, str(geojson_file))
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_no_warnings_valid_crs(db):
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
            "properties": {"name": "urn:ogc:async def:crs:OGC:1.3:CRS84"},
        },
    }

    with warnings.catch_warnings(record=True) as recorded_warnings:
        result = await parse_aoi_async(db, geojson_data)
    if recorded_warnings:
        raise AssertionError(
            f"Warnings should not be raised here: {recorded_warnings[0].message}"
        )

    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


@pytest.mark.asyncio
async def test_warnings_raised_invalid_crs(db):
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
        await parse_aoi_async(db, geojson_data)


@pytest.mark.asyncio
async def test_warnings_raised_invalid_coords(db):
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
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:async def:crs:EPSG::4326"},
        },
    }
    with pytest.warns(UserWarning):
        await parse_aoi_async(db, geojson_data)
