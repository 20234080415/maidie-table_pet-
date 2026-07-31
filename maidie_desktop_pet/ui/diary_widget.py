from __future__ import annotations

import html

from PyQt6.QtWidgets import QDialog, QLabel, QTabWidget, QTextBrowser, QVBoxLayout

from ui.theme import apply_dialog_theme


class DiaryWidget(QDialog):
    """Read-only first pass for chats, important memories, and growth."""

    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Maidie 日记")
        self.resize(620, 520)
        apply_dialog_theme(self)
        self.tabs = QTabWidget()
        self.recent_browser = QTextBrowser()
        self.memory_browser = QTextBrowser()
        self.growth_browser = QTextBrowser()
        self.tabs.addTab(self.recent_browser, "最近聊天")
        self.tabs.addTab(self.memory_browser, "重要记忆")
        self.tabs.addTab(self.growth_browser, "成长记录")
        layout = QVBoxLayout(self)
        title = QLabel("📖 Maidie 日记")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        layout.addWidget(self.tabs)
        self.refresh()

    def refresh(self) -> None:
        chats = self.controller.recent_chats()
        if chats:
            recent = []
            for item in chats:
                recent.append(
                    "<div style='margin:8px 2px 14px'>"
                    f"<small style='color:#9a7f84'>{html.escape(str(item.get('time', '')))}</small>"
                    f"<p><b>你：</b>{html.escape(str(item.get('message', '')))}</p>"
                    "<p style='background:#fff2ec;padding:9px;border-radius:10px'>"
                    f"<b>Maidie：</b>{html.escape(str(item.get('response', '')))}</p></div>"
                )
            self.recent_browser.setHtml("".join(recent))
        else:
            self.recent_browser.setHtml("<p>今天还没有写下新的聊天。</p>")

        memory_loader = getattr(self.controller, "important_memories", None)
        memories = memory_loader() if callable(memory_loader) else []
        if memories:
            items = [
                f"<li><b>{html.escape(str(item.get('key', '记忆')))}</b>："
                f"{html.escape(str(item.get('value', '')))}</li>"
                for item in memories
            ]
            self.memory_browser.setHtml("<ul>" + "".join(items) + "</ul>")
        else:
            self.memory_browser.setHtml("<p>重要的事会慢慢记在这里。</p>")

        snapshot = self.controller.pet_state_snapshot()
        self.growth_browser.setHtml(
            "<div style='line-height:1.8'>"
            f"<p><b>相识时间：</b>{html.escape(str(snapshot.get('first_meet_time', '')))}</p>"
            f"<p><b>陪伴时长：</b>{html.escape(str(snapshot.get('companion_time', '')))}</p>"
            f"<p><b>当前关系：</b>{html.escape(str(snapshot.get('relationship', '初识')))}</p>"
            f"<p><b>累计互动：</b>{int(snapshot.get('interaction_count', 0))} 次</p>"
            "</div>"
        )

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)
