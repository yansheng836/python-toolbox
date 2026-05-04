# -*- encoding: utf-8 -*-
"""
settings_page.py - Module for toolbox
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from config import FONT_SIZE_12, FONT_SIZE_16, FONT_SIZE_18, FONT_WEIGHT_600, FONT_WEIGHT_700, FONT_WEIGHT_800
from toolbox import Theme


class Card(QFrame):
    """现代化卡片组件"""

    def __init__(self, title="", parent=None, theme=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.title = title
        self.theme = theme or Theme.DARK
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if self.title:
            title_label = QLabel(self.title)
            title_label.setObjectName("cardTitle")
            title_label.setStyleSheet(f"""
                font-size: {FONT_SIZE_18};
                font-weight: {FONT_WEIGHT_700};
                color: {self.theme['text']};
            """)
            layout.addWidget(title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {self.theme['bg_card']};
                border-radius: 12px;
                border: 1px solid {self.theme['border']};
            }}
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def update_theme(self, theme):
        """更新卡片主题"""
        self.theme = theme
        # 更新标题颜色
        title_label = self.findChild(QLabel, "cardTitle")
        if title_label:
            title_label.setStyleSheet(f"""
                font-size: {FONT_SIZE_18};
                font-weight: {FONT_WEIGHT_700};
                color: {theme['text']};
            """)
        # 更新卡片样式
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {theme['bg_card']};
                border-radius: 12px;
                border: 1px solid {theme['border']};
            }}
        """)


class SettingsPlugin:
    """设置插件 - 包含通用设置和关于信息"""

    name = "设置"
    description = "应用程序设置和关于信息"
    icon = "⚙️"
    version = "1.0.0"

    theme_changed = pyqtSignal(dict)  # 主题更改信号

    def __init__(self, parent=None, theme=None):
        self.parent = parent
        self.theme = theme or Theme.DARK
        self.widget = None

    def create_ui(self) -> QWidget:
        """创建设置页面UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setStyleSheet(f"""
            font-size: 32px;
            font-weight: {FONT_WEIGHT_800};
            color: {self.theme['text']};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.theme['border']};")
        line.setMaximumHeight(1)
        layout.addWidget(line)

        # 通用设置卡片
        general_card = Card("通用设置", theme=self.theme)

        # 主题设置
        theme_label = QLabel("外观:")
        theme_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {self.theme['text']};")
        general_card.content_layout.addWidget(theme_label)

        theme_btn_layout = QHBoxLayout()

        light_theme_btn = QPushButton("☀️ 浅色主题")
        light_theme_btn.setMinimumHeight(44)
        light_theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.LIGHT['bg_secondary']};
                color: {Theme.LIGHT['text']};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: {Theme.LIGHT['surface']};
            }}
        """)
        light_theme_btn.clicked.connect(lambda: self.set_theme("light"))

        dark_theme_btn = QPushButton("🌙 深色主题")
        dark_theme_btn.setMinimumHeight(44)
        dark_theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.DARK['bg_secondary']};
                color: {Theme.DARK['text']};
                border: 1px solid {Theme.DARK['border']};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: {Theme.DARK['surface']};
            }}
        """)
        dark_theme_btn.clicked.connect(lambda: self.set_theme("dark"))

        theme_btn_layout.addWidget(light_theme_btn)
        theme_btn_layout.addWidget(dark_theme_btn)
        theme_btn_layout.addStretch()

        general_card.content_layout.addLayout(theme_btn_layout)
        general_card.content_layout.addStretch()

        # 关于卡片
        about_card = Card("关于", theme=self.theme)

        # 版本信息
        version_label = QLabel(f"版本: v{self.version}")
        version_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {self.theme['text']};")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(version_label)

        # 功能描述
        desc_label = QLabel("批量处理工具，支持图片压缩、PDF转换、格式转换和拼接")
        desc_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_16};")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(desc_label)

        # 官方网站
        website_label = QLabel(
            f"<a href='https://www.example.com' style='color: {self.theme['primary']}; text-decoration: none;'>🌐 访问官方网站</a>")
        website_label.setOpenExternalLinks(True)
        website_label.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            font-weight: {FONT_WEIGHT_600};
            padding: 8px;
        """)
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(website_label)

        # 版权信息
        copyright_label = QLabel("© 2023 工具箱开发团队")
        copyright_label.setStyleSheet(f"color: {self.theme['text_secondary']}; font-size: {FONT_SIZE_12};")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(copyright_label)

        about_card.content_layout.addStretch()

        # 将卡片添加到主布局
        layout.addWidget(general_card)
        layout.addWidget(about_card)
        layout.addStretch()

        self.widget = widget
        return widget

    def get_widget(self) -> QWidget:
        if self.widget is None:
            self.widget = self.create_ui()
        return self.widget

    def set_theme(self, theme_name):
        """设置主题"""
        if theme_name == "light":
            theme = Theme.LIGHT
        else:
            theme = Theme.DARK

        self.theme = theme
        self.update_theme(theme)

        # 发射主题更改信号
        self.theme_changed.emit(theme)

        # 保存主题设置
        self.save_theme_setting(theme_name)

    def update_theme(self, theme):
        """更新主题"""
        # 更新所有子组件的主题
        if self.widget:
            for child in self.widget.findChildren(Card):
                if hasattr(child, 'update_theme'):
                    child.update_theme(theme)
            # 注意：这里需要重新创建 UI 或手动更新所有组件的样式
            # 为了简化，这里只更新 Card 组件

    def save_theme_setting(self, theme_name):
        """保存主题设置"""
        # 这里可以使用QSettings保存主题设置
        # 暂时先打印
        print(f"主题已切换为: {theme_name}")
