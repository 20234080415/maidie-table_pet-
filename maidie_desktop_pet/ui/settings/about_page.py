from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.version import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_DISPLAY_VERSION,
    APP_GITHUB_URL,
    APP_NAME,
)


class AboutPage(QWidget):
    """Warm, product-facing identity card for Maidie."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutPage")
        self.setStyleSheet("""
            QWidget#aboutPage {
                background: transparent;
                color: #3f5876;
            }
            QFrame#aboutHeroCard {
                background: #f7fbff;
                border: 1px solid #c9def4;
                border-radius: 22px;
            }
            QLabel#aboutAppName {
                color: #345d88;
                font-size: 26px;
                font-weight: 750;
            }
            QLabel#aboutMark {
                min-width: 54px;
                max-width: 54px;
                min-height: 54px;
                max-height: 54px;
                background: #dceeff;
                color: #4f84b7;
                border: 1px solid #bedaf4;
                border-radius: 27px;
                font-size: 25px;
                font-weight: 750;
            }
            QLabel#aboutTagline {
                color: #6c85a1;
                font-size: 13px;
            }
            QLabel#aboutVersion {
                background: #dceeff;
                color: #3c6f9f;
                border: 1px solid #bedaf4;
                border-radius: 10px;
                padding: 5px 12px;
                font-weight: 650;
            }
            QLabel#aboutCreator {
                background: #edf6ff;
                color: #4d6b8a;
                border-radius: 14px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLabel#aboutDescription {
                color: #657f9b;
                font-size: 13px;
            }
            QLabel#aboutGithubAddress {
                color: #7b91aa;
                font-size: 11px;
            }
            QPushButton#githubButton {
                min-height: 38px;
                background: #7eb6e8;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 7px 18px;
                font-size: 14px;
                font-weight: 650;
            }
            QPushButton#githubButton:hover {
                background: #6aa8df;
            }
            QPushButton#githubButton:pressed {
                background: #5c99cf;
            }
        """)

        card = QFrame()
        card.setObjectName("aboutHeroCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 25, 28, 25)
        card_layout.setSpacing(11)

        mark = QLabel("M")
        mark.setObjectName("aboutMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("aboutAppName")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("很高兴在你的桌面上陪着你。")
        tagline.setObjectName("aboutTagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"版本 {APP_DISPLAY_VERSION}")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        creator = QLabel(f"创作者 / \n{APP_AUTHOR}")
        creator.setObjectName("aboutCreator")
        creator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(APP_DESCRIPTION)
        description.setObjectName("aboutDescription")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setMinimumWidth(0)
        description.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )

        github_address = QLabel(APP_GITHUB_URL)
        github_address.setObjectName("aboutGithubAddress")
        github_address.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_address.setWordWrap(True)
        github_address.setMinimumWidth(0)
        github_address.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        github_address.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        github = QPushButton("在 GitHub 查看 Maidie  ↗")
        github.setObjectName("githubButton")
        github.clicked.connect(self.open_github)

        card_layout.addWidget(mark, alignment=Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(title)
        card_layout.addWidget(tagline)
        card_layout.addWidget(version, alignment=Qt.AlignmentFlag.AlignHCenter)
        card_layout.addSpacing(5)
        card_layout.addWidget(creator)
        card_layout.addWidget(description)
        card_layout.addSpacing(3)
        card_layout.addWidget(github_address)
        card_layout.addWidget(github)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(card)
        layout.addStretch(1)

    def open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(APP_GITHUB_URL))
