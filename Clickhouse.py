import sys
import os
from datetime import datetime, timedelta
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant, QThread, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QMessageBox, QLineEdit
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsVectorLayer, QgsProject, QgsApplication
from .Clickhouse_dialog import Ui_ClickhouseDialogBase
import tempfile
import json
import re
from . import resources

import sys
import platform
import subprocess

userpc = platform.system()
if 'Linux' in userpc:
    # qgis_python_path = QgsApplication.prefixPath() + '/bin/python3'
    qgis_python_path = sys.executable
elif 'Windows' in userpc:
    # qgis_python_path = r'C:\Program Files\QGIS 3.38.0\bin\python3'
    winpath = sys.executable
    directory = os.path.dirname(winpath)
    qgis_python_path = os.path.join(directory, "python3")
# Path to get-pip.py
get_pip_path = os.path.join(os.path.dirname(__file__), 'get-pip.py')

# Download get-pip.py if it doesn't exist
if not os.path.exists(get_pip_path):
    import urllib.request
    urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', get_pip_path)

# Run get-pip.py using the QGIS Python interpreter
subprocess.check_call([qgis_python_path, get_pip_path, '--break-system-packages'])

# Define the target directory for the library installation
libs_dir = os.path.join(os.path.dirname(__file__), 'libs')

os.makedirs(libs_dir, exist_ok=True)

# Check if clickhouse-connect is already installed
if not any(os.path.exists(os.path.join(libs_dir, pkg, 'clickhouse_connect')) for pkg in os.listdir(libs_dir) if os.path.isdir(os.path.join(libs_dir, pkg))):
    # Install clickhouse-connect into the specified directory
    subprocess.check_call([qgis_python_path, '-m', 'pip', 'install', '--target=' + libs_dir, 'clickhouse-connect', '--break-system-packages'])

# Add the libs folder to the Python path
sys.path.append(libs_dir)

# Define the target directory for the library installation
libs_dir = os.path.join(os.path.dirname(__file__), 'libs')

# Add the libs folder to the Python path
sys.path.append(libs_dir)
# Add the libs folder to the Python path
# sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
import clickhouse_connect

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
        

class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, client, query, database, table, location_column, timestamp_column, column_names):
        super().__init__()
        self.client = client
        self.query = query
        self.database = database
        self.table = table
        self.location_column = location_column
        self.timestamp_column = timestamp_column
        self.column_names = column_names

    def run(self):
        try:
            result = self.client.query(self.query).result_rows

            if not result:
                QMessageBox.information(None, "No Data", "No data available for the selected criteria.")
                return

            features = []
            total_rows = len(result)

            for index, row in enumerate(result):
                # Extract location and timestamp
                location_index = self.column_names.index(self.location_column)
                timestamp_index = self.column_names.index(self.timestamp_column) if self.timestamp_column else None

                location = row[location_index]
                timestamp = row[timestamp_index] if timestamp_index is not None else None

                if not isinstance(location, tuple) or len(location) != 2:
                    QMessageBox.warning(None, "Data Error", f"Invalid location format: {location}")
                    continue

                y, x = location

                # Skip points where latitude and longitude are both 0
                if x == 0 and y == 0:
                    continue
                if x < -180 or x > 180 or y < -90 or y > 90:
                    QMessageBox.warning(None, "Data Error", f"Coordinate out of bounds: ({y}, {x})")
                    continue

                # Convert datetime objects to string
                row = list(row)
                for i, value in enumerate(row):
                    if isinstance(value, datetime):
                        row[i] = value.strftime('%Y-%m-%d %H:%M:%S')

                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [x, y]
                    },
                    "properties": {self.column_names[i]: row[i] for i in range(len(self.column_names))}
                }


                features.append(feature)
                self.progress_updated.emit((index + 1) * 100 // total_rows)

            if not features:
                QMessageBox.information(None, "No Valid Data", "No valid data to display.")
                return

            # Create GeoJSON file
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }

            # Write GeoJSON to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.geojson') as temp_file:
                json.dump(geojson, temp_file)
                temp_file_path = temp_file.name

            self.data_loaded.emit(temp_file_path)
        except Exception as e:
            QMessageBox.critical(None, "Query Error", f"Failed to display data: {e}")

