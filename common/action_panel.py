"""
通用操作面板组件

包含按钮、进度条、状态标签，封装在一个卡片框内，可复用。
适用于需要"开始/停止"操作的插件（如图片转PDF、压缩、格式转换等）。
"""

from PyQt6.QtWidgets import QProgressBar, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

from toolbox import AnimatedButton, Card, Theme, FONT_SIZE_14, FONT_WEIGHT_600
from common.message_utils import show_info, show_error


class ActionPanel(Card):
    """
    操作面板：按钮 + 进度条 + 状态标签，封装在卡片内

    信号:
        clicked: 按钮被点击时发出
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None, *,
                 button_text="开始",
                 use_gradient=False,
                 gradient_colors=None,
                 gradient_hover_colors=None,
                 status_text="",
                 progress_chunk_color=None):
        super().__init__(parent, title="")  # 不显示卡片标题

        self.use_gradient = use_gradient
        self.gradient_colors = gradient_colors or ('#10b981', '#059669')
        self.gradient_hover_colors = gradient_hover_colors or ('#34d399', '#10b981')
        self.progress_chunk_color = progress_chunk_color or '#8b5cf6'

        self._setup_content(button_text, status_text)

    def _setup_content(self, button_text, status_text):
        """在 Card 的 content_layout 中添加按钮、进度条、状态标签"""

        # 按钮
        self.btn = AnimatedButton(button_text)
        self.btn.setMinimumHeight(40)

        if self.use_gradient:
            self.btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {self.gradient_colors[0]},
                        stop:1 {self.gradient_colors[1]});
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: {FONT_SIZE_14};
                    font-weight: {FONT_WEIGHT_600};
                }}
                QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.gradient_hover_colors[0]},
                    stop:1 {self.gradient_hover_colors[1]}); }}
                QPushButton:disabled {{ background: #334155; color: #64748b; }}
            """)

        self.btn.clicked.connect(self.clicked.emit)
        self.content_layout.addWidget(self.btn)

        # 进度条（初始样式，update_theme 会更新为主题适配的样式）
        self.progress = QProgressBar()
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Theme.DARK['bg_secondary']};
                border-radius: 6px;
                text-align: center;
                color: {Theme.DARK['text']};
            }}
            QProgressBar::chunk {{
                background-color: {self.progress_chunk_color};
                border-radius: 6px;
            }}
        """)
        self.progress.setVisible(False)
        self.content_layout.addWidget(self.progress)

        # 状态标签
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet(f"color: {Theme.DARK['text_secondary']};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.status_label)

    def start_task(self, maximum=0, status=""):
        """开始任务：禁用按钮，显示进度条，设置进度最大值，更新状态"""
        self.btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(maximum)
        self.progress.setValue(0)
        self.status_label.setText(status)

    def update_progress(self, value):
        """更新进度值"""
        self.progress.setValue(value)

    def update_status(self, text):
        """更新状态标签文字"""
        self.status_label.setText(text)

    def finish_task(self, status=""):
        """完成任务：启用按钮，隐藏进度条，更新状态"""
        self.btn.setEnabled(True)
        self.progress.setVisible(False)
        if status:
            self.status_label.setText(status)

    def update_theme(self, theme):
        """更新主题样式"""
        # 更新按钮样式（非渐变按钮由 AnimatedButton.update_style 处理）
        if not self.use_gradient:
            self.btn.update_style(theme)

        # 渐变按钮的主题更新：保持原渐变色（或可按主题调整）
        # 此处保持用户自定义的渐变色不变

        # 更新进度条样式
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme['bg']};
                border-radius: 6px;
                text-align: center;
                color: {theme['text']};
            }}
            QProgressBar::chunk {{
                background-color: {theme['secondary']};
                border-radius: 6px;
            }}
        """)

        # 更新状态标签样式
        self.status_label.setStyleSheet(f"color: {theme['text_secondary']};")
