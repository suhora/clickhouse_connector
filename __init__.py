# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Clickhouse
                                 A QGIS plugin
 This Plugin connects to Clickhouse
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-08-23
        copyright            : (C) 2024 by harsh
        email                : harsh.goyal@suhora.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Clickhouse class from file Clickhouse.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Clickhouse import Clickhouse
    return Clickhouse(iface)