class ClickhouseDialog(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface 
        self.ui = Ui_ClickhouseDialogBase()
        self.ui.setupUi(self)
        self.setup_connections()

        # Hide the progress bar initially
        self.ui.progressbar.hide()

        # Hide the password while typing
        self.ui.passwordbox.setEchoMode(QLineEdit.Password)

        # Load saved credentials if available
        self.load_credentials()

        # Disable querybox initially
        self.ui.querybox.setEnabled(False)

    def setup_connections(self):
        self.ui.Connectbutton.clicked.connect(self.connect_to_clickhouse)
        self.ui.databasebox.currentIndexChanged.connect(self.update_tables)
        self.ui.tablebox.currentIndexChanged.connect(self.update_columns)
        self.ui.displaybutton.clicked.connect(self.display_data)
        self.ui.clearbutton.clicked.connect(self.clear_filter)
        self.ui.locationbox.currentIndexChanged.connect(self.enable_querybox)

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

            # Show success message
            QMessageBox.information(self, "Connection Successful", "Connected to ClickHouse successfully!")

            # Save credentials if checkbox is checked
            if self.ui.savecredentialscheck.isChecked():
                self.save_credentials(host, port, username, password)
        except Exception as e:
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
            self.ui.timestampbox.clear()
            location_columns = [column[0] for column in columns if column[1] == 'Point']
            timestamp_columns = [column[0] for column in columns if column[1] == 'DateTime']
            self.ui.locationbox.addItems(location_columns)
            self.ui.timestampbox.addItems(timestamp_columns)
        except Exception as e:
            QMessageBox.critical(self, "Fetch Error", f"Failed to fetch columns: {e}")

    def enable_querybox(self):
        if self.ui.locationbox.currentText():
            self.ui.querybox.setEnabled(True)
        else:
            self.ui.querybox.setEnabled(False)

    def display_data(self):
        database = self.ui.databasebox.currentText()
        table = self.ui.tablebox.currentText()
        location_column = self.ui.locationbox.currentText()
        timestamp_column = self.ui.timestampbox.currentText()
        custom_query = self.ui.querybox.toPlainText().strip()

        if not database or not table or not location_column:
            QMessageBox.warning(self, "Missing Information", "Please select database, table, and location column.")
            return

        try:
            if custom_query:
                query = self.append_all_columns(custom_query)
            else:
                if timestamp_column:
                    # Calculate the timestamp for 8 hours ago
                    now = datetime.now()
                    past_8_hours = now - timedelta(hours=8)

                    # Query to get data points from the last 8 hours
                    query = f"""
                    SELECT *
                    FROM {database}.{table}
                    WHERE {timestamp_column} >= '{past_8_hours.strftime('%Y-%m-%d %H:%M:%S')}'
                    """
                else:
                    # Query to get initial 10,000 rows
                    query = f"""
                    SELECT *
                    FROM {database}.{table}
                    LIMIT 10000
                    """

            # Extract column names
            columns = self.client.query(f'DESCRIBE TABLE {database}.{table}').result_rows
            column_names = [col[0] for col in columns]

            if location_column not in column_names:
                QMessageBox.critical(self, "Column Error", "Selected location column is not present in the data.")
                return

            # Create and start the data loader thread
            self.data_loader_thread = DataLoaderThread(self.client, query, database, table, location_column, timestamp_column, column_names)
            self.data_loader_thread.data_loaded.connect(self.load_layer)
            self.data_loader_thread.progress_updated.connect(self.update_progress)
            self.data_loader_thread.start()

            # Show the progress bar
            self.ui.progressbar.setMaximum(100)
            self.ui.progressbar.setValue(0)
            self.ui.progressbar.show()
        except Exception as e:
            QMessageBox.critical(self, "Query Error", f"Failed to display data: {e}")
            self.ui.progressbar.hide()

    def update_progress(self, value):
        self.ui.progressbar.setValue(value)

    def load_layer(self, temp_file_path):
        try:
            # Load GeoJSON file into QGIS
            layer = QgsVectorLayer(temp_file_path, "Clickhouse Data", "ogr")
            if not layer.isValid():
                QMessageBox.warning(self, "Layer Error", "Failed to load GeoJSON layer.")
                self.ui.progressbar.hide()
                return

            # Add layer to QGIS project
            QgsProject.instance().addMapLayer(layer)

            # Zoom to extent of the new layer
            if layer.extent().isEmpty() is False:
                self.iface.mapCanvas().setExtent(layer.extent())
                self.iface.mapCanvas().refresh()

            QMessageBox.information(self, "Success", f"Loaded features into the map.")
        except Exception as e:
            QMessageBox.critical(self, "Layer Error", f"Failed to load layer: {e}")
        finally:
            self.ui.progressbar.hide()

    def clear_filter(self):
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

    def append_all_columns(self, custom_query):
        def is_join_clause(query, position):
            """Check if the SELECT clause at position is part of a JOIN clause."""
            # Find the substring from the start of the query to the SELECT clause
            sub_query = query[:position]
            return 'JOIN' in sub_query.upper()
        
        # Find all occurrences of SELECT in the query
        select_indices = [i for i in range(len(custom_query)) if custom_query.upper().startswith('SELECT', i)]
        
        # If no SELECT is found, return the original query
        if not select_indices:
            return custom_query

        # Start from the end to avoid index shifting issues
        for select_index in reversed(select_indices):
            # Check if the SELECT clause is part of a JOIN
            if is_join_clause(custom_query, select_index):
                continue

            # Find the next FROM keyword after the current SELECT
            from_index = custom_query.upper().find('FROM', select_index)
            if from_index != -1:
                # Find the end of the SELECT clause
                select_clause_end = from_index
                for i in range(select_index, from_index):
                    if custom_query[i] in ',(':
                        select_clause_end = i
                        break
                
                # Replace the SELECT clause with SELECT *
                custom_query = custom_query[:select_index + len('SELECT')] + ' *' + custom_query[select_clause_end:]
        
        return custom_query
