# -*- coding: utf-8 -*-
"""QGIS memory-layer lifecycle for the streamed viewport view: create the layer once
per Display-AIS session, then truncate/repopulate it on each viewport refresh.
"""

from qgis.PyQt.QtCore import QMetaType
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)

_INT_PREFIXES = ('Int', 'UInt')


def _field_type(base_type):
    # QMetaType.Type, not QVariant.Type -- QgsField(name, QVariant.Type) is deprecated
    # as of QGIS 3.38+ in favor of QMetaType.
    if base_type in ('Float32', 'Float64'):
        return QMetaType.Double
    if base_type.startswith(_INT_PREFIXES):
        return QMetaType.LongLong
    return QMetaType.QString  # covers DateTime/Date/String/Point/anything else


def _coerce_value(value, base_type):
    # Coercion is driven by the ClickHouse type string (already known from DESCRIBE),
    # not by round-tripping through QgsField.type() -- that can return either legacy
    # QVariant::Type or QMetaType::Type depending on QGIS version, which is exactly
    # the kind of version-fragile comparison worth avoiding.
    if value is None:
        return None
    if base_type in ('Float32', 'Float64'):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if base_type.startswith(_INT_PREFIXES):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return str(value)


def create_layer(columns, geometry_kind='point'):
    """columns: list of (name, base_type) tuples from DESCRIBE, Nullable(...) already
    stripped (see Clickhouse.py's _base_type() helper). geometry_kind: 'point' or
    'linestring' -- picks the memory layer's geometry type; add_rows() below dispatches
    the matching QgsGeometry construction. Returns a ViewportLayer."""
    qgis_geom_type = 'LineString' if geometry_kind == 'linestring' else 'Point'
    layer = QgsVectorLayer(f"{qgis_geom_type}?crs=EPSG:4326", "Clickhouse Data", "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField(name, _field_type(base_type)) for name, base_type in columns])
    layer.updateFields()
    QgsProject.instance().addMapLayer(layer)
    return ViewportLayer(layer, columns, geometry_kind)


class ViewportLayer:
    def __init__(self, layer, columns, geometry_kind='point'):
        self.layer = layer
        self._fields = layer.fields()
        self._columns = columns  # list of (name, base_type)
        self._geometry_kind = geometry_kind

    def truncate(self):
        self.layer.dataProvider().truncate()

    def add_rows(self, rows):
        """rows: list[(geom, attrs_dict)] -- geom is (x, y) in point mode, or
        list[(x, y), ...] vertices in linestring mode, both in EPSG:4326 degrees."""
        provider = self.layer.dataProvider()
        features = []
        for geom, attrs in rows:
            feature = QgsFeature(self._fields)
            if self._geometry_kind == 'linestring':
                feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in geom]))
            else:
                x, y = geom
                feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feature.setAttributes([_coerce_value(attrs.get(name), base_type) for name, base_type in self._columns])
            features.append(feature)
        provider.addFeatures(features)
        self.layer.updateExtents()
        self.layer.triggerRepaint()
