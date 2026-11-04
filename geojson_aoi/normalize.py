# Copyright (c) Humanitarian OpenStreetMap Team
# This file is part of geojson-aoi-parser.
#
#     geojson-aoi-parser is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     geojson-aoi-parser is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with geojson-aoi-parser.  If not, see <https:#www.gnu.org/licenses/>.
#
"""PostGIS queries to normalise an AOI into a FeatureCollection of Polygons.

A source query reads the input into (idx, geom, props) rows for NORMALIZE.
"""

from psycopg import sql

# A geometry level crs is dropped, as it would give each row a different SRID.
GEOJSON_SOURCE = sql.SQL("""
    SELECT
        f.idx,
        ST_GeomFromGeoJSON((f.feature -> 'geometry') - 'crs') AS geom,
        f.feature -> 'properties' AS props
    FROM (SELECT %(data)s::jsonb AS data) AS input,
    LATERAL jsonb_array_elements(
        CASE input.data ->> 'type'
            WHEN 'FeatureCollection' THEN input.data -> 'features'
            WHEN 'Feature' THEN jsonb_build_array(input.data)
            ELSE jsonb_build_array(jsonb_build_object('geometry', input.data))
        END
    ) WITH ORDINALITY AS f(feature, idx)
    WHERE jsonb_typeof(f.feature -> 'geometry') = 'object'
""")

# local-name() ignores the KML namespace version.
# Non-Polygons are read so that NORMALIZE can count them as skipped.
# ST_Force2D is needed as ST_Collect rejects mixed dimensions.
# XMLTABLE decodes entities and CDATA, unlike casting xpath() results to text.
KML_SOURCE = sql.SQL("""
    SELECT
        pm.idx,
        (
            SELECT ST_Collect(ST_Force2D(ST_GeomFromKML(node::text)))
            FROM unnest(xpath(
                '//*[local-name()="Polygon"
                    or local-name()="LineString"
                    or local-name()="Point"]',
                pm.node
            )) AS node
        ) AS geom,
        jsonb_strip_nulls(jsonb_build_object(
            'name', (
                SELECT t.name
                FROM XMLTABLE(
                    '/*/*[local-name()="name"]' PASSING pm.node
                    COLUMNS name text PATH '.'
                ) AS t
                LIMIT 1
            )
        )) AS props
    FROM unnest(
        xpath('//*[local-name()="Placemark"]', %(data)s::xml)
    ) WITH ORDINALITY AS pm(node, idx)
""")

# A union of disjoint polygons stays multi-part, so use the convex hull.
NORMALIZE = sql.SQL("""
    WITH source AS ({source}),
    dumped AS (
        SELECT idx, (d).path AS path, (d).geom AS geom, props
        FROM (SELECT idx, ST_Dump(geom) AS d, props FROM source) AS s
    ),
    polygons AS (
        SELECT idx, path, ST_Force2D(geom) AS geom, props
        FROM dumped
        WHERE ST_GeometryType(geom) = 'ST_Polygon'
    ),
    merged AS (
        SELECT ST_UnaryUnion(ST_Collect(geom)) AS geom FROM polygons
    ),
    output AS (
        SELECT idx, path, geom, props FROM polygons WHERE NOT %(merge)s
        UNION ALL
        SELECT
            1,
            '{{}}'::int[],
            CASE
                WHEN ST_NumGeometries(geom) = 1
                THEN ST_MakePolygon(ST_ExteriorRing(ST_GeometryN(geom, 1)))
                ELSE ST_ConvexHull(geom)
            END,
            NULL
        FROM merged
        WHERE %(merge)s AND geom IS NOT NULL
    )
    SELECT
        (SELECT count(*) FROM dumped) - (SELECT count(*) FROM polygons),
        (
            SELECT bool_and(
                ST_XMin(geom) >= -180 AND ST_XMax(geom) <= 180
                AND ST_YMin(geom) >= -90 AND ST_YMax(geom) <= 90
            )
            FROM polygons
        ),
        jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'type', 'Feature',
                        'geometry', ST_AsGeoJSON(ST_ForcePolygonCW(geom))::jsonb,
                        'properties', COALESCE(props, '{{}}'::jsonb)
                    )
                    ORDER BY idx, path
                ),
                '[]'::jsonb
            )
        )
    FROM output
""")
