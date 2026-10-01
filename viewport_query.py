# -*- coding: utf-8 -*-
"""Geo/SQL construction for viewport-driven ClickHouse queries.

Pure functions only (aside from the QGIS CRS transform) — no threading, no Qt signals.
The qgis.core import is deferred into canvas_bbox_wgs84() itself (the only function
that touches it) so the rest of this module, including build_query/build_linestring_query,
imports and runs with plain `python viewport_query.py` outside a QGIS process — see
_demo() below.
"""

GRID_ROWS = 10
GRID_COLS = 10
POINTS_PER_CELL = 100


def canvas_bbox_wgs84(iface):
    """Current map canvas extent, transformed to EPSG:4326 (WGS84 lat/lon degrees)."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    canvas = iface.mapCanvas()
    transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), wgs84, QgsProject.instance())
    return transform.transformBoundingBox(canvas.extent())


def grid_cell_size(bbox, rows=GRID_ROWS, cols=GRID_COLS):
    """(cell_height_degrees, cell_width_degrees) for the given bbox and grid shape."""
    cell_h = (bbox.yMaximum() - bbox.yMinimum()) / rows
    cell_w = (bbox.xMaximum() - bbox.xMinimum()) / cols
    return cell_h, cell_w


def build_query(base_query, location_column, bbox, cell_h, cell_w, grid_rows, grid_cols,
                 points_per_cell=POINTS_PER_CELL):
    """Wrap base_query in a bbox filter capped to points_per_cell per grid cell.

    location_column: either a str (single ClickHouse Point-typed column) or a
    (lat_col, lon_col) tuple of separate numeric columns -- same convention
    Clickhouse.py already uses elsewhere.

    grid_rows/grid_cols must be the same values used to compute cell_h/cell_w (via
    grid_cell_size) -- passed explicitly rather than re-read from a module constant so
    the degenerate-extent fallback below can never silently disagree with the caller's
    actual grid shape.

    Returns (sql, params) for client.query(sql, parameters=params) /
    client.query_row_block_stream(sql, parameters=params). params use ClickHouse's
    server-side {name:Type} query-parameter binding (confirmed against the installed
    clickhouse_connect driver) so float formatting/locale never leaks into the SQL text.
    """
    base = base_query.strip().rstrip(';')

    if isinstance(location_column, tuple):
        lat_col, lon_col = location_column
        lat_expr = f'base.{lat_col}'
        lon_expr = f'base.{lon_col}'
    else:
        # ClickHouse's Point type is Tuple(Float64, Float64) in (x, y) = (lon, lat)
        # order per its documented convention. Verify against a real Point column
        # before trusting this in production -- must stay consistent with the
        # row-unpack in viewport_query_thread.py's _process_block().
        lon_expr = f'tupleElement(base.{location_column}, 1)'
        lat_expr = f'tupleElement(base.{location_column}, 2)'

    params = {
        'min_lat': bbox.yMinimum(),
        'max_lat': bbox.yMaximum(),
        'min_lon': bbox.xMinimum(),
        'max_lon': bbox.xMaximum(),
    }
    where = (
        f"WHERE {lat_expr} BETWEEN {{min_lat:Float64}} AND {{max_lat:Float64}}\n"
        f"  AND {lon_expr} BETWEEN {{min_lon:Float64}} AND {{max_lon:Float64}}"
    )

    if cell_h > 0 and cell_w > 0:
        params['cell_h'] = cell_h
        params['cell_w'] = cell_w
        params['points_per_cell'] = points_per_cell
        # floor(), not intDiv(): intDiv's Float64 support is version-dependent in
        # ClickHouse; floor() is documented-safe on floats and works fine as a
        # LIMIT BY grouping key (only needs to be hashable/comparable, not an int).
        sql = (
            f"SELECT * FROM ({base}) AS base\n"
            f"{where}\n"
            f"LIMIT {{points_per_cell:UInt32}} BY\n"
            f"    floor(({lat_expr} - {{min_lat:Float64}}) / {{cell_h:Float64}}),\n"
            f"    floor(({lon_expr} - {{min_lon:Float64}}) / {{cell_w:Float64}})"
        )
    else:
        # Degenerate/zero-size extent (e.g. canvas hasn't painted yet) -- skip
        # per-cell bucketing, fall back to a flat cap on the whole viewport.
        sql = (
            f"SELECT * FROM ({base}) AS base\n"
            f"{where}\n"
            f"LIMIT {grid_rows * grid_cols * points_per_cell}"
        )

    return sql, params


def build_linestring_query(base_query, location_column, bbox):
    """Wrap base_query in a bbox-overlap filter for a LineString-typed column.

    Unlike build_query's per-cell point cap, a line has no single position to bucket
    into a grid cell, so v1 fetches everything whose own bounding box overlaps the
    viewport -- no LIMIT BY, no row cap (Clickhouse.py hides the grid-settings controls
    entirely in this mode, since they'd have no effect here).

    The overlap test compares the line's own arrayMin/arrayMax of its vertices against
    the viewport bbox -- the standard R-tree-style bbox prefilter. It also correctly
    matches a line that crosses the viewport without either endpoint inside it, since it
    only needs the two bboxes to overlap, not a vertex to land inside the viewport.
    Trade-off: a line whose bbox overlaps the viewport but doesn't actually cross it
    (e.g. a steep diagonal) can be an accepted false positive -- no exact segment
    clipping in v1.

    length(...) >= 2 excludes degenerate 0/1-vertex rows at the SQL layer: ClickHouse's
    arrayMin/arrayMax of an empty array default to 0 rather than erroring (confirmed
    against a live instance), which would otherwise synthesize a bogus (0,0) bbox and
    wrongly match the row whenever the viewport includes null island.

    Returns (sql, params) in the same client.query(sql, parameters=params) /
    client.query_row_block_stream(sql, parameters=params) shape as build_query().
    """
    base = base_query.strip().rstrip(';')
    col = location_column

    # ClickHouse's LineString type is Array(Point) = Array(Tuple(Float64, Float64)) in
    # (x, y) = (lon, lat) order, same convention as the Point column case in build_query
    # -- must stay consistent with the vertex unpack in viewport_query_thread.py's
    # _extract_linestring().
    lon_expr = f'arrayMap(p -> tupleElement(p, 1), base.{col})'
    lat_expr = f'arrayMap(p -> tupleElement(p, 2), base.{col})'

    params = {
        'min_lat': bbox.yMinimum(),
        'max_lat': bbox.yMaximum(),
        'min_lon': bbox.xMinimum(),
        'max_lon': bbox.xMaximum(),
    }
    where = (
        f"WHERE length(base.{col}) >= 2\n"
        f"  AND arrayMax({lon_expr}) >= {{min_lon:Float64}} AND arrayMin({lon_expr}) <= {{max_lon:Float64}}\n"
        f"  AND arrayMax({lat_expr}) >= {{min_lat:Float64}} AND arrayMin({lat_expr}) <= {{max_lat:Float64}}"
    )
    sql = f"SELECT * FROM ({base}) AS base\n{where}"
    return sql, params


def _demo():
    """Assert-based self-check for the pure SQL-building functions -- run as plain
    `python viewport_query.py`, no QGIS/pytest/unittest required."""

    class _Bbox:
        def __init__(self, min_lon, min_lat, max_lon, max_lat):
            self._min_lon, self._min_lat = min_lon, min_lat
            self._max_lon, self._max_lat = max_lon, max_lat

        def xMinimum(self): return self._min_lon
        def xMaximum(self): return self._max_lon
        def yMinimum(self): return self._min_lat
        def yMaximum(self): return self._max_lat

    bbox = _Bbox(-10.0, -5.0, 10.0, 5.0)

    # -- build_query: Point-column mode --
    cell_h, cell_w = grid_cell_size(bbox, rows=2, cols=2)
    sql, params = build_query("SELECT * FROM t", "pos", bbox, cell_h, cell_w, 2, 2, points_per_cell=50)
    assert "tupleElement(base.pos, 1)" in sql
    assert "LIMIT {points_per_cell:UInt32} BY" in sql
    assert params['min_lon'] == -10.0 and params['max_lat'] == 5.0

    # -- build_query: lat/lon-tuple mode --
    sql, params = build_query("SELECT * FROM t", ("lat", "lon"), bbox, cell_h, cell_w, 2, 2)
    assert "base.lat" in sql and "base.lon" in sql

    # -- build_query: degenerate zero-size extent falls back to a flat cap --
    sql, params = build_query("SELECT * FROM t", "pos", bbox, 0, 0, 2, 2, points_per_cell=50)
    assert "LIMIT 200" in sql and "LIMIT BY" not in sql

    # -- build_linestring_query --
    sql, params = build_linestring_query("SELECT * FROM t", "track", bbox)
    assert "length(base.track) >= 2" in sql
    assert "arrayMap(p -> tupleElement(p, 1), base.track)" in sql
    assert "LIMIT" not in sql  # v1: no cap, fetch everything intersecting the viewport
    assert params == {'min_lat': -5.0, 'max_lat': 5.0, 'min_lon': -10.0, 'max_lon': 10.0}

    print("viewport_query self-check OK")


if __name__ == "__main__":
    _demo()
