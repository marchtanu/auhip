import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auhip.skills.organizer import list_workspace_files, read_code_file, list_unused_files


class WorkspaceExplorer(QFrame):
    """
    Interactive Workspace & Code Explorer for Cockpit Mode:
    - Left: Workspace file tree list
    - Right: Code reader window with line numbers and monospace syntax
    - Action bar: Scan Workspace, Find Unused Files, Close Explorer
    """

    close_requested = pyqtSignal()
    file_opened = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            WorkspaceExplorer {
                background: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 16px;
            }
        """)
        self._build_ui()
        self.refresh_files()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        self.title_lbl = QLabel("📁 Workspace & Code Explorer")
        self.title_lbl.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self.title_lbl.setStyleSheet("color: #0C0A09; border: none; background: transparent;")
        header_row.addWidget(self.title_lbl)

        header_row.addStretch(1)

        scan_btn = QPushButton("🔍 Scan Files")
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        scan_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #E7E5E4; }
        """)
        scan_btn.clicked.connect(self.refresh_files)
        header_row.addWidget(scan_btn)

        unused_btn = QPushButton("🧹 Find Unused")
        unused_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unused_btn.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        unused_btn.setStyleSheet("""
            QPushButton {
                background: #F0EFED;
                color: #292524;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #E7E5E4; }
        """)
        unused_btn.clicked.connect(self._find_unused)
        header_row.addWidget(unused_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #777169;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #FEE2E2; color: #DC2626; }
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        header_row.addWidget(close_btn)

        layout.addLayout(header_row)

        # ── Content Split: File List (Left) + Code Viewer (Right) ─────────────
        split_layout = QHBoxLayout()
        split_layout.setSpacing(10)

        # File list
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(240)
        self.file_list.setFont(QFont("Inter", 11))
        self.file_list.setStyleSheet("""
            QListWidget {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 10px;
                padding: 4px;
                color: #0C0A09;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #F0EFED;
            }
            QListWidget::item:selected {
                background: #292524;
                color: #FFFFFF;
            }
        """)
        self.file_list.itemClicked.connect(self._on_item_clicked)
        split_layout.addWidget(self.file_list)

        # Code viewer
        viewer_box = QVBoxLayout()
        viewer_box.setSpacing(4)

        self.file_path_lbl = QLabel("Select a file to inspect")
        self.file_path_lbl.setFont(QFont("JetBrains Mono", 10, QFont.Weight.Medium))
        self.file_path_lbl.setStyleSheet("color: #777169; border: none; background: transparent;")
        viewer_box.addWidget(self.file_path_lbl)

        self.code_viewer = QTextEdit()
        self.code_viewer.setReadOnly(True)
        self.code_viewer.setFont(QFont("Consolas", 10))
        self.code_viewer.setStyleSheet("""
            QTextEdit {
                background: #FAFAFA;
                border: 1px solid #E7E5E4;
                border-radius: 10px;
                color: #1C1917;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        viewer_box.addWidget(self.code_viewer, 1)

        split_layout.addLayout(viewer_box, 1)
        layout.addLayout(split_layout, 1)

    def refresh_files(self):
        """Scans workspace directory and populates file list."""
        self.file_list.clear()
        target_dirs = ["auhip", "docs", "tests"]
        found = []

        for d in target_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.endswith((".py", ".md", ".json")):
                            rel = os.path.relpath(os.path.join(root, f), ".")
                            found.append(rel.replace("\\", "/"))

        # Add root files
        for f in ["main.py", "PROJECT_DOCUMENTATION.md"]:
            if os.path.exists(f):
                found.insert(0, f)

        for f in sorted(found):
            icon = "📄 " if f.endswith(".py") else "📝 " if f.endswith(".md") else "⚙ "
            item = QListWidgetItem(f"{icon}{f}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.file_list.addItem(item)

    def load_file(self, file_path: str):
        """Loads and displays file content in code viewer."""
        clean_path = file_path.replace("\\", "/")
        self.file_path_lbl.setText(f"📄 {clean_path}")

        if os.path.exists(clean_path):
            try:
                with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
                    self.code_viewer.setPlainText("".join(numbered))
            except Exception as e:
                self.code_viewer.setPlainText(f"Error reading file: {e}")
        else:
            self.code_viewer.setPlainText(f"File not found: {clean_path}")

    def _on_item_clicked(self, item: QListWidgetItem):
        f = item.data(Qt.ItemDataRole.UserRole)
        if f:
            self.load_file(f)
            self.file_opened.emit(f)

    def _find_unused(self):
        import asyncio
        async def run_scan():
            result = await list_unused_files()
            self.file_path_lbl.setText("🧹 Unused Files Report")
            self.code_viewer.setPlainText(result)
        asyncio.create_task(run_scan())
