"""form_editor.py — an editable form, generated from the schema spec.

Loads a form's values via case_api.read_form(), renders one widget per field
(driven by schemas.FIELD_SPECS), and writes edits back via case_api.write_form().
Like everything else, it touches case data ONLY through the seam.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app import case_api, schemas


class FormEditor(QDialog):
    def __init__(self, case_name: str, form: str, parent=None) -> None:
        super().__init__(parent)
        self.case_name = case_name
        self.form = form
        self.setWindowTitle(f"{form.capitalize()} form  \u2014  {case_name}")
        self.resize(560, 660)

        # key -> (widget, kind)
        self._widgets: dict[str, tuple[QWidget, str]] = {}

        data = case_api.read_form(case_name, form)
        spec = schemas.FIELD_SPECS.get(form, [])

        inner = QWidget()
        inner.setObjectName("formInner")
        flay = QFormLayout(inner)
        flay.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        flay.setContentsMargins(18, 18, 18, 18)
        flay.setVerticalSpacing(10)
        flay.setHorizontalSpacing(14)

        for key, label, kind in spec:
            value = str(data.get(key, "") or "")
            if kind == "text":
                widget: QWidget = QPlainTextEdit()
                widget.setPlainText(value)
                widget.setMinimumHeight(64)
            else:
                widget = QLineEdit()
                widget.setText(value)
            self._widgets[key] = (widget, kind)
            flay.addRow(label + ":", widget)

        scroll = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        buttons.setContentsMargins(12, 8, 12, 12)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll, stretch=1)
        lay.addWidget(buttons)

    def _save(self) -> None:
        # Start from the on-disk form so schemaVersion and any unknown keys
        # are preserved, then overwrite the edited fields.
        data = case_api.read_form(self.case_name, self.form)
        for key, (widget, kind) in self._widgets.items():
            data[key] = widget.toPlainText() if kind == "text" else widget.text()
        case_api.write_form(self.case_name, self.form, data)
        self.accept()
