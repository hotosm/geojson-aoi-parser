"""Functions to normalize a GeoJSON to FeatureCollection."""

from geojson_aoi.types import (
    Feature,
    FeatureCollection,
    Geometry,
    PolygonCoords,
    Properties,
)


def normalize_featcol(featcol: FeatureCollection) -> FeatureCollection:
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


def _remove_z_dimension(coords: PolygonCoords) -> PolygonCoords:
    """Recursively remove the Z dimension from coordinates."""
    if isinstance(coords[0], (list, tuple)):
        # If the first element is a list, recurse into each sub-list
        return [_remove_z_dimension(sub_coord) for sub_coord in coords]
    else:
        # If the first element is not a list, it's a coordinate pair (x, y, z)
        return coords[:2]  # Return only [x, y]


def _multigeom_to_singlegeom(featcol: FeatureCollection) -> FeatureCollection:
    """Converts any Multi(xxx) geometry types to list of individual geometries.

    Args:
        featcol : A GeoJSON FeatureCollection of geometries.

    Returns:
        FeatureCollection: A GeoJSON FeatureCollection containing
            single geometry types only: Polygon, LineString, Point.
    """

    def split_multigeom(geom: Geometry, properties: Properties) -> list[Feature]:
        """Splits multi-geometries into individual geometries."""
        geom_type = geom["type"]
        coordinates = geom["coordinates"]

        # Handle MultiPolygon correctly
        if geom_type == "MultiPolygon":
            return [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": polygon},
                    "properties": properties,
                }
                for polygon in coordinates
            ]

        # Handle other MultiXXX types
        return [
            {
                "type": "Feature",
                "geometry": {"type": geom_type[5:], "coordinates": coord},
                "properties": properties,
            }
            for coord in coordinates
        ]

    final_features = []

    for feature in featcol.get("features", []):
        properties = feature.get("properties", {})
        geom = feature.get("geometry")
        if not geom or "type" not in geom:
            continue

        if geom["type"].startswith("Multi"):
            # Handle all MultiXXX types
            final_features.extend(split_multigeom(geom, properties))
        else:
            # Handle single geometry types
            final_features.append(feature)

    return {"type": "FeatureCollection", "features": final_features}
