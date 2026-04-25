from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QComboBox, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class Card(QFrame):
    """现代化卡片组件"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.title = title
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if self.title:
            title_label = QLabel(self.title)
            title_label.setObjectName("cardTitle")
            title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: 700;
                color: #f1f5f9;
            """)
            layout.addWidget(title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        self.setStyleSheet("""
            QFrame#card {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class SettingsPlugin:
    """设置插件 - 包含通用设置和关于信息"""

    name = "设置"
    description = "应用程序设置和关于信息"
    icon = "⚙️"
    version = "1.0.0"

    theme_changed = pyqtSignal(dict)  # 主题更改信号

    def __init__(self, parent=None):
        self.parent = parent
        self.widget = None

    def create_ui(self) -> QWidget:
        """创建设置页面UI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #f1f5f9;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        layout.addWidget(line)

        # 通用设置卡片
        general_card = Card("通用设置")

        # 主题设置
        theme_label = QLabel("外观:")
        theme_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f1f5f9;")
        general_card.content_layout.addWidget(theme_label)

        theme_btn_layout = QHBoxLayout()

        light_theme_btn = QPushButton("☀️ 浅色主题")
        light_theme_btn.setMinimumHeight(44)
        light_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        light_theme_btn.clicked.connect(lambda: self.set_theme("light"))

        dark_theme_btn = QPushButton("🌙 深色主题")
        dark_theme_btn.setMinimumHeight(44)
        dark_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        dark_theme_btn.clicked.connect(lambda: self.set_theme("dark"))

        theme_btn_layout.addWidget(light_theme_btn)
        theme_btn_layout.addWidget(dark_theme_btn)
        theme_btn_layout.addStretch()

        general_card.content_layout.addLayout(theme_btn_layout)
        general_card.content_layout.addStretch()

        # 关于卡片
        about_card = Card("关于")

        # 版本信息
        version_label = QLabel(f"版本: v{self.version}")
        version_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #f1f5f9;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(version_label)

        # 功能描述
        desc_label = QLabel("批量处理工具，支持图片压缩、PDF转换、格式转换和拼接")
        desc_label.setStyleSheet("color: #94a3b8; font-size: 14px;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(desc_label)

        # 官方网站
        website_label = QLabel(
            "<a href='https://www.example.com' style='color: #6366f1; text-decoration: none;'>🌐 访问官方网站</a>")
        website_label.setOpenExternalLinks(True)
        website_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 500;
            padding: 8px;
        """)
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(website_label)

        # 版权信息
        copyright_label = QLabel("© 2023 工具箱开发团队")
        copyright_label.setStyleSheet("color: #64748b; font-size: 12px;")
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
        from toolbox import Theme

        if theme_name == "light":
            theme = Theme.LIGHT
        else:
            theme = Theme.DARK

        # 发射主题更改信号
        self.theme_changed.emit(theme)

        # 保存主题设置
        self.save_theme_setting(theme_name)

    def save_theme_setting(self, theme_name):
        """保存主题设置"""
        # 这里可以使用QSettings保存主题设置
        # 暂时先打印
        print(f"主题已切换为: {theme_name}")
