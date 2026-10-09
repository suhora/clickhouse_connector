import sys
import os
from qgis.PyQt.QtCore import Qt, QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QMessageBox, QLabel, QLineEdit
from qgis.core import QgsApplication
from .Clickhouse_dialog import Ui_ClickhouseDialogBase
from .filters import FiltersPanel
from .viewport_streamer import ViewportStreamer
from .viewport_query import GRID_ROWS, GRID_COLS, POINTS_PER_CELL
import json
import re
from . import resources

import sys
import pip
import platform

# Define the target directory for the library installation
libs_dir = os.path.join(os.path.dirname(__file__), 'libs')
os.makedirs(libs_dir, exist_ok=True)

# Add the libs folder to the Python path
sys.path.append(libs_dir)

# Add the libs folder to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))

try:
    import clickhouse_connect
except:
    # Install to lib target if missing
    pip.main(['install', 'install', '--target=' + libs_dir, 'clickhouse-connect'])

class Clickhouse:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'Clickhouse_{locale}.qm')

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&Clickhouse_Connector')
        self.first_start = None

    def tr(self, message):
        """Translate using Qt translation API."""
        return QCoreApplication.translate('Clickhouse', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/clickhouse/suhora.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Clickhouse_Connector'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Clickhouse_Connector'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        if self.first_start:
            self.first_start = False
            self.dlg = ClickhouseDialog(self.iface)

        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            pass
        

def _base_type(column_type):
    if column_type.startswith('Nullable(') and column_type.endswith(')'):
        return column_type[len('Nullable('):-1]
    return column_type


class ClickhouseDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.ui = Ui_ClickhouseDialogBase()
        self.ui.setupUi(self)
        self.relayout()
        self.filters.changed.connect(self.filters_changed)
        self.setup_connections()

        # Hide the progress bar initially
        self.ui.progressbar.hide()

        # Hide the password while typing
        self.ui.passwordbox.setEchoMode(QLineEdit.Password)

        # Load saved credentials if available
        self.load_credentials()

        # Disable querybox initially
        self.ui.querybox.setEnabled(False)

        # Only show the controls for the currently selected location mode
        self.update_location_mode()

        # Grid-settings defaults -- single source of truth is viewport_query.py's
        # GRID_ROWS/GRID_COLS/POINTS_PER_CELL; the spin boxes just start there and
        # the user can change them per-session from here on.
        self.ui.gridrowsbox.setValue(GRID_ROWS)
        self.ui.gridcolsbox.setValue(GRID_COLS)
        self.ui.pointspercellbox.setValue(POINTS_PER_CELL)

        # Viewport-driven, chunked-and-capped rendering controller (see
        # viewport_streamer.py) -- keeps this dialog thin; all the
        # generation/staleness/debounce/threading state lives there.
        self.viewport_streamer = ViewportStreamer(self.iface)
        self.viewport_streamer.error_occurred.connect(self.show_thread_message)
        self.viewport_streamer.busy_changed.connect(self._set_busy)
        self.finished.connect(self._on_dialog_finished)

    def relayout(self):
        """Compact two-column layout (the .ui is fixed-position and generated, so it is rearranged here)."""
        ui, left, right, half, full = self.ui, 10, 401, 375, 766

        def put(widget, x, y, w=None):
            widget.setGeometry(x, y, w or widget.width(), widget.height())

        # credentials 2x2
        for lbl, box, x, y in ((ui.hostlabel, ui.hostbox, left, 10), (ui.portlabel, ui.portbox, right, 10),
                               (ui.usernamelabel, ui.usernamebox, left, 65),
                               (ui.passwordlabel, ui.passwordbox, right, 65)):
            put(lbl, x, y)
            put(box, x, y + 20, half)
        put(ui.savecredentialscheck, left, 125)
        put(ui.Connectbutton, left + full - ui.Connectbutton.width(), 122)
        ui.progressbar.setGeometry(left, 122, full, 31)
        # database | table
        for lbl, box, x in ((ui.databaselabel, ui.databasebox, left), (ui.tablelabel, ui.tablebox, right)):
            put(lbl, x, 165)
            put(box, x, 185, half)
        put(ui.locationmodelabel, left, 225)
        for r in (ui.pointmoderadio, ui.latlonmoderadio, ui.linestringmoderadio):
            put(r, r.x(), 245)
        # location column pickers: lat | lon side by side, point/linestring full width
        put(ui.latitudelabel, left, 280)
        put(ui.latitudebox, left, 300, half)
        put(ui.longitudelabel, right, 280)
        put(ui.longitudebox, right, 300, half)
        for lbl, box in ((ui.locationlabel, ui.locationbox), (ui.linestringlabel, ui.linestringbox)):
            put(lbl, left, 280)
            put(box, left, 300, full)
        # filters, query, grid settings, buttons
        self.status = QLabel(self)
        self.status.setGeometry(left + 200, 122, 190, 27)  # same row/height as the Connect button
        self.status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.filters = FiltersPanel(self)
        self.filters.setGeometry(left, 340, full, 165)
        put(ui.querylabel, left, 515)
        ui.querybox.setGeometry(left, 535, full, 131)
        put(ui.gridsettingslabel, left, 675)
        for i, box in enumerate((ui.gridrowsbox, ui.gridcolsbox, ui.pointspercellbox)):
            box.setGeometry(left + i * 255, 700, 246, box.height())
        put(ui.clearbutton, left, 740)
        put(ui.displaybutton, left + full - ui.displaybutton.width(), 740)
        self.resize(786, 785)

    def filters_changed(self):
        """Mirror the GUI filters into the query box (display_data uses that text verbatim)."""
        clauses = self.filters.clauses()
        database, table = self.ui.databasebox.currentText(), self.ui.tablebox.currentText()
        nl = chr(10)
        self.ui.querybox.setPlainText(
            f"SELECT * FROM {database}.{table}{nl}WHERE " + f"{nl}  AND ".join(clauses) if clauses else '')

    def setup_connections(self):
        self.ui.Connectbutton.clicked.connect(self.connect_to_clickhouse)
        self.ui.databasebox.currentIndexChanged.connect(self.update_tables)
        self.ui.tablebox.currentIndexChanged.connect(self.update_columns)
        self.ui.displaybutton.clicked.connect(self.display_data)
        self.ui.clearbutton.clicked.connect(self.clear_filter)
        self.ui.pointmoderadio.toggled.connect(self.update_location_mode)
        self.ui.latlonmoderadio.toggled.connect(self.update_location_mode)
        self.ui.linestringmoderadio.toggled.connect(self.update_location_mode)
        self.ui.locationbox.currentIndexChanged.connect(self.enable_querybox)
        self.ui.latitudebox.currentIndexChanged.connect(self.enable_querybox)
        self.ui.longitudebox.currentIndexChanged.connect(self.enable_querybox)
        self.ui.linestringbox.currentIndexChanged.connect(self.enable_querybox)

    def _on_dialog_finished(self, result):
        # ClickhouseDialog is reused across invocations (see Clickhouse.run()'s
        # first_start pattern) -- closing it only hides it, so without this the
        # viewport streamer would keep firing background queries after close.
        self.viewport_streamer.stop()

    def _set_busy(self, busy):
        if busy:
            self.ui.progressbar.setRange(0, 0)
            self.ui.progressbar.show()
            self.status.hide()  # progress bar covers this row
        else:
            self.ui.progressbar.setRange(0, 100)
            self.ui.progressbar.hide()
            self.status.show()

    def update_location_mode(self):
        is_point_mode = self.ui.pointmoderadio.isChecked()
        is_latlon_mode = self.ui.latlonmoderadio.isChecked()
        is_linestring_mode = self.ui.linestringmoderadio.isChecked()

        self.ui.locationlabel.setVisible(is_point_mode)
        self.ui.locationbox.setVisible(is_point_mode)
        self.ui.latitudelabel.setVisible(is_latlon_mode)
        self.ui.latitudebox.setVisible(is_latlon_mode)
        self.ui.longitudelabel.setVisible(is_latlon_mode)
        self.ui.longitudebox.setVisible(is_latlon_mode)
        self.ui.linestringlabel.setVisible(is_linestring_mode)
        self.ui.linestringbox.setVisible(is_linestring_mode)

        # Grid-cell capping has no effect on an uncapped linestring fetch (v1 fetches
        # everything intersecting the viewport) -- hide it rather than leave controls
        # that silently do nothing.
        self.ui.gridsettingslabel.setVisible(not is_linestring_mode)
        self.ui.gridrowsbox.setVisible(not is_linestring_mode)
        self.ui.gridcolsbox.setVisible(not is_linestring_mode)
        self.ui.pointspercellbox.setVisible(not is_linestring_mode)

        self.enable_querybox()

    def connect_to_clickhouse(self):
        host = self.ui.hostbox.text()
        port = self.ui.portbox.text()
        username = self.ui.usernamebox.text()
        password = self.ui.passwordbox.text()

        try:
            # Connect to ClickHouse
            self.client = clickhouse_connect.get_client(host=host, port=port, username=username, password=password)
            # Test the connection
            self.client.query('SELECT 1')

            # Fetch and populate databases
            databases = self.client.query('SHOW DATABASES').result_rows
            self.ui.databasebox.clear()
            self.ui.databasebox.addItems([db[0] for db in databases])

            self.status.setText("Connected to ClickHouse successfully!")
            self.status.setStyleSheet("color: green")

            # Save credentials if checkbox is checked
            if self.ui.savecredentialscheck.isChecked():
                self.save_credentials(host, port, username, password)
        except Exception as e:
            self.status.setText("")
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to ClickHouse: {e}")

    def update_tables(self):
        database = self.ui.databasebox.currentText()
        if not database:
            return
        
        try:
            # Fetch and populate tables
            tables = self.client.query(f'SHOW TABLES FROM {database}').result_rows
            self.ui.tablebox.clear()
            self.ui.tablebox.addItems([table[0] for table in tables])
        except Exception as e:
            QMessageBox.critical(self, "Fetch Error", f"Failed to fetch tables: {e}")

    def update_columns(self):
        database = self.ui.databasebox.currentText()
        table = self.ui.tablebox.currentText()
        if not database or not table:
            return
        
        try:
            # Fetch and populate columns
            columns = self.client.query(f'DESCRIBE TABLE {database}.{table}').result_rows

            self.ui.locationbox.clear()
            self.ui.latitudebox.clear()
            self.ui.longitudebox.clear()
            self.ui.linestringbox.clear()
            self.filters.set_columns([c[0] for c in columns], {c[0]: c[1] for c in columns})

            point_columns = [name for name, column_type, *_ in columns if _base_type(column_type) == 'Point']
            numeric_columns = [name for name, column_type, *_ in columns if _base_type(column_type) in ('Float32', 'Float64')]
            linestring_columns = [name for name, column_type, *_ in columns if _base_type(column_type) == 'LineString']

            self.ui.locationbox.addItems(point_columns)
            self.ui.latitudebox.addItems(numeric_columns)
            self.ui.longitudebox.addItems(numeric_columns)
            # preselect columns that look like lat / lon instead of both defaulting to the first
            for box, hints in ((self.ui.latitudebox, ('lat',)), (self.ui.longitudebox, ('lon', 'lng'))):
                box.setCurrentIndex(next((i for i, n in enumerate(numeric_columns)
                                          if any(h in n.lower() for h in hints)), 0))
            self.ui.linestringbox.addItems(linestring_columns)

            # Default to whichever mode this table actually has data for
            if point_columns:
                self.ui.pointmoderadio.setChecked(True)
            elif linestring_columns:
                self.ui.linestringmoderadio.setChecked(True)
            elif numeric_columns:
                self.ui.latlonmoderadio.setChecked(True)
            else:
                self.ui.pointmoderadio.setChecked(True)

            # Show the query that will actually be sent if the box is left empty.
            self.ui.querybox.setPlaceholderText(f"SELECT * FROM {database}.{table}")
        except Exception as e:
            QMessageBox.critical(self, "Fetch Error", f"Failed to fetch columns: {e}")

    def enable_querybox(self):
        if self.ui.pointmoderadio.isChecked():
            has_location = bool(self.ui.locationbox.currentText())
        elif self.ui.linestringmoderadio.isChecked():
            has_location = bool(self.ui.linestringbox.currentText())
        else:
            has_location = bool(self.ui.latitudebox.currentText()) and bool(self.ui.longitudebox.currentText())
        self.ui.querybox.setEnabled(has_location)

    def display_data(self):
        database = self.ui.databasebox.currentText()
        table = self.ui.tablebox.currentText()
        custom_query = self.ui.querybox.toPlainText().strip()

        if self.ui.pointmoderadio.isChecked():
            geometry_kind = 'point'
            location_column = self.ui.locationbox.currentText()
            if not database or not table or not location_column:
                QMessageBox.warning(self, "Missing Information", "Please select database, table, and location column.")
                return
        elif self.ui.linestringmoderadio.isChecked():
            geometry_kind = 'linestring'
            location_column = self.ui.linestringbox.currentText()
            if not database or not table or not location_column:
                QMessageBox.warning(self, "Missing Information", "Please select database, table, and LineString column.")
                return
        else:
            geometry_kind = 'point'
            lat_column = self.ui.latitudebox.currentText()
            lon_column = self.ui.longitudebox.currentText()
            if not database or not table or not lat_column or not lon_column:
                QMessageBox.warning(self, "Missing Information", "Please select database, table, and latitude/longitude columns.")
                return
            if lat_column == lon_column:
                QMessageBox.warning(self, "Missing Information", "Latitude and longitude columns must be different.")
                return
            location_column = (lat_column, lon_column)

        try:
            if custom_query:
                # Used verbatim -- no more forcing the SELECT list to '*'. Whatever
                # columns you ask for are what the query returns.
                base_query = custom_query.strip().rstrip(';')
            else:
                # No hardcoded LIMIT or time window here -- the viewport's per-cell
                # cap bounds how much comes back, regardless of table size.
                base_query = f"SELECT * FROM {database}.{table}"

            # Introspect the columns this query actually returns (not the whole
            # table's schema) -- a custom query that only selects a subset of
            # columns is respected, and dropping a needed lat/lon/point column is
            # caught by the validation below instead of being silently masked.
            columns = self.client.query(f'DESCRIBE TABLE ({base_query})').result_rows
            column_defs = [(col[0], _base_type(col[1])) for col in columns]
            column_names = [name for name, _ in column_defs]

            if isinstance(location_column, tuple):
                missing = [col for col in location_column if col not in column_names]
            else:
                missing = [location_column] if location_column not in column_names else []
            if missing:
                QMessageBox.critical(self, "Column Error", f"Selected location column(s) not present in the data: {', '.join(missing)}")
                return

            session = {
                'base_query': base_query,
                'location_column': location_column,
                'geometry_kind': geometry_kind,
                'columns': column_defs,
                'grid_rows': self.ui.gridrowsbox.value(),
                'grid_cols': self.ui.gridcolsbox.value(),
                'points_per_cell': self.ui.pointspercellbox.value(),
            }
            self.viewport_streamer.start(self.client, session)
        except Exception as e:
            QMessageBox.critical(self, "Query Error", f"Failed to display data: {e}")
            self.ui.progressbar.hide()

    def show_thread_message(self, title, text):
        # ViewportStreamer runs its queries on a background QThread and never
        # touches QMessageBox itself (constructing a Qt widget off the GUI thread
        # is undefined behavior and previously crashed this plugin outright) --
        # it reports errors here via a signal instead.
        QMessageBox.critical(self, title, text)

    def clear_filter(self):
        self.filters.clear()
        self.ui.querybox.clear()

    def save_credentials(self, host, port, username, password):
        credentials = {
            'host': host,
            'port': port,
            'username': username,
            'password': password
        }
        with open(os.path.join(os.path.dirname(__file__), 'credentials.json'), 'w') as f:
            json.dump(credentials, f)

    def load_credentials(self):
        credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        if os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                credentials = json.load(f)
                self.ui.hostbox.setText(credentials['host'])
                self.ui.portbox.setText(credentials['port'])
                self.ui.usernamebox.setText(credentials['username'])
                self.ui.passwordbox.setText(credentials['password'])
                self.ui.savecredentialscheck.setChecked(True)
