"""main_window.py — the LexiCase dashboard shell.

Build Step 3: the case-aware file browser is live. Selecting a case in the
CASES list loads its file tree in the FILE BROWSER panel — fed entirely through
app.case_api, so the UI never touches the disk directly. Double-clicking a file
opens it with the OS default app (in-app preview arrives in Step 6).

Layout:
    +--------------------------------------------------------------+
    | LexiCase            [New] [Open Case] [Export]   <date-time> |
    +-----------+--------------------------------+-----------------+
    |  CASES    |  FILE BROWSER                  |  DEADLINES      |
    | (roster)  |  --------------                |                 |
    |           |  DOCUMENT PREVIEW              |  ALERTS         |
    +-----------+--------------------------------+-----------------+
    | > ticker                                                     |
    +--------------------------------------------------------------+
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import case_api
from app.form_editor import FormEditor
from app.theme import ACTIVE, build_qss

# Files in the browser that should open the in-app form editor (not the OS app).
FORM_FILES = {"client.json": "client", "defendant.json": "defendant"}

# Image types that preview in-app (everything else opens in the OS default app).
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# Roles for stashing data on tree items.
ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_ISDIR = Qt.ItemDataRole.UserRole + 1


def panel(title: str, body: QWidget) -> QFrame:
    """Build a titled card panel wrapping a body widget."""
    frame = QFrame()
    frame.setProperty("class", "panel")
    frame.setObjectName("panel")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 12, 14, 14)
    lay.setSpacing(10)

    header = QLabel(title)
    header.setProperty("class", "panelHeader")
    lay.addWidget(header)
    lay.addWidget(body, stretch=1)
    return frame


def empty_state(text: str, big: bool = False) -> QLabel:
    """An honest placeholder describing what will live in a panel later."""
    lbl = QLabel(text)
    lbl.setProperty("class", "emptyBig" if big else "empty")
    lbl.setWordWrap(True)
    lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    return lbl


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LexiCase")
        self.resize(1180, 760)
        self.setMinimumSize(900, 560)
        self.setStyleSheet(build_qss(ACTIVE))

        self.current_case: str | None = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())
        outer.addWidget(self._build_body(), stretch=1)
        outer.addWidget(self._build_ticker())

        # Live clock.
        self._tick()
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)

        # Populate from the data layer (auto-selects the first case if any).
        self._load_roster()

    # ---- top bar -----------------------------------------------------------
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(54)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(10)

        brand = QLabel("Lexi<b>Case</b>")
        brand.setObjectName("brand")
        brand.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(brand)
        lay.addSpacing(18)

        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip("Create a new case")
        self.btn_new.clicked.connect(self._new_case)
        lay.addWidget(self.btn_new)

        self.btn_open = QPushButton("Open Case")
        self.btn_open.setToolTip("Reveal the active case folder on disk")
        self.btn_open.clicked.connect(self._reveal_case)
        lay.addWidget(self.btn_open)

        self.btn_gen = QPushButton("Generate")
        self.btn_gen.setToolTip("Generate a document from this case's data")
        self.btn_gen.clicked.connect(self._generate_doc)
        lay.addWidget(self.btn_gen)

        self.btn_export = QPushButton("Export")
        self.btn_export.setToolTip("Export this case to a .zip archive")
        self.btn_export.clicked.connect(self._export_case)
        lay.addWidget(self.btn_export)

        lay.addStretch(1)

        self.clock = QLabel("")
        self.clock.setObjectName("clock")
        lay.addWidget(self.clock)
        return bar

    def _tick(self) -> None:
        now = datetime.now()
        date_part = now.strftime("%a %d %b %Y  \u00b7  ")
        time_part = now.strftime("%I:%M:%S %p").lstrip("0")
        self.clock.setText(date_part + time_part)

    # ---- body (three panes) ------------------------------------------------
    def _build_body(self) -> QWidget:
        wrap = QWidget()
        wlay = QVBoxLayout(wrap)
        wlay.setContentsMargins(14, 14, 14, 14)

        cols = QSplitter(Qt.Orientation.Horizontal)
        cols.setHandleWidth(14)

        # --- Left: case roster (a selectable list) ---
        self.roster_list = QListWidget()
        self.roster_list.currentItemChanged.connect(self._on_case_changed)
        left = panel("CASES", self.roster_list)
        left.setMinimumWidth(190)

        # --- Center: file browser over document preview ---
        center = QSplitter(Qt.Orientation.Vertical)
        center.setHandleWidth(14)

        browser_body = QWidget()
        blay = QVBoxLayout(browser_body)
        blay.setContentsMargins(0, 0, 0, 0)
        blay.setSpacing(0)
        self.active_case_label = QLabel("No case selected")
        self.active_case_label.setProperty("class", "activeCase")
        self.browser_tree = QTreeWidget()
        self.browser_tree.setHeaderHidden(True)
        self.browser_tree.setIndentation(14)
        self.browser_tree.itemDoubleClicked.connect(self._on_file_opened)
        blay.addWidget(self.active_case_label)
        blay.addWidget(self.browser_tree, stretch=1)

        # Document preview: a real PDF viewer + a filename/page footer.
        preview_body = QWidget()
        play = QVBoxLayout(preview_body)
        play.setContentsMargins(0, 0, 0, 0)
        play.setSpacing(0)

        self.pdf_doc = QPdfDocument(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_doc)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        self.preview_hint = empty_state(
            "Generate a document, or double-click a .pdf or image in the browser, to view it here.\n\n"
            "Double-click client.json / defendant.json to edit the form instead.",
            big=True,
        )

        # Image preview (evidence photos): a scaled pixmap in a scroll area.
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_scroll = QScrollArea()
        self.image_scroll.setObjectName("formScroll")
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_label)

        self.preview_footer = QLabel("")
        self.preview_footer.setProperty("class", "activeCase")
        self.preview_footer.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Start on the hint; swap to a viewer once something is loaded.
        self.pdf_view.hide()
        self.image_scroll.hide()
        play.addWidget(self.preview_hint)
        play.addWidget(self.pdf_view, stretch=1)
        play.addWidget(self.image_scroll, stretch=1)
        play.addWidget(self.preview_footer)

        center.addWidget(panel("FILE BROWSER", browser_body))
        center.addWidget(panel("DOCUMENT PREVIEW", preview_body))
        center.setSizes([300, 320])

        # --- Right: deadlines over alerts ---
        right = QSplitter(Qt.Orientation.Vertical)
        right.setHandleWidth(14)
        right.addWidget(panel("DEADLINES", empty_state("Phase 2: upcoming deadlines, sorted by urgency.", big=True)))
        right.addWidget(panel("ALERTS", empty_state("Phase 3: incoming emails / notifications.", big=True)))
        right.setSizes([320, 300])
        right.setMinimumWidth(210)

        cols.addWidget(left)
        cols.addWidget(center)
        cols.addWidget(right)
        cols.setStretchFactor(0, 0)
        cols.setStretchFactor(1, 1)
        cols.setStretchFactor(2, 0)
        cols.setSizes([210, 640, 250])

        wlay.addWidget(cols)
        return wrap

    # ---- roster + browser logic (all via case_api) -------------------------
    def _load_roster(self, select: str | None = None) -> None:
        """Refresh the case list. Auto-selects `select`, else the first case."""
        cases = case_api.list_cases()

        self.roster_list.blockSignals(True)
        self.roster_list.clear()
        self.roster_list.addItems(cases)
        self.roster_list.blockSignals(False)

        if not cases:
            self.current_case = None
            self.active_case_label.setText("No cases yet — click New to create one")
            self.browser_tree.clear()
            return

        target = select if select in cases else cases[0]
        self.roster_list.setCurrentRow(cases.index(target))  # fires _on_case_changed

    def _on_case_changed(self, current, _previous) -> None:
        if current is None:
            return
        self._open_case(current.text())

    def _open_case(self, name: str) -> None:
        self.current_case = name
        self.active_case_label.setText("\U0001F4C1  " + name)
        self._populate_tree(name)
        self._show_preview("hint")

    def _populate_tree(self, name: str) -> None:
        self.browser_tree.clear()
        root_path = case_api.case_dir(name)
        tree = case_api.list_case_files(name)  # nested dict from the seam
        self._add_nodes(self.browser_tree.invisibleRootItem(), tree, root_path)
        self.browser_tree.expandAll()

    def _add_nodes(self, parent_item, node: dict, path) -> None:
        for child_name, child in node.items():
            is_dir = isinstance(child, dict)
            label = child_name + "/" if is_dir else child_name
            item = QTreeWidgetItem([label])
            item.setData(0, ROLE_PATH, str(path / child_name))
            item.setData(0, ROLE_ISDIR, is_dir)
            parent_item.addChild(item)
            if is_dir:
                self._add_nodes(item, child, path / child_name)

    def _on_file_opened(self, item, _column) -> None:
        """Double-click: forms -> editor, PDFs/images -> in-app preview, else OS app."""
        if item.data(0, ROLE_ISDIR):
            return
        path = item.data(0, ROLE_PATH)
        if not path:
            return
        name = Path(path).name
        ext = Path(path).suffix.lower()
        if name in FORM_FILES and self.current_case:
            self._edit_form(FORM_FILES[name])
            return
        if ext == ".pdf":
            self._preview_pdf(Path(path))
            return
        if ext in IMAGE_EXTS:
            self._preview_image(Path(path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _show_preview(self, which: str) -> None:
        """Swap the preview pane between 'hint', 'pdf', and 'image'."""
        self.preview_hint.setVisible(which == "hint")
        self.pdf_view.setVisible(which == "pdf")
        self.image_scroll.setVisible(which == "image")
        if which == "hint":
            self.preview_footer.setText("")

    def _preview_pdf(self, path: Path) -> None:
        """Render a PDF in the preview pane with a filename + page-count footer."""
        self.pdf_doc.load(str(path))
        self._show_preview("pdf")
        pages = self.pdf_doc.pageCount()
        self.preview_footer.setText(f"{path.name}   \u00b7   {pages} page{'s' if pages != 1 else ''}")

    def _preview_image(self, path: Path) -> None:
        """Render an image in the preview pane, scaled to fit the pane width."""
        pixmap = QPixmap(str(path))
        if pixmap.isNull():  # unreadable -> fall back to the OS app
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            return
        view_w = max(self.image_scroll.viewport().width() - 24, 200)
        shown = pixmap.scaledToWidth(view_w, Qt.TransformationMode.SmoothTransformation) \
            if pixmap.width() > view_w else pixmap
        self.image_label.setPixmap(shown)
        self._show_preview("image")
        self.preview_footer.setText(f"{path.name}   \u00b7   {pixmap.width()}\u00d7{pixmap.height()} px")

    def _edit_form(self, form: str) -> None:
        dlg = FormEditor(self.current_case, form, self)
        dlg.exec()

    # ---- toolbar actions ---------------------------------------------------
    def _new_case(self) -> None:
        name, ok = QInputDialog.getText(self, "New case", "Case name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if any(c in name for c in r'/\:*?"<>|'):
            QMessageBox.warning(self, "Invalid name", "A case name can't contain / \\ : * ? \" < > |")
            return
        try:
            case_api.create_case(name)
        except FileExistsError:
            QMessageBox.warning(self, "Case exists", f"A case named '{name}' already exists.")
            return
        self._load_roster(select=name)

    def _reveal_case(self) -> None:
        if not self.current_case:
            QMessageBox.information(self, "No case", "Select or create a case first.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(case_api.case_dir(self.current_case))))

    def _generate_doc(self) -> None:
        if not self.current_case:
            QMessageBox.information(self, "No case", "Select or create a case first.")
            return

        # Let the user choose which document to generate.
        templates = case_api.list_templates()           # [(id, label), ...]
        labels = [label for _id, label in templates]
        choice, ok = QInputDialog.getItem(
            self, "Generate document", "Choose a document:", labels, 0, False
        )
        if not ok:
            return
        template_id = templates[labels.index(choice)][0]

        try:
            out = case_api.generate_document(self.current_case, template_id)
        except ModuleNotFoundError as exc:
            QMessageBox.critical(
                self, "Missing dependency",
                f"{exc}\n\nRun this in your project folder, then try again:\n"
                "    pip install -r requirements.txt",
            )
            return
        except Exception as exc:  # surface any builder/disk error plainly
            QMessageBox.critical(self, "Generation failed", str(exc))
            return
        self._populate_tree(self.current_case)  # the new file appears under generated/
        self._preview_pdf(out)                   # and shows immediately in the preview pane

    def _export_case(self) -> None:
        if not self.current_case:
            QMessageBox.information(self, "No case", "Select or create a case first.")
            return
        default = str(Path.home() / f"{self.current_case}.zip")
        dest, _ = QFileDialog.getSaveFileName(self, "Export case", default, "Zip archive (*.zip)")
        if not dest:
            return
        try:
            out = case_api.export_case(self.current_case, Path(dest))
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Case exported", f"Saved to:\n{out}")

    # ---- bottom ticker -----------------------------------------------------
    def _build_ticker(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("ticker")
        bar.setFixedHeight(34)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 18, 0)
        text = QLabel("\u25b8  v1.1 \u2014 3 document types, image preview, export. Next: case roster + deadlines.")
        text.setObjectName("tickerText")
        lay.addWidget(text)
        lay.addStretch(1)
        return bar
