from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class HelpPage(QWidget):
    """Product-facing help kept independent from editable settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.browser = QTextBrowser()
        self.browser.setObjectName("helpBrowser")
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(self._content())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.browser)

    @staticmethod
    def _content() -> str:
        return """
        <style>
          body { color:#496681; line-height:1.55; }
          h2 { color:#345d88; margin-bottom:4px; }
          h3 { color:#4778a6; margin-top:18px; margin-bottom:6px; }
          .welcome {
            background:#edf6ff; border:1px solid #d1e5f7;
            border-radius:12px; padding:12px 14px; color:#5f7892;
          }
          li { margin:4px 0; }
          b { color:#3f6488; }
        </style>
        <h2>帮助与说明</h2>
        <p class="welcome">把 Maidie 当作住在桌面上的小伙伴就好。想聊天、看看状态，
        或翻翻共同记忆，都可以从右键菜单开始。</p>
        <h3>基础操作</h3>
        <ul>
          <li><b>点击 Maidie：</b>根据点击位置触发互动。</li>
          <li><b>拖动 Maidie：</b>把她移动到喜欢的位置。</li>
          <li><b>双击 Maidie：</b>快速打开聊天输入框。</li>
          <li><b>鼠标滚轮：</b>缩放角色窗口。</li>
          <li><b>右键菜单：</b>进入聊天、状态、日记、皮肤、设置、帮助和关于。</li>
          <li><b>锁定位置：</b>开启后限制 Maidie 的活动范围。</li>
        </ul>
        <h3>聊天能力</h3>
        <ul>
          <li>“聊聊”用于日常对话、陪伴和问题解答。</li>
          <li>“Maidie 日记”保存最近聊天、重要记忆与成长记录。</li>
          <li>回复较长时会自动打开可滚动的详细内容面板。</li>
        </ul>
        <h3>Agent 工具能力</h3>
        <ul>
          <li>Maidie 会根据输入判断是否需要调用工具。</li>
          <li>简单聊天直接回复；需要外部信息时调用搜索、时间、天气等工具。</li>
          <li>需要屏幕上下文时调用 OCR / Vision / Window 工具。</li>
        </ul>
        <h3>隐私说明</h3>
        <ul>
          <li>Maidie 默认不会主动读取用户文件。</li>
          <li>剪贴板变化只提示，不自动处理内容，除非用户确认。</li>
          <li>屏幕识别需要用户明确触发。</li>
          <li>API Key 保存在本地配置中。</li>
          <li>联网搜索工具通过配置启用。</li>
        </ul>
        <h3>常见问题</h3>
        <p><b>为什么 Maidie 没有回复？</b> 检查 Base URL、模型名称、API Key 和网络连接。</p>
        <p><b>为什么输入框里的文字没有消失？</b> Maidie 仍在处理上一项任务，
        未成功发送的文字会保留，稍后可以再次提交。</p>
        <p><b>为什么搜索失败？</b> 检查联网开关、Tavily Key 和网络状态。</p>
        <p><b>如何调整大小？</b> 使用鼠标滚轮，或右键菜单中的缩放操作。</p>
        <p><b>在哪里查看作者和项目地址？</b> 右键 Maidie，选择“关于 Maidie”。</p>
        <p><b>如何退出 Maidie？</b> 右键 Maidie，选择“退出”。</p>
        """
