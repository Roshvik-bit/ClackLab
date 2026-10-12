"""
Sound pack management interface for importing, validating, and managing custom sound packs.
"""

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QFileDialog,
    QMessageBox, QFrame
)
from PySide6.QtCore import Signal
from ..soundpacks.pack_manager import SoundPackManager
from ..profiles.profile_manager import ProfileManager

class SoundPacksView(QWidget):
    """Interface for importing and managing mechanical keyboard sound packs."""

    pack_imported = Signal()

    def __init__(self, pack_manager: SoundPackManager, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.pack_manager = pack_manager
        self.profile_manager = profile_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("Sound Pack Manager", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        layout.addWidget(header)

        sub = QLabel("Import authentic community mechanical switch sound packs (native ClackLab or Mechvibes format).", self)
        sub.setObjectName("SubheaderLabel")
        layout.addWidget(sub)

        # 1. Action Buttons
        btn_row = QHBoxLayout()
        self.import_dir_btn = QPushButton("📁 Import Pack Folder...", self)
        self.import_dir_btn.setObjectName("PrimaryButton")
        self.import_dir_btn.clicked.connect(self._on_import_folder)
        btn_row.addWidget(self.import_dir_btn)

        self.import_zip_btn = QPushButton("📦 Import Pack (.zip)...", self)
        self.import_zip_btn.clicked.connect(self._on_import_zip)
        btn_row.addWidget(self.import_zip_btn)

        self.open_folder_btn = QPushButton("Finder: Open Soundpacks Directory", self)
        self.open_folder_btn.clicked.connect(self._on_open_finder)
        btn_row.addWidget(self.open_folder_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 2. Installed Sound Packs List
        list_group = QGroupBox("Installed Switch Sound Packs", self)
        lg_layout = QVBoxLayout(list_group)
        lg_layout.setSpacing(8)

        self.pack_list = QListWidget(list_group)
        self.pack_list.setStyleSheet("""
            QListWidget {
                background-color: #17181f;
                border: 1px solid #282c38;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #20222a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #272a38;
                color: #818cf8;
            }
        """)
        lg_layout.addWidget(self.pack_list)

        layout.addWidget(list_group)
        self.refresh_packs()

    def refresh_packs(self):
        self.pack_list.clear()
        profiles = self.profile_manager.discover_profiles()

        for p_id, prof in profiles.items():
            item_text = f"● {prof.name} (v{prof.version}) — {len(prof.down_samples)} down samples, {len(prof.up_samples)} release"
            if "assets/sounds" in prof.directory_path:
                item_text += " [Built-in]"
            else:
                item_text += " [Custom Pack]"
            item = QListWidgetItem(item_text)
            self.pack_list.addItem(item)

    def _on_import_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Sound Pack Directory")
        if dir_path:
            success, msg, report = self.pack_manager.import_from_folder(dir_path)
            if success:
                QMessageBox.information(self, "Import Successful", msg)
                self.refresh_packs()
                self.pack_imported.emit()
            else:
                QMessageBox.warning(self, "Import Failed", msg)

    def _on_import_zip(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Sound Pack Archive", "", "ZIP Archives (*.zip)")
        if file_path:
            success, msg, report = self.pack_manager.import_from_zip(file_path)
            if success:
                QMessageBox.information(self, "Import Successful", msg)
                self.refresh_packs()
                self.pack_imported.emit()
            else:
                QMessageBox.warning(self, "Import Failed", msg)

    def _on_open_finder(self):
        try:
            os.makedirs(self.pack_manager.target_dir, exist_ok=True)
            subprocess.run(["open", self.pack_manager.target_dir], check=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open Finder: {e}")
