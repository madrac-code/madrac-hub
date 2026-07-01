"""QAbstractTableModel wrapping SubtitleDocument (no editing logic, pure bridge)."""

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor

from ...utils.editor_model import SubtitleDocument, SubtitleEntry
from ..i18n import _

_COLUMNS = [_("#"), _("Inicio"), _("Fin"), _("Duracion"), _("Texto")]

_DISABLED_BG = QColor(240, 240, 240)


def _ms_to_str(ms: int) -> str:
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    r = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"


def _parse_ms(value: str) -> int:
    import re
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", value.strip())
    if not m:
        return -1
    return (int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])) * 1000 + int(m[4])


def _dur_str(ms: int) -> str:
    s = ms / 1000.0
    return f"{s:.1f}s"


class SubtitleTableModel(QAbstractTableModel):
    beforeEdit = Signal()

    def __init__(self, doc: SubtitleDocument, parent=None):
        super().__init__(parent)
        self._doc = doc

    @property
    def doc(self) -> SubtitleDocument:
        return self._doc

    def reset_from_doc(self, doc: SubtitleDocument) -> None:
        self.beginResetModel()
        self._doc = doc
        self.endResetModel()

    # ── Qt model interface ────────────────────────────────────────────

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self._doc.count() if not parent.isValid() else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 5 if not parent.isValid() else 0

    def headerData(self, section: int, orientation, role: int = Qt.DisplayRole):
        if orientation != Qt.Horizontal or role != Qt.DisplayRole:
            return None
        return _COLUMNS[section] if section < len(_COLUMNS) else None

    def flags(self, index: QModelIndex) -> int:
        if not index.isValid():
            return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (1, 2, 4):
            return base | Qt.ItemIsEditable
        return base

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        e = self._entry_at(index)
        if not e:
            return None
        col = index.column()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._format_col(e, col)
        if role == Qt.BackgroundRole and col in (0, 3):
            return _DISABLED_BG
        if role == Qt.UserRole:
            return e.index
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        e = self._entry_at(index)
        if not e:
            return False
        col = index.column()
        self.beforeEdit.emit()
        if col == 1:
            ms = _parse_ms(str(value))
            if ms < 0 or ms >= e.end_ms:
                return False
            e.start_ms = ms
            self._doc.modified = True
            self._emit_row_changed(index)
            return True
        if col == 2:
            ms = _parse_ms(str(value))
            if ms <= e.start_ms or ms < 0:
                return False
            e.end_ms = ms
            self._doc.modified = True
            self._emit_row_changed(index)
            return True
        if col == 4:
            e.text = str(value)
            self._doc.modified = True
            self._emit_row_changed(index)
            return True
        return False

    # ── helpers ───────────────────────────────────────────────────────

    def _entry_at(self, index: QModelIndex) -> SubtitleEntry | None:
        row = index.row()
        if 0 <= row < len(self._doc.entries):
            return self._doc.entries[row]
        return None

    def _format_col(self, e: SubtitleEntry, col: int) -> str:
        if col == 0:
            return str(e.index)
        if col == 1:
            return _ms_to_str(e.start_ms)
        if col == 2:
            return _ms_to_str(e.end_ms)
        if col == 3:
            return _dur_str(e.duration_ms())
        if col == 4:
            return e.text
        return ""

    def _emit_row_changed(self, index: QModelIndex) -> None:
        self.dataChanged.emit(index.siblingAtColumn(0), index.siblingAtColumn(4))
