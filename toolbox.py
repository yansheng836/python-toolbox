import sys
import os
import importlib
import importlib.util
from pathlib import Path
from typing import Dict

# 从config.py导入全局配置
try:
    from config import (
        APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_COPYRIGHT,
        APP_WEBSITE_URL, APP_WEBSITE_LINK_TEXT,
        FEATURE_MODULES, UI_CONFIG, THEME_CONFIG, WELCOME_CONFIG,
        TITLE_STYLES, FONT_SIZE_12, FONT_SIZE_14, FONT_SIZE_16, FONT_SIZE_20,
        FONT_WEIGHT_600, FONT_WEIGHT_700, FONT_WEIGHT_800
    )
except ImportError:
    __version__ = "1.0.0"
    APP_NAME = "工具箱"
    APP_DESCRIPTION = "批量处理工具，支持图片压缩、PDF转换、格式转换和拼接"
    APP_COPYRIGHT = "© 2023 工具箱开发团队"
    APP_WEBSITE_URL = "https://www.example.com"
    APP_WEBSITE_LINK_TEXT = "🌐 访问官方网站"
    FEATURE_MODULES = []
    UI_CONFIG = {}
    THEME_CONFIG = {}
    WELCOME_CONFIG = {}

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy,
    QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QSettings
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QColor, QFont, QAction
)


# ==================== 主题配置 ====================
class Theme:
    """现代化深色/浅色主题"""
    DARK = {
        'primary': '#6366f1',
        'primary_hover': '#4f46e5',
        'secondary': '#8b5cf6',
        'bg': '#0f172a',
        'bg_secondary': '#1e293b',
        'bg_card': '#1e293b',
        'surface': '#334155',
        'text': '#f1f5f9',
        'text_secondary': '#94a3b8',
        'border': '#334155',
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'shadow': 'rgba(0, 0, 0, 0.3)'
    }

    LIGHT = {
        'primary': '#4f46e5',
        'primary_hover': '#4338ca',
        'secondary': '#7c3aed',
        'bg': '#f8fafc',
        'bg_secondary': '#f1f5f9',
        'bg_card': '#ffffff',
        'surface': '#e2e8f0',
        'text': '#0f172a',
        'text_secondary': '#64748b',
        'border': '#e2e8f0',
        'success': '#059669',
        'warning': '#d97706',
        'error': '#dc2626',
        'shadow': 'rgba(0, 0, 0, 0.1)'
    }

    @staticmethod
    def init_theme():
        """初始化主题系统"""


# ==================== 动画组件 ====================
class AnimatedButton(QPushButton):
    """带动画效果的按钮"""

    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)

        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.base_style = ""
        self.update_style()

    def update_style(self, theme=None):
        if theme is None:
            theme = Theme.DARK
        self.base_style = f"""
            QPushButton {{
                background-color: {theme['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: {FONT_WEIGHT_600};
                font-size: {FONT_SIZE_16};
            }}
            QPushButton:hover {{
                background-color: {theme['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['secondary']};
            }}
            QPushButton:disabled {{
                background-color: {theme['surface']};
                color: {theme['text_secondary']};
            }}
        """
        self.setStyleSheet(self.base_style)

    def enterEvent(self, event):
        self.setStyleSheet(self.base_style.replace(
            f"background-color: {Theme.DARK['primary']};",
            f"background-color: {Theme.DARK['primary_hover']};"
        ))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        super().leaveEvent(event)


