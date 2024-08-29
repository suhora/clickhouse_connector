# clickhouse-connector

It connects Clickhouse with QGIS, enabling seamless integration and visualization of spatial data. It retrieves records from ClickHouse that contain point information and displays them as layers in QGIS. This plugin allows users to easily manage and visualize large geospatial datasets stored in Clickhouse directly within the QGIS environment.

# Clickhouse Plugin for QGIS

Query and Visualize [Clickhouse](https://clickhouse.com/) Point data in QGIS.

**Requirements**

************
QGIS 3.10 (minimum)

**Note**

---
The code uses "—break-system-packages" to install the dependencies (try it at your own risk)

## Install

#### Install from ZIP file

The plugin can be installed using **Install from ZIP** option on the **QGIS plugin manager**.

* Download zip file from the required plugin released version.
* From the **Install from ZIP** page, select the zip file and click the **Install** button to install plugin
* It might take a few minutes to get all the required dependencies for plugin to work

#### Install from QGIS plugin repository

* Open QGIS application and open plugin manager.
* Search for `clickhouse_connector` in the All page of the plugin manager.
* From the found results, click on the `clickhouse_connector` result item and a page with plugin information will show up.
* Click the `Install Plugin` button at the bottom of the dialog to install the plugin.
