# GeoJSON AOI Parser

<!-- markdownlint-disable -->
<p align="center">
  <img src="https://raw.githubusercontent.com/hotosm/geojson-aoi-parser/refs/heads/main/docs/images/hot_logo.png" style="width: 200px;" alt="HOT"></a>
</p>
<p align="center">
  <em>Parse and normalize a GeoJSON area of interest, using using PostGIS.</em>
</p>
<p align="center">
  <a href="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/docs.yml" target="_blank">
      <img src="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/docs.yml/badge.svg" alt="Publish Docs">
  </a>
  <a href="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/publish.yml" target="_blank">
      <img src="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/publish.yml/badge.svg" alt="Publish">
  </a>
  <a href="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/pytest.yml" target="_blank">
      <img src="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/pytest.yml/badge.svg?branch=main" alt="Test">
  </a>
  <a href="https://pypi.org/project/geojson-aoi-parser" target="_blank">
      <img src="https://img.shields.io/pypi/v/geojson-aoi-parser?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://pypistats.org/packages/geojson-aoi-parser" target="_blank">
      <img src="https://img.shields.io/pypi/dm/geojson-aoi-parser.svg" alt="Downloads">
  </a>
  <a href="https://github.com/hotosm/geojson-aoi-parser/blob/main/LICENSE.md" target="_blank">
      <img src="https://img.shields.io/github/license/hotosm/geojson-aoi-parser.svg" alt="License">
  </a>
</p>

---

📖 **Documentation**: <a href="https://hotosm.github.io/geojson-aoi-parser/" target="_blank">https://hotosm.github.io/geojson-aoi-parser/</a>

🖥️ **Source Code**: <a href="https://github.com/hotosm/geojson-aoi-parser" target="_blank">https://github.com/hotosm/geojson-aoi-parser</a>

---

<!-- markdownlint-enable -->

## Why do we need this?

- We generally need an Area of Interest (AOI) specified for software to run
  on a geospatial area.
- GeoJSON is a simple exchange format to communicate this AOI.
- We only care about Polygon data types, but GeoJSON data can be quite variable,
  with many options for presenting data.
- The goal of this package is to receive GeoJSON data in various forms, then
  produce a normalised output that can be used for further processing.

## Priorities

- **Flexible data input**: file bytes, dict, string JSON.
- **Flexible geometry input**:
  - Polygon
  - MultiPolygons
  - GeometryCollection
  - Feature
  - FeatureCollection
- Splits multipolygons into featcol of individual polygons.
- Handle geometries nested inside GeometryCollection.
- Remove any z-dimension coordinates.
- Warn user if CRS is provided, in a coordinate system other than EPSG:4326.
- **Normalised output**: FeatureCollection containing Polygon geoms.

## Capturing The Warnings

If the GeoJSON has an invalid CRS, or coordinates seem off, a warning
will be raised.

To install:

```bash
pip install geojson-aoi-parser
```

Basic example:

```python
from geojson_aoi import parse_aoi

polygon_geojson = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
    }

# Where 'db' is some upstream database connection.
feat_col = parse_aoi(db, polygon_geojson)

print(feat_col)
# {
#   'type': 'FeatureCollection',
#   'features': [
#       {
#           'type': 'Feature', 
#           'geometry': 
#               {
#                   'type': 'Polygon', 
#                   'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
#                }
#        }
#     ]
# }
```

Basic async example:

```python
from geojson_aoi import parse_aoi_async

polygon_geojson = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
    }

# Where 'db' is some upstream database connection.
feat_col = parse_aoi_async(db, polygon_geojson)

print(feat_col)
# {
#   'type': 'FeatureCollection',
#   'features': [
#       {
#           'type': 'Feature', 
#           'geometry': 
#               {
#                   'type': 'Polygon', 
#                   'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
#                }
#        }
#     ]
# }
```

To halt execution when a warning is raised and act on it:

```python
try:
    featcol = parse_aoi(raw_geojson)
except UserWarning as warning:
    log.error(warning.message)
    msg = "Using a valid CRS is mandatory!"
    log.error(msg)
    raise HTTPException(HTTPStatus.BAD_REQUEST, detail=msg)
```

To record warnings, but allow execution to continue:

```python
import warnings

with warnings.catch_warnings(record=True) as recorded_warnings:
    featcol = parse_aoi(raw_geojson)

if recorded_warnings:
    for warning in recorded_warnings:
        if isinstance(warning.message, UserWarning)
            # do stuff with warning
            logger.warning(f"A warning was encountered: {warning.message}")
```

## History

- Initially I tried to write a pure-Python implementation of this, no dependencies.
- I underestimated the amount of work that is! It could be possible to reverse
  engineer C++ Geos or georust/geos, but it's more hassle than it's worth.
- As all of the target install candidates for this package use a db driver
  anyway, I thought it wisest (and most time efficient) to use the PostGIS
  Geos implementation (specifically for the unary_union and convex_hull
  algorithms).
- An additional advantage is the potential to port this to PGLite when the
  PostGIS extension is available, meaning AOI processing easily in the browser.
