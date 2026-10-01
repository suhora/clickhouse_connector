# -*- coding: utf-8 -*-
"""Controller/state machine driving viewport-following, chunked-and-capped ClickHouse
queries as the QGIS map canvas pans/zooms.

Keeps Clickhouse.py thin: this owns the generation/staleness bookkeeping, the debounce
timer, the single-flight + pending-request coalescing, and the extentsChanged wiring.
Never touches QMessageBox or any GUI widget directly -- it reports back to
Clickhouse.py via error_occurred/busy_changed signals only.
"""

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal

from .viewport_layer import create_layer
from .viewport_query import build_linestring_query, build_query, canvas_bbox_wgs84, grid_cell_size
from .viewport_query_thread import ViewportQueryThread

DEBOUNCE_MS = 350


class ViewportStreamer(QObject):
    error_occurred = pyqtSignal(str, str)   # title, text
    busy_changed = pyqtSignal(bool)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._streaming = False
        self._generation = 0
        self._active_query_thread = None
        self._pending_refresh = False
        self._pending_request = None   # (generation, sql, params, column_names)
        self._client = None
        self._session = None
        self._layer = None
        self._layer_generation_started = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_viewport_settled)

    # -- public API -----------------------------------------------------

    def start(self, client, session):
        """session: dict with keys base_query, location_column, columns (list of
        (name, base_type) tuples, Nullable(...) already stripped), geometry_kind
        ('point' or 'linestring'), grid_rows, grid_cols, points_per_cell (grid settings
        are point-mode-only -- see viewport_query.GRID_ROWS/GRID_COLS/POINTS_PER_CELL for
        the shipped defaults, not hardcoded here; linestring mode ignores them, v1 fetches
        everything intersecting the viewport)."""
        self.stop()
        self._client = client
        self._session = session
        self._layer = create_layer(session['columns'], session.get('geometry_kind', 'point'))
        self._streaming = True
        self.iface.mapCanvas().extentsChanged.connect(self._on_extents_changed)
        self._on_viewport_settled()  # kick off the first fetch immediately

    def stop(self):
        was_streaming = self._streaming
        self._streaming = False
        if was_streaming:
            try:
                self.iface.mapCanvas().extentsChanged.disconnect(self._on_extents_changed)
            except TypeError:
                pass  # wasn't connected
        self._debounce_timer.stop()
        self._pending_refresh = False
        self._pending_request = None
        if self._active_query_thread is not None:
            self._active_query_thread.request_cancel()

    # -- viewport change handling ----------------------------------------

    def _on_extents_changed(self):
        self._debounce_timer.start(DEBOUNCE_MS)

    def _on_viewport_settled(self):
        if not self._streaming:
            return
        self._generation += 1
        gen = self._generation
        self._layer_generation_started = None

        bbox = canvas_bbox_wgs84(self.iface)
        column_names = [name for name, _ in self._session['columns']]
        geometry_kind = self._session.get('geometry_kind', 'point')

        if geometry_kind == 'linestring':
            sql, params = build_linestring_query(
                self._session['base_query'],
                self._session['location_column'],
                bbox,
            )
        else:
            grid_rows = self._session['grid_rows']
            grid_cols = self._session['grid_cols']
            points_per_cell = self._session['points_per_cell']
            cell_h, cell_w = grid_cell_size(bbox, grid_rows, grid_cols)
            sql, params = build_query(
                self._session['base_query'],
                self._session['location_column'],
                bbox, cell_h, cell_w, grid_rows, grid_cols, points_per_cell,
            )
        self._launch_or_queue(gen, sql, params, column_names)

    def _launch_or_queue(self, gen, sql, params, column_names):
        self._pending_request = (gen, sql, params, column_names)
        if self._active_query_thread is not None:
            self._pending_refresh = True
            self._active_query_thread.request_cancel()
            return
        self._start_query_thread(gen, sql, params, column_names)

    def _start_query_thread(self, gen, sql, params, column_names):
        self._pending_refresh = False
        self.busy_changed.emit(True)
        thread = ViewportQueryThread(
            self._client, sql, params, gen, column_names, self._session['location_column'],
            self._session.get('geometry_kind', 'point'),
        )
        thread.result_block.connect(self._on_result_block)
        thread.finished_ok.connect(self._on_finished_ok)
        thread.error.connect(self._on_error)
        thread.finished.connect(self._on_thread_finished)
        self._active_query_thread = thread
        thread.start()

    # -- thread signal handlers ------------------------------------------

    def _is_stale(self, gen):
        return not self._streaming or gen != self._generation

    def _on_result_block(self, gen, rows):
        if self._is_stale(gen):
            return
        if self._layer_generation_started != gen:
            # Defer clearing the previous generation's points until real new data
            # actually arrives, to avoid a blank-canvas flash while waiting.
            self._layer.truncate()
            self._layer_generation_started = gen
        self._layer.add_rows(rows)

    def _on_finished_ok(self, gen):
        if self._is_stale(gen):
            return
        if self._layer_generation_started != gen:
            # This viewport genuinely produced zero matching points (e.g. panned
            # out over open ocean) -- clear old points instead of leaving them.
            self._layer.truncate()
            self._layer_generation_started = gen

    def _on_error(self, gen, message):
        if self._is_stale(gen):
            return
        self.error_occurred.emit("Query Error", f"Failed to load viewport data: {message}")

    def _on_thread_finished(self):
        self._active_query_thread = None
        if self._pending_refresh and self._streaming:
            gen, sql, params, column_names = self._pending_request
            self._start_query_thread(gen, sql, params, column_names)
        else:
            self.busy_changed.emit(False)
