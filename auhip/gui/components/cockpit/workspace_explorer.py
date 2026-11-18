import os
from pathlib import Path
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
    QComboBox,
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

        from auhip.core.config import config
        self.workspace_selector = QComboBox()
        self.workspace_selector.setAccessibleName("Workspace to browse")
        self.workspace_selector.addItem("AUHIP project", str(Path(__file__).resolve().parents[4]))
        self.workspace_selector.addItem("Second brain", config.SECOND_BRAIN_PATH)
        self.workspace_selector.currentIndexChanged.connect(self.refresh_files)
        header_row.addWidget(self.workspace_selector)

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
        """Browse one explicit root; never mix project and second-brain paths."""
        self.file_list.clear()
        self.code_viewer.clear()
        self.file_path_lbl.setText("Choose a file")
        root_dir = self.workspace_selector.currentData()
        self._current_root = os.path.realpath(root_dir)
        self.title_lbl.setText(f"📁 Workspace ({os.path.basename(self._current_root)})")
        if not os.path.isdir(self._current_root):
            self.code_viewer.setPlainText("This workspace folder is unavailable. Choose another workspace.")
            return

        target_dirs = (["auhip", "docs", "tests"] if self.workspace_selector.currentIndex() == 0 else
                       ["data", "university", "ai_tools", "media_production", "operations", "documents", "coding"])
        found = []

        for d in target_dirs:
            full_d = os.path.join(self._current_root, d)
            if os.path.exists(full_d):
                for root, dirs, files in os.walk(full_d):
                    dirs[:] = [sub for sub in dirs if sub not in (".git", ".venv", "__pycache__", "node_modules", ".next")]
                    for f in files:
                        if f.endswith((".py", ".md", ".json", ".ts", ".tsx", ".bat")):
                            rel = os.path.relpath(os.path.join(root, f), self._current_root)
                            found.append(rel.replace("\\", "/"))

        for f in os.listdir(self._current_root):
            if not f.startswith(".") and f.endswith((".py", ".md")) and os.path.isfile(os.path.join(self._current_root, f)):
                found.insert(0, f)

        for f in sorted(found):
            icon = "📄 " if f.endswith((".py", ".ts", ".tsx")) else "📝 " if f.endswith(".md") else "⚙ "
            item = QListWidgetItem(f"{icon}{f}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.file_list.addItem(item)

    def load_file(self, file_path: str):
        """Loads and displays file content in code viewer."""
        root_dir = getattr(self, "_current_root", ".")
        clean_path = os.path.join(root_dir, file_path) if not os.path.isabs(file_path) else file_path
        clean_path = os.path.realpath(clean_path).replace("\\", "/")
        try:
            Path(clean_path).relative_to(Path(root_dir).resolve())
        except ValueError:
            self.code_viewer.setPlainText("Choose the workspace containing this file before opening it.")
            return
        rel_label = os.path.relpath(clean_path, root_dir).replace("\\", "/")
        self.file_path_lbl.setText(f"📄 {rel_label}")

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
