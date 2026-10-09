# clickhouse-connector

It connects Clickhouse with QGIS, enabling seamless integration and visualization of spatial data. It retrieves records from ClickHouse — a native `Point` column, separate latitude/longitude columns, or a native `LineString` column — and displays them as a live, continuously-refreshing layer in QGIS as you pan and zoom. This plugin allows users to easily manage and visualize large geospatial datasets stored in Clickhouse directly within the QGIS environment.

# Clickhouse Plugin for QGIS

Query and Visualize [Clickhouse](https://clickhouse.com/) geospatial data in QGIS.

**Requirements**

************
QGIS 3.34 LTR (tested; earlier 3.x versions not verified)
- Tested successfully in 3.44.15

**Important Note**

---
 - The code uses "—break-system-packages" to install the dependencies (try it at your own risk).
 - **Location Data Type**: choose how your table stores position data before clicking Display AIS —
   - **Point Column**: a native ClickHouse `Point` column.
   - **Lat/Lon Columns**: two separate numeric (`Float32`/`Float64`) columns; pick which is latitude and which is longitude.
   - **LineString Column**: a native ClickHouse `LineString` column, rendered as a line layer instead of points.
 - **Viewport-driven rendering**: Display AIS doesn't load the whole result set at once.
   - In Point/Lat-Lon mode, it splits the current map view into a grid and fetches up to a capped number of points per grid cell, so the total number of rendered points stays bounded no matter how large the table is. Grid rows, columns, and points-per-cell are adjustable from the **Grid Settings** row (defaults: 100 rows, 100 columns, 3 points per cell). Recommended to use <200k capped points overall.
   - In LineString mode, grid-cell capping doesn't apply to lines (a line has no single position to bucket into a cell), so the **Grid Settings** row is hidden and v1 fetches every line whose bounding box overlaps the viewport, uncapped — a pathologically large table of huge lines can mean a slow/heavy fetch.
   - Either way, as you pan or zoom the query automatically refreshes to match the new view.
 - **Connection**: enter host, port, username and password, then click **Connect**. A green status line next to the button confirms success (failures show an error popup). Tick **Save Database Credentials** to remember them, including the password, which is stored unencrypted. Once connected, pick the database and table from the dropdowns; Lat/Lon pickers preselect columns named like `lat` / `lon`.
 - **Filters**: click **+ Add Filter** to filter without writing SQL. Each row is a column, an operator and a value.
   - Operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `BETWEEN`, `IN` / `NOT IN` (comma-separated values), `LIKE` / `NOT LIKE`, `IS NULL`, `IS NOT NULL`.
   - Date / DateTime columns use a date-time picker (calendar popup; click the hour/minute/second part to edit the time). Timestamps are interpreted in the column's timezone, or the server's if it has none.
   - All filters are combined with `AND`; incomplete rows are ignored. The **Basic Query Tool** box is rewritten as `SELECT * FROM database.table WHERE ...` whenever filters change, so edit the SQL after setting filters (a later filter change overwrites manual edits). **Clear Query** removes the filters too. Filters reset when you pick a different table.
 - By default, before the per-cell cap is applied, the query is simply `SELECT * FROM database.table` — shown as placeholder text in the Basic Query Tool box once a table is selected. Type your own query there (e.g. to filter by time range or any other column) to use that instead — it still composes with the viewport grid/cap.
   - A very zoomed-out view (e.g. the whole world) still has to check every candidate row against the current viewport, so it can be noticeably slower than a zoomed-in view. May be able to resolve with a spatial index in the DB.
## Install

#### Install from ZIP file

The plugin can be installed using **Install from ZIP** option on the **QGIS plugin manager**.

* Download zip file from the required plugin released version.
* From the **Install from ZIP** page, select the zip file and click the **Install** button to install plugin
* It might take a few minutes to get all the required dependencies for plugin to work

#### Install from QGIS plugin repository in experimental plugins

* Open QGIS application and open plugin manager.
* Search for `clickhouse_connector` in the All page of the plugin manager.
* From the found results, click on the `clickhouse_connector` result item and a page with plugin information will show up.
* Click the `Install Plugin` button at the bottom of the dialog to install the plugin.
