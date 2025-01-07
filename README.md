# GeoJSON AOI Parser

<!-- markdownlint-disable -->
<p align="center">
  <img src="https://github.com/hotosm/fmtm/blob/main/images/hot_logo.png?raw=true" style="width: 200px;" alt="HOT"></a>
</p>
<p align="center">
  <em>Parse and normalize a GeoJSON area of interest, using pure Python.</em>
</p>
<p align="center">
  <a href="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/docs.yml" target="_blank">
      <img src="https://github.com/hotosm/geojson-aoi-parser/workflows/Publish Docs/badge.svg" alt="Publish Docs">
  </a>
  <a href="https://github.com/hotosm/geojson-aoi-parser/actions/workflows/publish.yml" target="_blank">
      <img src="https://github.com/hotosm/geojson-aoi-parser/workflows/Publish to PyPi.org/badge.svg" alt="Publish">
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
  - Feature
  - FeatureCollection
- Handle multigeometries with an optional merge to single polygon, or split into
  featcol of individual polygons.
- Handle geometries nested inside GeometryCollection*.
- Remove any z-dimension coordinates.
- Warn user if CRS is provided, in a coordinate system other than EPSG:4326.
- **Normalised output**: FeatureCollection containing Polygon geoms.

> [!WARNING]  
> *We typically advise against using the GeometryCollection type, and support
> in this library may not be fully functional.
>
> However sometimes geometries may need to be returned wrapped in
> GeometryCollection, for example due to idiosyncrasies of PostGIS.
>
> In this scenario, we support stripping out the first geometry from inside
> each GeometryCollection object (that may be nested in a FeatureCollection).
