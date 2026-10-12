"""
Switch Library displaying rich cards for Linear, Tactile, Clicky, Silent, Thocky, and Creamy switches.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from typing import Dict, List
from ..models import SwitchProfile
from ..profiles.switch_profiles import BUILTIN_PROFILES

class SwitchCard(QFrame):
    """Card representing an individual mechanical switch profile."""

    select_requested = Signal(str)
    preview_requested = Signal(str)

    def __init__(self, profile_id: str, name: str, tag: str, description: str, parent=None):
        super().__init__(parent)
        self.profile_id = profile_id
        self.is_active = False

        self.setFixedHeight(180)
        self.setObjectName("SwitchCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header: Name + Tag badge
        top_row = QHBoxLayout()
        name_label = QLabel(name, self)
        name_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")
        top_row.addWidget(name_label)
        top_row.addStretch()

        tag_badge = QLabel(tag, self)
        tag_badge.setStyleSheet("""
            background-color: #2e2640;
            color: #c084fc;
            padding: 3px 8px;
            border-radius: 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        top_row.addWidget(tag_badge)
        layout.addLayout(top_row)

        # Description
        desc_label = QLabel(description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc_label)

        layout.addStretch()

        # Action Buttons Row
        actions_row = QHBoxLayout()
        
        self.preview_btn = QPushButton("▶ Test Sound", self)
        self.preview_btn.setFixedHeight(30)
        self.preview_btn.clicked.connect(lambda: self.preview_requested.emit(self.profile_id))
        actions_row.addWidget(self.preview_btn)

        actions_row.addStretch()

        self.select_btn = QPushButton("Select Switch", self)
        self.select_btn.setFixedHeight(30)
        self.select_btn.setObjectName("PrimaryButton")
        self.select_btn.clicked.connect(lambda: self.select_requested.emit(self.profile_id))
        actions_row.addWidget(self.select_btn)

        layout.addLayout(actions_row)
        self.set_active_state(False)

    def set_active_state(self, active: bool):
        self.is_active = active
        if active:
            self.setStyleSheet("""
                QFrame#SwitchCard {
                    background-color: #1a1e2e;
                    border: 2px solid #6366f1;
                    border-radius: 12px;
                }
            """)
            self.select_btn.setText("✓ ACTIVE")
            self.select_btn.setEnabled(False)
            self.select_btn.setStyleSheet("background-color: #10b981; border: 1px solid #34d399; color: #ffffff; font-weight: 800;")
        else:
            self.setStyleSheet("""
                QFrame#SwitchCard {
                    background-color: #17181e;
                    border: 1px solid #282c37;
                    border-radius: 12px;
                }
                QFrame#SwitchCard:hover {
                    border-color: #4338ca;
                    background-color: #1c1e26;
                }
            """)
            self.select_btn.setText("Select Switch")
            self.select_btn.setEnabled(True)
            self.select_btn.setStyleSheet("")

class SwitchLibraryView(QWidget):
    """Grid catalog for browsing and selecting switch profiles."""

    profile_selected = Signal(str)
    preview_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: Dict[str, SwitchCard] = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QLabel("Mechanical Switch Library", self)
        header.setObjectName("HeaderLabel")
        header.setStyleSheet("font-size: 20px; font-weight: 800;")
        main_layout.addWidget(header)

        sub = QLabel("Select an authentic mechanical switch acoustic profile to update the audio engine in real time.", self)
        sub.setObjectName("SubheaderLabel")
        main_layout.addWidget(sub)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget(scroll)
        grid = QGridLayout(container)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 8, 0, 8)

        # Standard 6 profiles in 2 columns
        row, col = 0, 0
        for p_id, p_meta in BUILTIN_PROFILES.items():
            card = SwitchCard(
                profile_id=p_id,
                name=p_meta["name"],
                tag=p_meta["tag"],
                description=p_meta["description"],
                parent=container
            )
            card.select_requested.connect(self.profile_selected.emit)
            card.preview_requested.connect(self.preview_requested.emit)
            self.cards[p_id] = card

            grid.addWidget(card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_active_profile(self, active_id: str):
        for p_id, card in self.cards.items():
            card.set_active_state(p_id == active_id)
