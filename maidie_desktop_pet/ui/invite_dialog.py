"""Invite-code and first-run AI service dialogs."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ui.theme import apply_dialog_theme


class _ActivationWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, activation: Callable[[str], dict[str, Any]], code: str):
        super().__init__()
        self.activation = activation
        self.code = code

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.activation(self.code)
        except Exception:
            result = {
                "success": False,
                "message": "邀请码无效，请检查后重试",
            }
        self.finished.emit(result)


class InviteCodeDialog(QDialog):
    """Non-blocking invite activation styled like Maidie's settings surfaces."""

    def __init__(
        self,
        activation: Callable[[str], dict[str, Any]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.activation = activation
        self._thread: QThread | None = None
        self._worker: _ActivationWorker | None = None
        self.setWindowTitle("使用邀请码解锁 AI")
        self.setMinimumWidth(430)
        apply_dialog_theme(self)

        title = QLabel("使用邀请码解锁 AI")
        title.setObjectName("panelTitle")
        note = QLabel(
            "输入一个 Maidie 邀请码，即可授权默认 AI、Tavily 搜索和千问视觉服务。"
        )
        note.setObjectName("sectionSubtitle")
        note.setWordWrap(True)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入邀请码")
        self.code_input.returnPressed.connect(self._activate)
        self.status = QLabel("")
        self.status.setObjectName("settingHint")
        self.status.setWordWrap(True)

        self.activate_button = QPushButton("激活")
        self.activate_button.setDefault(True)
        self.activate_button.clicked.connect(self._activate)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.activate_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self.code_input)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

    def _activate(self) -> None:
        code = self.code_input.text().strip()
        if not code:
            self._show_failure("邀请码无效，请检查后重试")
            return
        if self._thread is not None:
            return
        self.activate_button.setEnabled(False)
        self.code_input.setEnabled(False)
        self.status.setStyleSheet("color: #52627a;")
        self.status.setText("正在验证邀请码…")

        thread = QThread(self)
        worker = _ActivationWorker(self.activation, code)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._activation_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _activation_finished(self, result: object) -> None:
        payload = result if isinstance(result, dict) else {}
        if payload.get("success"):
            self.status.setStyleSheet("color: #16803a; font-weight: 600;")
            self.status.setText("Maidie准备好陪你啦~")
            self.accept()
            return
        self._show_failure("邀请码无效，请检查后重试")

    def _show_failure(self, message: str) -> None:
        self.status.setStyleSheet("color: #c0392b;")
        self.status.setText(message)
        self.activate_button.setEnabled(True)
        self.code_input.setEnabled(True)
        self.code_input.setFocus()
        self.code_input.selectAll()

    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def reject(self) -> None:
        if self._thread is not None:
            return
        super().reject()


class AIServiceSetupDialog(QDialog):
    """First-run choice shown only when neither custom API nor token exists."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.choice = "skip"
        self.setWindowTitle("AI 服务设置")
        self.setMinimumWidth(460)
        apply_dialog_theme(self)

        title = QLabel("AI 服务设置")
        title.setObjectName("panelTitle")
        note = QLabel(
            "选择一种方式启用 Maidie 的云服务。一个邀请码可授权 AI、搜索和视觉；"
            "你之后仍可在设置中填写自己的各类 API Key。"
        )
        note.setObjectName("sectionSubtitle")
        note.setWordWrap(True)
        invite = QPushButton("使用邀请码解锁 AI")
        custom = QPushButton("配置自己的 API Key")
        skip = QPushButton("暂时跳过")
        invite.clicked.connect(lambda: self._choose("invite"))
        custom.clicked.connect(lambda: self._choose("custom"))
        skip.clicked.connect(lambda: self._choose("skip"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addSpacing(4)
        layout.addWidget(invite)
        layout.addWidget(custom)
        layout.addWidget(skip)

    def _choose(self, choice: str) -> None:
        self.choice = choice
        self.accept()
