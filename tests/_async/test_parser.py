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


async def test_polygon(db, polygon_geojson):
    """A single Polygon."""
    result = await parse_aoi_async(db, polygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


async def test_polygon_with_holes(db, polygon_holes_geojson):
    """A single Polygon with holes, should remain unchanged."""
    result = await parse_aoi_async(db, polygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    # 1 exterior, 2 interior
    assert len(result["features"][0]["geometry"]["coordinates"]) == 3


async def test_polygon_merge_with_holes(db, polygon_holes_geojson):
    """A single Polygon with holes, where the holes should be removed."""
    result = await parse_aoi_async(db, polygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert len(result["features"][0]["geometry"]["coordinates"]) == 1


async def test_polygon_with_overlaps_merged(db, polygon_overlaps_geojson):
    """Merge overlapping polygons within multipolygon."""
    result = await parse_aoi_async(db, polygon_overlaps_geojson, merge=True)
    assert len(result["features"]) == 1


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
        "features": [
            {"type": "Feature", "geometry": polygon_geojson, "properties": {}}
        ],
    }


async def test_feature(db, feature_geojson):
    """A Polygon nested in a Feature."""
    result = await parse_aoi_async(db, feature_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


async def test_feature_collection(db, featcol_geojson):
    """A Polygon nested in a Feature, inside a FeatureCollection."""
    result = await parse_aoi_async(db, featcol_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


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


async def test_geometrycollection_multiple_geoms(db, polygon_geojson):
    """A GeometryCollection with multiple geometries."""
    geojson_data = {
        "type": "GeometryCollection",
        "geometries": [polygon_geojson, polygon_geojson, polygon_geojson],
    }

    result = await parse_aoi_async(db, geojson_data)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


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


async def test_merge_multipolygon(db, multipolygon_geojson):
    """Merge multiple polygons inside a MultiPolygon."""
    result = await parse_aoi_async(db, multipolygon_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1


async def test_multipolygon_no_merge(db, multipolygon_geojson):
    """Do not merge multiple polygons inside a MultiPolygon."""
    result = await parse_aoi_async(db, multipolygon_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 3


async def test_multipolygon_with_holes(db, multipolygon_holes_geojson):
    """MultiPolygon --> Polygon, with holes remaining."""
    result = await parse_aoi_async(db, multipolygon_holes_geojson)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert len(result["features"][0]["geometry"]["coordinates"]) == 3


async def test_multipolygon_with_holes_merged(db, multipolygon_holes_geojson):
    """Merge multipolygon, including holes."""
    result = await parse_aoi_async(db, multipolygon_holes_geojson, merge=True)
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert len(result["features"][0]["geometry"]["coordinates"]) == 1


async def test_feature_with_property(db, feature_with_property_geojson):
    """Test a Feature with a single property."""
    result = await parse_aoi_async(db, feature_with_property_geojson)

    for feature in result["features"]:
        assert feature["properties"] == feature_with_property_geojson["properties"]


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


async def test_geometrycollection_mixed_geoms(db, geometrycollection_mixed_geoms):
    """Polygons are extracted from a GeometryCollection, non-Polygons skipped."""
    with pytest.warns(UserWarning, match="Skipped 8 non-Polygon"):
        result = await parse_aoi_async(db, geometrycollection_mixed_geoms)

    assert is_featcol_nested_polygon(result)
    # One Polygon, plus two from the MultiPolygon
    assert len(result["features"]) == 3


async def test_featurecollection_mixed_geoms(db, featurecollection_mixed_geoms):
    """Non-Polygon Features are skipped, keeping the remaining properties."""
    with pytest.warns(UserWarning, match="Skipped 2 non-Polygon"):
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


async def test_featurecollection_multi_props(
    db,
    featurecollection_multipolygon_properties,
):
    """Test a FeatureCollection containing MultiPolygon Feature with properties."""
    result = await parse_aoi_async(db, featurecollection_multipolygon_properties)

    assert result["features"][0]["properties"] == {"id": 1}


async def test_invalid_input(db):
    """Invalid input for parse_aoi_async function."""
    with pytest.raises(
        ValueError, match="GeoJSON input must be a valid dict, str, or bytes"
    ):
        await parse_aoi_async(db, 123)

    with pytest.raises(ValueError, match="Provided GeoJSON is empty"):
        await parse_aoi_async(db, "{}")

    with pytest.raises(ValueError, match="The GeoJSON type must be one of:"):
        await parse_aoi_async(db, {"type": "Point"})

    line_featcol = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                "properties": {},
            }
        ],
    }
    with pytest.warns(UserWarning), pytest.raises(ValueError, match="No Polygon"):
        await parse_aoi_async(db, line_featcol)


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
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
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
    with pytest.warns(UserWarning, match="Unsupported coordinate system"):
        await parse_aoi_async(db, geojson_data)


async def test_no_warnings_z_coords(db):
    """A z-dimension is valid, so should not raise warnings."""
    geojson_data = {
        "type": "Polygon",
        "coordinates": [[[0, 0, 5], [1, 0, 5], [1, 1, 5], [0, 1, 5], [0, 0, 5]]],
        "crs": {"type": "name", "properties": {"name": "WGS 84"}},
    }
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        await parse_aoi_async(db, geojson_data)


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
            "properties": {"name": "urn:ogc:def:crs:EPSG::4326"},
        },
    }
    with pytest.warns(UserWarning, match="outside WGS84"):
        await parse_aoi_async(db, geojson_data)


async def test_kml_input(db):
    """Polygons are extracted from KML Placemarks, keeping the name."""
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <name>Area A</name>
          <Polygon><outerBoundaryIs><LinearRing>
            <coordinates>0,0,10 1,0,10 1,1,10 0,1,10 0,0,10</coordinates>
          </LinearRing></outerBoundaryIs></Polygon>
        </Placemark>
        <Placemark>
          <Point><coordinates>5,5</coordinates></Point>
        </Placemark>
      </Document>
    </kml>"""

    with pytest.warns(UserWarning, match="Skipped 1 non-Polygon"):
        result = await parse_aoi_async(db, kml.encode())
    assert is_featcol_nested_polygon(result)
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"] == {"name": "Area A"}
    # z-dimension is stripped
    assert result["features"][0]["geometry"]["coordinates"][0][0] == [0, 0]


async def test_kml_name_is_unescaped(db):
    """XML entities and CDATA in a Placemark name are decoded."""
    kml = """<kml xmlns="http://www.opengis.net/kml/2.2">
      <Placemark>
        <name>A &amp; B</name>
        <Polygon><outerBoundaryIs><LinearRing>
          <coordinates>0,0 1,0 1,1 0,1 0,0</coordinates>
        </LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
      <Placemark>
        <name><![CDATA[C & D]]></name>
        <Polygon><outerBoundaryIs><LinearRing>
          <coordinates>2,0 3,0 3,1 2,1 2,0</coordinates>
        </LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
    </kml>"""

    result = await parse_aoi_async(db, kml)
    names = [feature["properties"]["name"] for feature in result["features"]]
    assert names == ["A & B", "C & D"]


async def test_kml_warns_on_skipped_geometries(db):
    """Non-Polygon KML geometries are counted, including mixed dimensions."""
    kml = """<kml xmlns="http://www.opengis.net/kml/2.2">
      <Placemark>
        <MultiGeometry>
          <Polygon><outerBoundaryIs><LinearRing>
            <coordinates>0,0,10 1,0,10 1,1,10 0,1,10 0,0,10</coordinates>
          </LinearRing></outerBoundaryIs></Polygon>
          <Point><coordinates>5,5</coordinates></Point>
        </MultiGeometry>
      </Placemark>
      <Placemark>
        <LineString><coordinates>0,0 1,1</coordinates></LineString>
      </Placemark>
    </kml>"""

    with pytest.warns(UserWarning, match="Skipped 2 non-Polygon"):
        result = await parse_aoi_async(db, kml)
    assert len(result["features"]) == 1


async def test_nested_crs_merge(db, polygon_geojson):
    """A CRS on a nested geometry does not produce mixed SRIDs."""
    nested_crs = {"type": "name", "properties": {"name": "EPSG:3857"}}
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": polygon_geojson, "properties": {}},
            {
                "type": "Feature",
                "geometry": {**polygon_geojson, "crs": nested_crs},
                "properties": {},
            },
        ],
    }

    result = await parse_aoi_async(db, geojson, merge=True)
    assert len(result["features"]) == 1
    assert "crs" not in result["features"][0]["geometry"]
