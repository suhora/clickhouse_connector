"""GUI attribute filters (column / operator / value rows), AND-combined into a SQL WHERE body."""
from qgis.PyQt.QtCore import QDateTime, pyqtSignal
from qgis.PyQt.QtWidgets import (QComboBox, QDateTimeEdit, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                 QScrollArea, QVBoxLayout, QWidget)


def _q(name):
    """Backtick-quote a ClickHouse identifier."""
    return '`' + name.replace('`', '``') + '`'


OPERATORS = [('= (eq)', '='), ('!= (ne)', '!='), ('> (gt)', '>'), ('>= (ge)', '>='), ('< (lt)', '<'),
             ('<= (le)', '<='), ('BETWEEN', 'BETWEEN'), ('IN (a, b, ...)', 'IN'), ('NOT IN (a, b, ...)', 'NOT IN'),
             ('LIKE', 'LIKE'), ('NOT LIKE', 'NOT LIKE'), ('IS NULL', 'IS NULL'), ('IS NOT NULL', 'IS NOT NULL')]
NO_VALUE = ('IS NULL', 'IS NOT NULL')


def _literal(value, col_type):
    """SQL literal for a user-typed value: bare if the column is numeric and the value parses, else quoted."""
    value = value.strip()
    if any(t in col_type for t in ('Int', 'Float', 'Decimal')):
        try:
            float(value)
            return value
        except ValueError:
            pass
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"


class FilterRow(QWidget):
    """One filter: column, operator, value(s) and a remove button."""
    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, cols, types):
        super().__init__()
        self.types = types
        self.col = QComboBox()
        self.col.addItems(cols)
        self.op = QComboBox()
        for label, op in OPERATORS:
            self.op.addItem(label, op)
        self.v1, self.v2 = QLineEdit(), QLineEdit()
        self.v2.setPlaceholderText('and')
        self.d1, self.d2 = QDateTimeEdit(), QDateTimeEdit()  # used instead of v1/v2 for Date/DateTime columns
        for d in (self.d1, self.d2):
            d.setCalendarPopup(True)
            d.setMinimumWidth(165)  # wide enough to show the time part
            d.setDateTime(QDateTime.currentDateTime())
            d.dateTimeChanged.connect(self.changed)
        remove = QPushButton('-')
        remove.setFixedWidth(28)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        for w in (self.col, self.op, self.v1, self.d1, self.v2, self.d2, remove):
            lay.addWidget(w)
        self.col.currentIndexChanged.connect(self.on_op)
        self.op.currentIndexChanged.connect(self.on_op)
        self.v1.textChanged.connect(self.changed)
        self.v2.textChanged.connect(self.changed)
        remove.clicked.connect(lambda: self.removed.emit(self))
        self.on_op()

    def date_kind(self):
        """'DateTime', 'Date' or None for the selected column; None for operators that need free text."""
        t = self.types.get(self.col.currentText(), '')
        if self.op.currentData() in ('IN', 'NOT IN', 'LIKE', 'NOT LIKE'):
            return None
        return 'DateTime' if 'DateTime' in t else 'Date' if 'Date' in t else None

    def on_op(self):
        op, kind = self.op.currentData(), self.date_kind()
        for d in (self.d1, self.d2):
            d.setDisplayFormat('yyyy-MM-dd' if kind == 'Date' else 'yyyy-MM-dd HH:mm:ss')
        has_value, between = op not in NO_VALUE, op == 'BETWEEN'
        self.v1.setVisible(has_value and not kind)
        self.v2.setVisible(between and not kind)
        self.d1.setVisible(has_value and bool(kind))
        self.d2.setVisible(between and bool(kind))
        self.v1.setPlaceholderText('a, b, c' if 'IN' in op and 'NULL' not in op else 'value')
        self.changed.emit()

    def value(self, i):
        """Raw text of value i (1 or 2), from the date picker when the column is a date type."""
        kind = self.date_kind()
        if kind:
            d = self.d1 if i == 1 else self.d2
            return d.dateTime().toString('yyyy-MM-dd' if kind == 'Date' else 'yyyy-MM-dd HH:mm:ss')
        return (self.v1 if i == 1 else self.v2).text().strip()

    def clause(self):
        """SQL for this filter, or None while it is incomplete."""
        col, op = self.col.currentText(), self.op.currentData()
        if not col:
            return None
        t = self.types.get(col, '')
        name = _q(col)
        if op in NO_VALUE:
            return f'{name} {op}'
        v1, v2 = self.value(1), self.value(2)
        if not v1 or (op == 'BETWEEN' and not v2):
            return None
        if op == 'BETWEEN':
            return f'{name} BETWEEN {_literal(v1, t)} AND {_literal(v2, t)}'
        if 'IN' in op.split():
            return f"{name} {op} ({', '.join(_literal(v, t) for v in v1.split(',') if v.strip())})"
        return f'{name} {op} {_literal(v1, t)}'


class FiltersPanel(QWidget):
    """Label + scrolling list of FilterRows + '+ Add Filter' button."""
    changed = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.cols, self.types, self.rows = [], {}, []
        self.rows_lay = QVBoxLayout()
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        self.rows_lay.addStretch()
        inner = QWidget()
        inner.setLayout(self.rows_lay)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        add = QPushButton('+ Add Filter')
        add.clicked.connect(self.add_row)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel('Filters (combined with AND)'))
        lay.addWidget(scroll)
        lay.addWidget(add)

    def set_columns(self, cols, types):
        """New table selected: drop old filters and use its columns."""
        self.clear()
        self.cols, self.types = cols, types

    def clear(self):
        for row in list(self.rows):
            self.remove_row(row)

    def add_row(self):
        if not self.cols:
            return
        row = FilterRow(self.cols, self.types)
        row.changed.connect(self.changed)
        row.removed.connect(self.remove_row)
        self.rows_lay.insertWidget(self.rows_lay.count() - 1, row)
        self.rows.append(row)

    def remove_row(self, row):
        self.rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self.changed.emit()

    def clauses(self):
        """SQL for each complete filter."""
        return [c for c in (r.clause() for r in self.rows) if c]