class Card(QFrame):
    """现代化卡片组件"""

    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.title = title
        self.setObjectName("card")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setObjectName("cardTitle")
            self.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']}; color: #f1f5f9;")
            layout.addWidget(self.title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        self.setStyleSheet("""
            QFrame#card {
                background-color: #1e293b;
                border-radius: 12px;
                border: none;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class SidebarButton(QPushButton):
    """侧边栏导航按钮"""

    def __init__(self, text, icon_text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setMinimumHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                text-align: left;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.1);
                color: #f1f5f9;
            }
            QPushButton:checked {
                background-color: rgba(99, 102, 241, 0.2);
                color: #6366f1;
                font-weight: {FONT_WEIGHT_600};
            }
        """)


# ==================== 核心功能模块 ====================
class ToolPlugin:
    """插件基类 - 所有工具都应继承此类"""
    name = "Base Tool"
    description = "Base tool description"
    icon = "🔧"
    version = "1.0.0"
    order = 999  # 插件排序权重，数值越小排在越前面

    def __init__(self, parent=None):
        self.parent = parent
        self.widget = None

    def create_ui(self) -> QWidget:
        """创建工具UI，子类必须实现"""
        raise NotImplementedError

    def get_widget(self) -> QWidget:
        if self.widget is None:
            self.widget = self.create_ui()
            if hasattr(self, 'setup_drag_handler'):
                self.setup_drag_handler()
        return self.widget

    def update_theme(self, theme):
        """更新主题 - 由子类实现"""


# ==================== 拖拽处理工具类 ====================
class DragDropHandler:
    """通用的拖拽处理工具类"""

    @staticmethod
    def setup_drag_drop(text_edit, files_list):
        text_edit.setAcceptDrops(True)
        text_edit.dragEnterEvent = lambda e: DragDropHandler.drag_enter_event(e, files_list)
        text_edit.dropEvent = lambda e: DragDropHandler.drop_event(e, files_list)

    @staticmethod
    def drag_enter_event(event, files_list):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')):
                        event.acceptProposedAction()
                        return
        event.ignore()

    @staticmethod
    def drop_event(event, files_list):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')):
                        if hasattr(files_list, 'append'):
                            if file_path not in files_list.files:
                                files_list.append(file_path)
                        else:
                            if file_path not in files_list:
                                files_list.append(file_path)
            if hasattr(files_list, '_parent') and hasattr(files_list._parent, 'update_file_list'):
                files_list._parent.update_file_list()
            elif hasattr(files_list, '_text_edit'):
                if hasattr(files_list, 'files'):
                    files_list._text_edit.setText("\n".join([os.path.basename(f) for f in files_list.files]))
                else:
                    files_list._text_edit.setText("\n".join([os.path.basename(f) for f in files_list]))
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def update_file_list_display(text_edit, files_list):
        text_edit.setText("\n".join([os.path.basename(f) for f in files_list]))

class WelcomePage(QWidget):
    """欢迎页面"""

    def __init__(self, plugins=None, parent=None):
        super().__init__(parent)
        self.plugins = plugins or {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        logo = QLabel("🧰")
        logo.setStyleSheet("font-size: 72px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel(APP_NAME)
        title.setStyleSheet(f"""
            font-size: 36px;
            font-weight: {FONT_WEIGHT_800};
            color: #f1f5f9;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(WELCOME_CONFIG.get("subtitle", ""))
        subtitle.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            color: #94a3b8;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        features = QWidget()
        features_layout = QHBoxLayout(features)
        features_layout.setSpacing(16)

        for icon, text, desc in FEATURE_MODULES:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border-radius: 12px;
                    border: 1px solid #334155;
                    padding: 20px;
                }
            """)
            card_layout = QVBoxLayout(card)

            icon_label = QLabel(icon)
            icon_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            font = icon_label.font()
            font.setPointSize(24)
            font.setBold(True)
            icon_label.setFont(font)
            icon_label.setMinimumSize(48, 48)
            card_layout.setStretch(0, 2)
            card_layout.setStretch(1, 1)
            card_layout.addWidget(icon_label)

            text_label = QLabel(text)
            font = text_label.font()
            font.setPointSize(14)
            font.setBold(True)
            text_label.setFont(font)
            text_label.setStyleSheet("color: #f1f5f9;")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(text_label)

            desc_label = QLabel(desc)
            desc_font = desc_label.font()
            desc_font.setPointSize(11)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet("color: #94a3b8;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(desc_label)

            features_layout.addWidget(card)

        layout.addWidget(features)

        hint = QLabel(WELCOME_CONFIG.get("hint", ""))
        hint.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            color: #6366f1;
            margin-top: 20px;
        """)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()

class SettingsPlugin(ToolPlugin):
    """设置插件 - 包含通用设置和关于信息"""

    name = "设置"
    description = "应用程序设置和关于信息"
    icon = "⚙️"
    version = "1.0.0"
    order = 999  # 设置始终放在最后

    def update_theme(self, theme):
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']}; color: {theme['text']};")

        if hasattr(self, 'theme_label'):
            self.theme_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {theme['text']};")

        if hasattr(self, 'version_label'):
            self.version_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {theme['text']};")

        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_16};")

        if hasattr(self, 'website_label'):
            self.website_label.setStyleSheet(f"""
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
                color: {theme['text']};
                padding: 8px;
            """)

        if hasattr(self, 'copyright_label'):
            self.copyright_label.setStyleSheet(f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_12};")

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        self.title_label = QLabel("⚙️ 设置")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        layout.addWidget(line)

        general_card = Card(title="通用设置")

        self.theme_label = QLabel("外观:")
        self.theme_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};")
        general_card.content_layout.addWidget(self.theme_label)

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
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }
            QPushButton:hover { background-color: #e2e8f0; }
            QPushButton:checked {
                background-color: #fbbf24;
                color: #0f172a;
                font-weight: {FONT_WEIGHT_700};
            }
        """)

        dark_theme_btn = QPushButton("🌙 深色主题")
        dark_theme_btn.setMinimumHeight(44)
        dark_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }
            QPushButton:hover { background-color: #334155; }
            QPushButton:checked {
                background-color: #6366f1;
                color: white;
                font-weight: {FONT_WEIGHT_700};
                border: none;
            }
        """)

        self.light_theme_btn = light_theme_btn
        self.dark_theme_btn = dark_theme_btn

        light_theme_btn.clicked.connect(lambda: self.switch_theme("light"))
        dark_theme_btn.clicked.connect(lambda: self.switch_theme("dark"))

        theme_btn_layout.addWidget(light_theme_btn)
        theme_btn_layout.addWidget(dark_theme_btn)
        theme_btn_layout.addStretch()

        general_card.content_layout.addLayout(theme_btn_layout)
        general_card.content_layout.addStretch()

        about_card = Card(title="关于")

        self.version_label = QLabel(f"版本: v{APP_VERSION}")
        self.version_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.version_label)

        self.desc_label = QLabel(APP_DESCRIPTION)
        self.desc_label.setStyleSheet(f"font-size: {FONT_SIZE_16};")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.desc_label)

        self.website_label = QLabel(
            f"<a href='{APP_WEBSITE_URL}' style='color: #6366f1; text-decoration: none;'>{APP_WEBSITE_LINK_TEXT}</a>")
        self.website_label.setOpenExternalLinks(True)
        self.website_label.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            font-weight: {FONT_WEIGHT_600};
            padding: 8px;
        """)
        self.website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.website_label)

        self.copyright_label = QLabel(APP_COPYRIGHT)
        self.copyright_label.setStyleSheet(f"color: #64748b; font-size: {FONT_SIZE_12};")
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.copyright_label)
        about_card.content_layout.addStretch()

        layout.addWidget(general_card)
        layout.addWidget(about_card)
        layout.addStretch()

        return widget

    def switch_theme(self, theme_name):
        if theme_name == "light":
            self.light_theme_btn.setChecked(True)
            self.dark_theme_btn.setChecked(False)
        else:
            self.dark_theme_btn.setChecked(True)
            self.light_theme_btn.setChecked(False)
        self.set_theme(theme_name)

    def set_theme(self, theme_name):
        if theme_name == "light":
            theme = Theme.LIGHT
        else:
            theme = Theme.DARK

        self.save_theme_setting(theme_name)

        if hasattr(self.parent, 'apply_theme'):
            self.parent.apply_theme(theme)

        if hasattr(self.parent, 'theme_changed'):
            self.parent.theme_changed.emit(theme_name)

        print(f"主题已切换为: {theme_name}")

    def save_theme_setting(self, theme_name):
        settings = QSettings("Toolbox", "App")
        settings.setValue("theme", theme_name)

class ToolboxWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setWindowTitle(UI_CONFIG.get("window_title", f"{APP_NAME} v{APP_VERSION}"))

        # 设置窗口图标
        self._set_window_icon()

        # 设置窗口最小尺寸
        min_size = UI_CONFIG.get("window_min_size", (1200, 800))
        self.setMinimumSize(min_size[0], min_size[1])

        # 设置窗口最大尺寸（可选）
        max_size = UI_CONFIG.get("window_max_size", None)
        if max_size:
            self.setMaximumSize(max_size[0], max_size[1])
        else:
            # 明确不限制最大尺寸，确保可以调整大小
            self.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX

        self.settings = QSettings("Toolbox", "App")
        self.load_geometry()

        self.plugins: Dict[str, ToolPlugin] = {}
        self.current_plugin = None

        self.setup_ui()
        self.load_plugins()

        self.setup_tray()
        self.init_theme()
        self.setup_menu()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMaximumWidth(260)
        self.sidebar.setMinimumWidth(260)
        self.sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)

        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🧰")
        logo_icon.setStyleSheet("font-size: 28px;")
        logo_text = QLabel("工具箱")
        logo_text.setStyleSheet(f"font-size: {FONT_SIZE_20}; font-weight: {FONT_WEIGHT_700};")
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        sidebar_layout.addWidget(line)

        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 8, 0, 0)
        self.nav_layout.setSpacing(4)
        sidebar_layout.addWidget(self.nav_widget)

        sidebar_layout.addStretch()

        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet(f"color: #475569; font-size: {FONT_SIZE_12};")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version)

        main_layout.addWidget(self.sidebar)

        self.content = QStackedWidget()
        self.content.setStyleSheet("""
            QStackedWidget {
                background-color: #0f172a;
            }
        """)

        self.welcome_page = WelcomePage(self.plugins)
        self.content.addWidget(self.welcome_page)

        main_layout.addWidget(self.content, 1)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QScrollArea { border: none; background-color: transparent; }
            QLabel { color: #f1f5f9; }
            QMessageBox { background-color: #1e293b; }
            QMessageBox QLabel { color: #f1f5f9; }
            QDialog { background-color: #0f172a; }
        """)

    def register_plugin(self, plugin_class):
        try:
            plugin = plugin_class(self)
            self.plugins[plugin.name] = plugin

            btn = SidebarButton(plugin.name, plugin.icon)
            from functools import partial
            btn.clicked.connect(partial(self.switch_plugin, plugin.name))
            self.nav_layout.addWidget(btn)

            widget = plugin.get_widget()
            self.content.addWidget(widget)
        except Exception as e:
            print(f"注册插件失败 {plugin_class.name}: {e}")

    def load_plugins(self):
        """从plugins目录加载外部插件，按order排序后注册"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent

        plugins_dir = base_path / "plugins"
        plugin_classes = []

        # 收集外部插件类
        if plugins_dir.exists():
            for file in plugins_dir.glob("*.py"):
                try:
                    spec = importlib.util.spec_from_file_location(file.stem, file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                                attr.__name__ != 'ToolPlugin' and
                                any(c.__name__ == 'ToolPlugin' for c in attr.__mro__)):
                            plugin_classes.append(attr)
                except Exception as e:
                    print(f"加载插件失败 {file}: {e}")

        # 添加设置插件
        plugin_classes.append(SettingsPlugin)

        # 按 order 排序（数值越小排在越前面）
        plugin_classes.sort(key=lambda x: getattr(x, 'order', 999))

        # 按顺序注册插件
        for plugin_class in plugin_classes:
            self.register_plugin(plugin_class)

    def switch_plugin(self, name):
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton):
                widget.setChecked(name in widget.text())

        if name in self.plugins:
            widget = self.plugins[name].get_widget()
            index = self.content.indexOf(widget)
            if index >= 0:
                self.content.setCurrentIndex(index)
                self.current_plugin = name

    def _set_window_icon(self):
        """设置窗口图标，支持开发模式和打包模式"""
        if getattr(sys, 'frozen', False):
            # 打包模式：使用 PyInstaller 的 _MEIPASS 路径
            base_path = Path(sys._MEIPASS)
        else:
            # 开发模式：使用当前文件所在目录
            base_path = Path(__file__).parent

        icon_path = base_path / "favicon.ico"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)
            # 同时设置应用程序图标
            if self._app:
                self._app.setWindowIcon(icon)

    def init_theme(self):
        theme_name = "dark"
        theme = Theme.DARK
        self.apply_theme(theme)
        self.settings.setValue("theme", theme_name)

    def apply_theme(self, theme):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {theme['bg']}; }}
            QScrollArea {{ border: none; background-color: {theme['bg']}; }}
            QFrame {{ background-color: {theme['bg_secondary']}; border: 1px solid {theme['surface']}; }}
            QLabel {{ color: {theme['text']}; }}
            *[style*="color: #f1f5f9"] {{ color: {theme['text']} !important; }}
            *[style*="color: white"] {{ color: {theme['text']} !important; }}
            *[style*="color: #94a3b8"] {{ color: {theme['text_secondary']} !important; }}
            *[style*="color: #64748b"] {{ color: {theme['text_secondary']} !important; }}
            *[style*="background-color: #0f172a"] {{ background-color: {theme['bg']} !important; }}
            *[style*="background-color: #1e293b"] {{ background-color: {theme['bg_secondary']} !important; }}
            QTextEdit {{
                background-color: {theme['bg']};
                border: 2px solid {theme['surface']};
                border-radius: 8px;
                color: {theme['text']};
                padding: 8px;
            }}
            QLineEdit {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {theme['text']};
            }}
            QComboBox {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {theme['text']};
            }}
            QTableWidget {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 8px;
                color: {theme['text']};
                gridline-color: {theme['surface']};
            }}
            QProgressBar {{
                background-color: {theme['bg']};
                border-radius: 6px;
                text-align: center;
                color: {theme['text']};
            }}
            QHeaderView::section {{
                background-color: {theme['bg_secondary']};
                color: {theme['text']};
                padding: 4px;
                border: 1px solid {theme['surface']};
            }}
            QPushButton {{
                background-color: {theme['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{ background-color: {theme['primary_hover']}; }}
            QPushButton:disabled {{ background-color: {theme['surface']}; color: {theme['text_secondary']}; }}
        """)

        self.sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {theme['bg_secondary']};
                border-right: 1px solid {theme['surface']};
            }}
        """)

        self.content.setStyleSheet(f"""
            QStackedWidget {{ background-color: {theme['bg']}; }}
        """)

        for plugin_name, plugin in self.plugins.items():
            if hasattr(plugin, 'update_theme'):
                plugin.update_theme(theme)

    def setup_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self)
            self.tray.setToolTip("工具箱")

            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "favicon.ico")
            if os.path.exists(icon_path):
                self.tray.setIcon(QIcon(icon_path))
            else:
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor("#6366f1"))
                self.tray.setIcon(QIcon(pixmap))

            menu = QMenu()
            show_action = menu.addAction("显示")
            show_action.triggered.connect(self.show)
            quit_action = menu.addAction("退出")
            quit_action.triggered.connect(QApplication.quit)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu('工具')
        settings_action = QAction('设置', self)
        settings_action.setShortcut('Ctrl+S')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

    def show_settings(self):
        self.switch_plugin("设置")

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        self.save_geometry()
        event.accept()

    def save_geometry(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def load_geometry(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 800)
            self.move(
                QApplication.primaryScreen().geometry().center() -
                self.rect().center()
            )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("工具箱")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Toolbox")
    app.setOrganizationDomain("toolbox.com")

    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 设置应用程序图标（支持开发模式和打包模式）
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    icon_path = base_path / "favicon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = ToolboxWindow(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
