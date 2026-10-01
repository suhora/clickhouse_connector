# -*- coding: utf-8 -*-
"""Background thread that streams one already-built ClickHouse query per viewport
refresh and emits results block by block.

Must never construct or touch QgsFeature/QgsVectorLayer/QMessageBox itself -- those
only ever happen on the GUI thread (constructing a Qt widget from a non-GUI QThread is
undefined behavior and previously crashed this plugin outright).
"""

from datetime import datetime

from qgis.PyQt.QtCore import QThread, pyqtSignal


class ViewportQueryThread(QThread):
    # generation, list[(geom, attrs_dict)] -- geom is (x, y) in point mode, or
    # list[(x, y), ...] (vertices) in linestring mode.
    result_block = pyqtSignal(int, list)
    finished_ok = pyqtSignal(int)          # generation -- query completed, no error
    error = pyqtSignal(int, str)           # generation, message

    def __init__(self, client, sql, params, generation, column_names, location_column,
                 geometry_kind='point'):
        super().__init__()
        self.client = client
        self.sql = sql
        self.params = params
        self.generation = generation
        self.column_names = column_names
        self.location_column = location_column
        self.geometry_kind = geometry_kind
        self._cancel_requested = False

    def request_cancel(self):
        # Polled between blocks in run(); a plain bool is a single writer (GUI
        # thread) / single reader (this thread) flag, safe enough under the GIL
        # without extra locking.
        self._cancel_requested = True

    def run(self):
        try:
            with self.client.query_row_block_stream(self.sql, parameters=self.params) as stream:
                for block in stream:
                    if self._cancel_requested:
                        return
                    rows_out = self._process_block(block)
                    if rows_out:
                        self.result_block.emit(self.generation, rows_out)
            if not self._cancel_requested:
                self.finished_ok.emit(self.generation)
        except Exception as e:
            if not self._cancel_requested:
                self.error.emit(self.generation, str(e))

    def _process_block(self, block):
        out = []
        for row in block:
            if self.geometry_kind == 'linestring':
                geom = self._extract_linestring(row)
            else:
                geom = self._extract_point(row)
            if geom is None:
                continue

            row = list(row)
            for i, value in enumerate(row):
                if isinstance(value, datetime):
                    row[i] = value.strftime('%Y-%m-%d %H:%M:%S')
            attrs = {col: val for col, val in zip(self.column_names, row)}
            out.append((geom, attrs))
        return out

    def _extract_point(self, row):
        """Returns (x, y) in EPSG:4326 degrees, or None if the row has no usable point."""
        if isinstance(self.location_column, tuple):
            lat_col, lon_col = self.location_column
            y = row[self.column_names.index(lat_col)]
            x = row[self.column_names.index(lon_col)]
            if y is None or x is None:
                return None
        else:
            location_index = self.column_names.index(self.location_column)
            location = row[location_index]
            if not isinstance(location, tuple) or len(location) != 2:
                return None
            # Must match the tupleElement(col, 1/2) order used to build the bbox
            # filter in viewport_query.build_query() -- (lon, lat).
            x, y = location

        # Skip points where latitude and longitude are both 0 (ClickHouse's
        # no-value sentinel for a missing Point), and obviously invalid coordinates.
        if x == 0 and y == 0:
            return None
        if x < -180 or x > 180 or y < -90 or y > 90:
            return None
        return (x, y)

    def _extract_linestring(self, row):
        """Returns a list of (x, y) vertices in EPSG:4326 degrees, or None if the row
        has no usable line. Unlike a single Point column, a real line can legitimately
        pass through (0, 0) (equator/prime meridian) -- that's not treated as a missing-
        value sentinel here, only the length(...) >= 2 guard (also enforced at the SQL
        layer in build_linestring_query) and per-vertex range checks apply."""
        location_index = self.column_names.index(self.location_column)
        vertices = row[location_index]
        if not vertices or len(vertices) < 2:
            return None

        points = []
        for vertex in vertices:
            if not isinstance(vertex, tuple) or len(vertex) != 2:
                return None
            x, y = vertex
            if x < -180 or x > 180 or y < -90 or y > 90:
                return None
            points.append((x, y))
        return points
