# -*- encoding: utf-8 -*-
"""
toolbox.py - Module for toolbox
"""

import sys
import os
import importlib
import importlib.util
from pathlib import Path
from typing import Dict

# 从config.py导入全局配置
from config import (
    APP_VERSION,
    APP_WEBSITE_URL,
    APP_UPDATE_URL, APP_ISSUE_URL,
    PLUGIN_MODULES, UI_CONFIG,
    TITLE_STYLES, FONT_SIZE_12, FONT_SIZE_14, FONT_SIZE_16, FONT_SIZE_20,
    FONT_WEIGHT_600, FONT_WEIGHT_700, FONT_WEIGHT_800,
    SPACING_SMALL
)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QComboBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QSystemTrayIcon, QMenu, QScrollArea,
    QListWidget, QListWidgetItem, QAbstractItemView, QSizePolicy,
    QStylePainter, QStyleOptionComboBox, QStyle
)
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QTimer, QEvent
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QColor, QAction, QPainter, QPainterPath, QPen, QPalette
)

from common import i18n
from common import nav_config
from common.i18n import t, bind_combo, install_qt_translator
from common.utils import get_combo_style


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
        'success_hover': '#34d399',
        'success_gradient_end': '#059669',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'error_hover': '#f87171',
        'error_gradient_end': '#dc2626',
        'action_gradient_start': '#10b981',
        'action_gradient_end': '#059669',
        'action_gradient_hover_start': '#34d399',
        'action_gradient_hover_end': '#10b981',
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
        'success_hover': '#10b981',
        'success_gradient_end': '#047857',
        'warning': '#d97706',
        'error': '#dc2626',
        'error_hover': '#ef4444',
        'error_gradient_end': '#b91c1c',
        'action_gradient_start': '#10b981',
        'action_gradient_end': '#059669',
        'action_gradient_hover_start': '#34d399',
        'action_gradient_hover_end': '#10b981',
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
                padding: 6px 12px;
                font-weight: {FONT_WEIGHT_600};
                font-size: {FONT_SIZE_14};
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
        # 渐变样式由 :hover 伪状态处理，不在此处替换颜色
        if "qlineargradient" not in self.styleSheet():
            self.setStyleSheet(self.base_style.replace(
                f"background-color: {Theme.DARK['primary']};",
                f"background-color: {Theme.DARK['primary_hover']};"
            ))
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 渐变样式由 :hover 伪状态处理，不在此处替换颜色
        if "qlineargradient" not in self.styleSheet():
            self.setStyleSheet(self.base_style)
        super().leaveEvent(event)


class SelectableLabel(QLabel):
    """支持鼠标选择和复制文本的标签组件"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.setCursor(Qt.CursorShape.IBeamCursor)
        # 悬停链接时以 tooltip 显示目标地址；离开链接时信号传空串，自动清除
        self.linkHovered.connect(self.setToolTip)


class Card(QFrame):
    """现代化卡片组件"""

    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.title = title
        self.setObjectName("card")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # 卡片内边距：调小至12px，使卡片内容更紧凑（原20px）
        layout.setContentsMargins(12, 12, 12, 12)
        # 卡片内部元素间距：调小至8px（原12px）
        layout.setSpacing(SPACING_SMALL)

        if self.title:
            self.title_label = SelectableLabel(self.title)
            self.title_label.setObjectName("cardTitle")
            self.title_label.setStyleSheet(
                f"font-size: {FONT_SIZE_20}; font-weight: {FONT_WEIGHT_700};")
            self.title_label.setWordWrap(True)
            layout.addWidget(self.title_label)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class SidebarButton(QPushButton):
    """侧边栏导航按钮"""

    def __init__(self, plugin_id, text, icon_text, parent=None):
        super().__init__(parent)
        self._plugin_id = plugin_id
        self._icon_text = icon_text
        self._text = text
        self._elided_text = ""
        self.setMinimumHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.apply_theme(Theme.DARK)
        self._apply_text()
        self.setToolTip(text)

    def apply_theme(self, theme):
        """按主题重设按钮配色，保证浅色主题下文字对比度"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 0 10px;
                text-align: left;
                font-size: {FONT_SIZE_16};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: rgba(99, 102, 241, 0.1);
                color: {theme['text']};
            }}
            QPushButton:checked {{
                background-color: rgba(99, 102, 241, 0.2);
                color: {theme['primary']};
                font-weight: {FONT_WEIGHT_600};
            }}
        """)

    def plugin_id(self):
        """返回该按钮绑定的插件稳定 id"""
        return self._plugin_id

    def _apply_text(self):
        """按当前宽度省略过长文本，完整名称保留在 tooltip 中"""
        metrics = self.fontMetrics()
        if self.width() <= 0:
            display = self._text
        else:
            reserved = metrics.horizontalAdvance(f" {self._icon_text}  ")
            available = max(0, self.width() - 20 - reserved)
            display = metrics.elidedText(
                self._text, Qt.TextElideMode.ElideRight, available
            )
        if display != self._elided_text:
            self._elided_text = display
            self.setText(f" {self._icon_text}  {display}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_text()

    def set_texts(self, text, icon_text):
        """更新按钮显示文本（保留 icon+文本的双空格布局），供语言切换重放"""
        self._text = text
        self._icon_text = icon_text
        self._elided_text = ""
        self.setToolTip(text)
        self._apply_text()


# ==================== 核心功能模块 ====================
class CenteredComboBox(QComboBox):
    """文本水平居中的下拉框

    Qt 样式表的 text-align 对 QComboBox 不生效，因此改为自绘：
    让样式只画边框与箭头，再在整个控件范围内居中绘制当前文本。
    """

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        text = option.currentText
        option.currentText = ""
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        painter.setPen(self.palette().color(QPalette.ColorRole.Text))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class ToolPlugin:
    """插件基类 - 所有工具都应继承此类"""
    name = "Base Tool"
    description = "Base tool description"
    icon = "🔧"
    version = "2.0.1"
    order = 999  # 插件排序权重，数值越小排在越前面
    id = None  # 插件稳定 id，由 load_plugins 从 config 注入

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

    def retranslate_ui(self):
        """语言切换时刷新界面文本 - 由子类实现（与 update_theme 对称）"""

    # ==================== 共享辅助方法 ====================

    def _setup_header(self, layout, title=None, desc=None, theme=None):
        """创建标题和描述标签

        统一处理所有插件常见的标题+描述布局。
        Args:
            layout: 父级 QVBoxLayout
            title: 标题文本，默认使用 self.icon + self.name
            desc: 描述文本，默认使用 self.description
            theme: 主题字典，默认使用 Theme.DARK
        """
        if theme is None:
            from toolbox import Theme
            theme = Theme.DARK
        title_text = title or f"{self.icon} {self.name}"
        desc_text = desc or self.description

        self.title_label = SelectableLabel(title_text)
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; "
            f"font-weight: {TITLE_STYLES['font_weight']}; "
            f"color: {theme['text']};"
        )
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.desc_label = SelectableLabel(desc_text)
        self.desc_label.setStyleSheet(
            f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_14};"
        )
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

    def _show_empty_warning(self, message=None):
        """弹出文件为空警告"""
        from common.message_utils import show_warning
        if message is None:
            message = t("app.warning.empty_files")
        parent = self.widget if self.widget else None
        show_warning(parent, t("app.dialog.warning_title"), message)

    def _finish_with_message(self, action_panel, success, message):
        """完成任务并显示结果消息

        统一处理完成后的操作面板更新和结果弹窗。
        """
        from common.message_utils import show_info, show_error
        action_panel.finish_task(message)
        parent = self.widget if self.widget else None
        if success:
            show_info(parent, t("app.dialog.done_title"), message)
        else:
            show_error(parent, t("app.dialog.error_title"), message)


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
    """欢迎页面 - 支持卡片自动轮播"""

    def __init__(self, plugins=None, parent=None):
        super().__init__(parent)
        self.plugins = plugins or {}
        self.favicon_path = self._get_favicon_path()
        self.separators = []
        self.title = None
        self.subtitle = None
        self.hint = None
        self.text_labels = []
        self.desc_labels = []

        # 轮播相关属性
        self.scroll_area = None
        self.features_widget = None
        self.scroll_timer = None
        self.scroll_step = 1
        self.scroll_interval = 30
        self.pause_on_hover = True
        self._scroll_direction = 1  # 1=右, -1=左
        self._at_end_pause = 0
        self._paused_by_hover = False

        self.setup_ui()
        self._init_auto_scroll()

    def _init_auto_scroll(self):
        """初始化自动轮播定时器"""
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._do_auto_scroll)
        self.scroll_timer.start(self.scroll_interval)

    def _do_auto_scroll(self):
        """执行自动滚动"""
        if not self.scroll_area or not self.features_widget:
            return
        if self._paused_by_hover:
            return

        hbar = self.scroll_area.horizontalScrollBar()
        if hbar.maximum() <= 0:
            return

        current = hbar.value()
        maximum = hbar.maximum()

        # 暂停计数（到达端点后短暂停留）
        if self._at_end_pause > 0:
            self._at_end_pause -= 1
            return

        if self._scroll_direction > 0:
            if current >= maximum:
                self._scroll_direction = -1
                self._at_end_pause = int(1500 / self.scroll_interval)  # 暂停1.5秒
                return
            hbar.setValue(current + self.scroll_step)
        else:
            if current <= 0:
                self._scroll_direction = 1
                self._at_end_pause = int(1500 / self.scroll_interval)
                return
            hbar.setValue(current - self.scroll_step)

    def eventFilter(self, watched, event):
        """事件过滤器：仅当鼠标进入/离开卡片滚动区域时暂停/恢复轮播"""
        if watched == self.scroll_area:
            if event.type() == QEvent.Type.Enter:
                self._paused_by_hover = True
            elif event.type() == QEvent.Type.Leave:
                self._paused_by_hover = False
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        """窗口大小变化时动态调整轮播区域高度"""
        super().resizeEvent(event)
        if self.scroll_area:
            # 根据窗口高度动态设置轮播区域高度（约占可用高度的 35-40%）
            available_height = self.height()
            # 计算合适的高度：最小 250px，最大 500px，默认约 35% 窗口高度
            target_height = max(250, min(500, int(available_height * 0.35)))
            self.scroll_area.setMaximumHeight(target_height)

    def update_theme(self, theme):
        """更新欢迎页主题"""
        if self.title:
            self.title.setStyleSheet(f"""
                font-size: 36px;
                font-weight: {FONT_WEIGHT_800};
                color: {theme['text']};
            """)
        if self.subtitle:
            self.subtitle.setStyleSheet(f"""
                font-size: {FONT_SIZE_16};
                color: {theme['text_secondary']};
            """)
        if self.hint:
            self.hint.setStyleSheet(f"""
                font-size: {FONT_SIZE_16};
                color: {theme['primary']};
                margin-top: 20px;
            """)
        for sep in self.separators:
            sep.setStyleSheet(f"background-color: {theme['surface']}; max-height: 1px;")
        for label in self.text_labels:
            label.setStyleSheet(f"color: {theme['text']};")
        for label in self.desc_labels:
            label.setStyleSheet(f"color: {theme['text_secondary']};")

        if hasattr(self, "empty_hint"):
            self.empty_hint.setStyleSheet(f"""
                font-size: {FONT_SIZE_16};
                color: {theme['text_secondary']};
            """)

        # 更新滚动条主题
        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                QScrollBar:horizontal {{
                    background: {theme['bg_secondary']};
                    height: 8px;
                    margin: 0;
                }}
                QScrollBar::handle:horizontal {{
                    background: {theme['surface']};
                    min-width: 20px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: {theme['text_secondary']};
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    width: 0;
                }}
            """)

    def retranslate_ui(self):
        """语言切换后重放欢迎页文本（title/subtitle/hint/功能卡片）"""
        if self.title:
            self.title.setText(t("welcome.title"))
        if self.subtitle:
            self.subtitle.setText(t("welcome.subtitle"))
        if self.hint:
            self.hint.setText(t("welcome.hint"))
        if hasattr(self, "empty_hint"):
            self.empty_hint.setText(t("welcome.no_tools_hint"))
        for pid, text_label, desc_label in zip(
            self._feature_ids, self.text_labels, self.desc_labels
        ):
            if text_label:
                text_label.setText(t(f"plugin.{pid}.name"))
            if desc_label:
                desc = t(f"plugin.{pid}.description")
                desc_label.setText(desc[:40] + "..." if len(desc) > 40 else desc)

    @staticmethod
    def _get_favicon_path():
        """获取 favicon.ico 的路径，支持开发模式和打包模式"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent
        return str(base_path / "favicon.ico")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(5, 0, 5, 0)

        logo = QLabel()
        if self.favicon_path and os.path.exists(self.favicon_path):
            pixmap = QPixmap(self.favicon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
                logo.setPixmap(scaled_pixmap)
            else:
                logo.setText("🧰")
                logo.setStyleSheet("font-size: 72px;")
        else:
            logo.setText("🧰")
            logo.setStyleSheet("font-size: 72px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        self.title = SelectableLabel(t("welcome.title"))
        self.title.setStyleSheet(f"""
            font-size: 36px;
            font-weight: {FONT_WEIGHT_800};
            color: {Theme.DARK['text']};
        """)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        self.subtitle = SelectableLabel(t("welcome.subtitle"))
        self.subtitle.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            color: {Theme.DARK['text_secondary']};
        """)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        # 功能卡片区域 - 使用横向滚动（自动轮播）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # 移除固定高度，改为在 resizeEvent 中动态设置
        self.scroll_area.setMinimumHeight(250)  # 设置最小高度
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:horizontal {{
                background: {Theme.DARK['bg_secondary']};
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {Theme.DARK['surface']};
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {Theme.DARK['text_secondary']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
        """)
        self.scroll_area.viewport().setStyleSheet("background-color: transparent;")
        self.scroll_area.installEventFilter(self)

        self.features_widget = QWidget()
        self.features_layout = QHBoxLayout(self.features_widget)
        # 卡片间距
        self.features_layout.setSpacing(10)
        self.features_layout.setContentsMargins(5, 10, 5, 10)

        self.scroll_area.setWidget(self.features_widget)
        layout.addWidget(self.scroll_area)

        # 全部工具被隐藏时替代轮播区显示
        self.empty_hint = SelectableLabel(t("welcome.no_tools_hint"))
        self.empty_hint.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            color: {Theme.DARK['text_secondary']};
        """)
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setVisible(False)
        layout.addWidget(self.empty_hint)

        self.hint = SelectableLabel(t("welcome.hint"))
        self.hint.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            color: {Theme.DARK['primary']};
            margin-top: 20px;
        """)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint)

        layout.addStretch()

        # 先按 config.py 默认顺序创建卡片；应用启动后由
        # ToolboxWindow.rebuild_navigation() 按用户配置重建
        self.rebuild_feature_cards(
            [p["id"] for p in PLUGIN_MODULES if p["order"] < 999])

    def _create_feature_card(self, plugin_config):
        """创建单个功能卡片，并把标签登记到语言切换/主题更新用的列表"""
        pid = plugin_config["id"]
        icon = plugin_config["icon"]
        text = t(f"plugin.{pid}.name")
        desc = t(f"plugin.{pid}.description")

        card = QFrame()
        card.setObjectName("card")
        # 卡片内边距：左右调小至8px，使内容更紧凑（原12px）
        card.setContentsMargins(6, 10, 6, 10)
        card.setMinimumWidth(200)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = icon_label.font()
        font.setPointSize(20)
        font.setBold(True)
        icon_label.setFont(font)
        icon_label.setMinimumSize(36, 36)
        card_layout.addWidget(icon_label)

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background-color: {Theme.DARK['surface']}; max-height: 1px;")
        self.separators.append(line1)
        card_layout.addWidget(line1)

        text_label = SelectableLabel(text)
        font = text_label.font()
        font.setPointSize(14)
        font.setBold(True)
        text_label.setFont(font)
        text_label.setStyleSheet(f"color: {Theme.DARK['text']};")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_labels.append(text_label)
        card_layout.addWidget(text_label)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"background-color: {Theme.DARK['surface']}; max-height: 1px;")
        self.separators.append(line2)
        card_layout.addWidget(line2)

        desc_text = desc[:40] + "..." if len(desc) > 40 else desc
        desc_label = SelectableLabel(desc_text)
        desc_font = desc_label.font()
        desc_font.setPointSize(10)
        desc_label.setFont(desc_font)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {Theme.DARK['text_secondary']};")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_labels.append(desc_label)
        card_layout.addWidget(desc_label)

        return card

    def rebuild_feature_cards(self, visible_ids):
        """按可见插件 id 重建首页功能卡片（顺序与侧边栏一致）

        重建同时重置 text_labels/desc_labels/separators/_feature_ids，
        保证语言切换重放与主题更新只作用于当前卡片（这些列表只增不清
        会导致重放错位）。
        """
        if not hasattr(self, "features_layout"):
            return

        # 清空旧卡片：逐个摘除并销毁，避免布局项与控件残留
        while self.features_layout.count():
            item = self.features_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self.text_labels = []
        self.desc_labels = []
        self.separators = []
        self._feature_ids = []

        by_id = {p["id"]: p for p in PLUGIN_MODULES}
        for pid in visible_ids:
            plugin_config = by_id.get(pid)
            if plugin_config is None:
                continue
            self.features_layout.addWidget(self._create_feature_card(plugin_config))
            self._feature_ids.append(pid)

        # 轮播状态复位，避免定时器继续指向旧的滚动范围
        self._scroll_direction = 1
        self._at_end_pause = 0
        self.scroll_area.horizontalScrollBar().setValue(0)

        has_tools = bool(self._feature_ids)
        self.scroll_area.setVisible(has_tools)
        if hasattr(self, "empty_hint"):
            self.empty_hint.setVisible(not has_tools)

class SettingsPlugin(ToolPlugin):
    """设置插件 - 包含通用设置和关于信息"""

    # 有边框控件（主题按钮/语言下拉/恢复默认按钮）统一尺寸，保证视觉对齐
    CONTROL_WIDTH = 170
    CONTROL_HEIGHT = 40

    def update_theme(self, theme):
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(
                f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']}; color: {theme['text']};")

        if hasattr(self, 'theme_label'):
            self.theme_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {theme['text']};")

        if hasattr(self, 'language_label'):
            self.language_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {theme['text']};")

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

        if hasattr(self, 'language_combo'):
            self.language_combo.setStyleSheet(
                get_combo_style(theme, FONT_SIZE_14, FONT_WEIGHT_600))

        if hasattr(self, 'reset_btn'):
            self._apply_reset_style(theme)

        if hasattr(self, 'nav_hint_label'):
            self.nav_hint_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_12};")

        if hasattr(self, 'nav_list'):
            self.nav_list.setStyleSheet(self._nav_list_style(theme))

        if hasattr(self, 'nav_show_all_btn'):
            self._apply_nav_button_style(theme)

    def _apply_reset_style(self, theme):
        """恢复默认设置标题/提示文字/按钮随主题更新（红色描边，强调不可逆操作）"""
        self.reset_label.setStyleSheet(
            f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {theme['text']};")
        self.reset_hint_label.setStyleSheet(
            f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_12};")
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['error']};
                border: 1px solid {theme['error']};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: {FONT_SIZE_14};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: {theme['error']};
                color: #ffffff;
            }}
        """)

    def create_ui(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # INI 配置引用（ToolboxWindow 已在 P2-A 接线中保证存在）
        self._settings_ref = getattr(self.parent, "app_settings", None)

        self.title_label = SelectableLabel(f"{self.icon} {t('plugin.settings.name')}")
        self.title_label.setStyleSheet(
            f"font-size: {TITLE_STYLES['font_size']}; font-weight: {TITLE_STYLES['font_weight']};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #334155;")
        line.setMaximumHeight(1)
        layout.addWidget(line)

        general_card = Card(title=t("settings.card.general"))
        self._general_card = general_card

        self.theme_label = SelectableLabel(t("settings.label.appearance"))
        self.theme_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};")
        general_card.content_layout.addWidget(self.theme_label)

        theme_btn_layout = QHBoxLayout()

        light_theme_btn = QPushButton(t("settings.button.light_theme"))
        light_theme_btn.setFixedHeight(self.CONTROL_HEIGHT)
        light_theme_btn.setMinimumWidth(self.CONTROL_WIDTH)
        light_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #0f172a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
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

        dark_theme_btn = QPushButton(t("settings.button.dark_theme"))
        dark_theme_btn.setFixedHeight(self.CONTROL_HEIGHT)
        dark_theme_btn.setMinimumWidth(self.CONTROL_WIDTH)
        dark_theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 16px;
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

        general_card.content_layout.addSpacing(SPACING_SMALL)

        # 语言切换行：bind_combo 自动填充并在语言切换时重放（保持选中 data）
        self.language_label = SelectableLabel(t("settings.label.language"))
        self.language_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};")
        general_card.content_layout.addWidget(self.language_label)

        language_layout = QHBoxLayout()
        self.language_combo = CenteredComboBox()
        self.language_combo.setFixedHeight(self.CONTROL_HEIGHT)
        self.language_combo.setMinimumWidth(self.CONTROL_WIDTH)
        self.language_combo.setStyleSheet(
            get_combo_style(Theme.DARK, FONT_SIZE_14, FONT_WEIGHT_600))
        bind_combo(self.language_combo, [
            ("settings.combo.zh_CN", "zh_CN"),
            ("settings.combo.en", "en"),
        ])
        self.language_combo.setCurrentIndex(
            self.language_combo.findData(i18n.manager.current_language))
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        general_card.content_layout.addLayout(language_layout)

        general_card.content_layout.addSpacing(SPACING_SMALL)

        # 恢复默认设置
        self.reset_label = SelectableLabel(t("settings.label.reset_defaults"))
        self.reset_label.setStyleSheet(
            f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600}; color: {self.parent.current_theme['text']};")
        general_card.content_layout.addWidget(self.reset_label)

        self.reset_hint_label = SelectableLabel(t("settings.label.reset_hint"))
        self.reset_hint_label.setWordWrap(True)
        general_card.content_layout.addWidget(self.reset_hint_label)

        self.reset_btn = QPushButton(t("settings.button.reset_defaults"))
        self.reset_btn.setFixedHeight(self.CONTROL_HEIGHT)
        self.reset_btn.setMinimumWidth(self.CONTROL_WIDTH)
        self.reset_btn.clicked.connect(self.reset_defaults)
        reset_btn_layout = QHBoxLayout()
        reset_btn_layout.addWidget(self.reset_btn)
        reset_btn_layout.addStretch()
        general_card.content_layout.addLayout(reset_btn_layout)
        self._apply_reset_style(self.parent.current_theme)

        general_card.content_layout.addStretch()

        # 导航栏管理：拖拽排序 + 勾选控制可见性，改动即时生效并持久化
        nav_card = Card(title=t("settings.card.nav"))
        self._nav_card = nav_card

        self.nav_hint_label = SelectableLabel(t("settings.label.nav_hint"))
        self.nav_hint_label.setWordWrap(True)
        nav_card.content_layout.addWidget(self.nav_hint_label)

        self.nav_list = QListWidget()
        self.nav_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.nav_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.nav_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.nav_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nav_list.setStyleSheet(self._nav_list_style(self.parent.current_theme))
        self._populate_nav_list()
        self.nav_list.itemChanged.connect(self._on_nav_item_changed)
        self.nav_list.model().rowsMoved.connect(self._on_nav_rows_moved)
        nav_card.content_layout.addWidget(self.nav_list)

        self.nav_show_all_btn = QPushButton(t("settings.button.nav_show_all"))
        self.nav_show_all_btn.setFixedHeight(self.CONTROL_HEIGHT)
        self.nav_show_all_btn.setMinimumWidth(self.CONTROL_WIDTH)
        self.nav_show_all_btn.clicked.connect(self._show_all_nav_items)

        self.nav_reset_btn = QPushButton(t("settings.button.nav_reset"))
        self.nav_reset_btn.setFixedHeight(self.CONTROL_HEIGHT)
        self.nav_reset_btn.setMinimumWidth(self.CONTROL_WIDTH)
        self.nav_reset_btn.clicked.connect(self._reset_nav_config)

        nav_btn_layout = QHBoxLayout()
        nav_btn_layout.addWidget(self.nav_show_all_btn)
        nav_btn_layout.addWidget(self.nav_reset_btn)
        nav_btn_layout.addStretch()
        nav_card.content_layout.addLayout(nav_btn_layout)
        self._apply_nav_button_style(self.parent.current_theme)

        about_card = Card(title=t("settings.card.about"))
        self._about_card = about_card

        self.version_label = SelectableLabel(t("settings.label.version", version=APP_VERSION))
        self.version_label.setStyleSheet(f"font-size: {FONT_SIZE_16}; font-weight: {FONT_WEIGHT_600};")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.version_label)

        # 检查更新
        update_label = SelectableLabel(
            f"<a href='{APP_UPDATE_URL}' style='color: #6366f1; text-decoration: none;'>"
            f"{t('settings.link.check_update')}</a>")
        update_label.setOpenExternalLinks(True)
        update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        update_label.setStyleSheet(f"font-size: {FONT_SIZE_14}; padding: 2px;")
        self._update_label = update_label
        about_card.content_layout.addWidget(update_label)

        # 问题反馈
        issue_label = SelectableLabel(
            f"<a href='{APP_ISSUE_URL}' style='color: #6366f1; text-decoration: none;'>"
            f"{t('settings.link.feedback')}</a>")
        issue_label.setOpenExternalLinks(True)
        issue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        issue_label.setStyleSheet(f"font-size: {FONT_SIZE_14}; padding: 2px;")
        self._issue_label = issue_label
        about_card.content_layout.addWidget(issue_label)

        self.website_label = SelectableLabel(
            f"<a href='{APP_WEBSITE_URL}' style='color: #6366f1; text-decoration: none;'>{t('app.website_link_text')}</a>")
        self.website_label.setOpenExternalLinks(True)
        self.website_label.setStyleSheet(f"""
            font-size: {FONT_SIZE_16};
            font-weight: {FONT_WEIGHT_600};
            padding: 8px;
        """)
        self.website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.website_label)

        self.copyright_label = SelectableLabel(t("app.copyright"))
        self.copyright_label.setStyleSheet(f"color: #64748b; font-size: {FONT_SIZE_12};")
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_card.content_layout.addWidget(self.copyright_label)

        about_card.content_layout.addStretch()

        layout.addWidget(general_card)
        layout.addWidget(nav_card)
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
        """主题持久化到 INI [general] theme（旧 QSettings 注册表已弃用）"""
        if self._settings_ref is not None:
            self._settings_ref.set("general", "theme", theme_name)
            self._settings_ref.save()

    # ==================== 导航栏管理 ====================

    @staticmethod
    def _nav_list_style(theme):
        """导航列表样式（深浅主题下背景与文字均需可读）"""
        return f"""
            QListWidget {{
                background-color: {theme['bg']};
                border: 1px solid {theme['surface']};
                border-radius: 8px;
                color: {theme['text']};
                padding: 4px;
                font-size: {FONT_SIZE_14};
            }}
            QListWidget::item {{
                padding: 6px 4px;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {theme['primary']};
                color: #ffffff;
            }}
        """

    def _apply_nav_button_style(self, theme):
        """导航管理按钮：中性描边样式，与红色「恢复默认设置」区分"""
        style = f"""
            QPushButton {{
                background-color: transparent;
                color: {theme['text']};
                border: 1px solid {theme['surface']};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: {FONT_SIZE_14};
                font-weight: {FONT_WEIGHT_600};
            }}
            QPushButton:hover {{
                background-color: {theme['surface']};
            }}
        """
        self.nav_show_all_btn.setStyleSheet(style)
        self.nav_reset_btn.setStyleSheet(style)

    def _populate_nav_list(self):
        """按当前配置填充导航列表（回填期间屏蔽信号，避免误触发持久化）"""
        order, hidden = nav_config.load_nav_state(self._settings_ref, PLUGIN_MODULES)
        meta = {p["id"]: p for p in PLUGIN_MODULES}

        self.nav_list.blockSignals(True)
        try:
            self.nav_list.clear()
            for pid in order:
                plugin_config = meta.get(pid, {})
                item = QListWidgetItem(
                    f"{plugin_config.get('icon', '🔧')} {t(f'plugin.{pid}.name')}")
                item.setData(Qt.ItemDataRole.UserRole, pid)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Unchecked if pid in hidden else Qt.CheckState.Checked)
                self.nav_list.addItem(item)
        finally:
            self.nav_list.blockSignals(False)

        # 按条目实际行高给出最小高度：插件增多时可滚动，减少时不留大片空白
        row_height = self.nav_list.sizeHintForRow(0) if self.nav_list.count() else 0
        if row_height <= 0:
            row_height = 30
        self.nav_list.setMinimumHeight(
            min(360, row_height * self.nav_list.count() + 16))

    def _current_nav_selection(self):
        """从列表读出 (order, hidden)"""
        order = []
        hidden = []
        for row in range(self.nav_list.count()):
            item = self.nav_list.item(row)
            pid = item.data(Qt.ItemDataRole.UserRole)
            if not pid:
                continue
            order.append(pid)
            if item.checkState() != Qt.CheckState.Checked:
                hidden.append(pid)
        return order, hidden

    def _apply_nav_config(self):
        """保存列表当前状态并立即生效（侧边栏与首页卡片同步重建）"""
        order, hidden = self._current_nav_selection()
        nav_config.save_nav_state(self._settings_ref, order, hidden)
        if hasattr(self.parent, "rebuild_navigation"):
            self.parent.rebuild_navigation()

    def _on_nav_item_changed(self, item):
        """勾选状态变化：立即应用（item 参数为信号签名所需）"""
        self._apply_nav_config()

    def _on_nav_rows_moved(self, *args):
        """拖拽排序完成：立即应用（*args 为 rowsMoved 信号参数）"""
        self._apply_nav_config()

    def _show_all_nav_items(self):
        """全部显示：勾选所有条目，顺序保持不变"""
        self.nav_list.blockSignals(True)
        try:
            for row in range(self.nav_list.count()):
                self.nav_list.item(row).setCheckState(Qt.CheckState.Checked)
        finally:
            self.nav_list.blockSignals(False)
        self._apply_nav_config()

    def _reset_nav_config(self):
        """恢复默认顺序与全部可见"""
        nav_config.reset_nav_state(self._settings_ref)
        self._populate_nav_list()
        if hasattr(self.parent, "rebuild_navigation"):
            self.parent.rebuild_navigation()

    def reset_defaults(self):
        """恢复默认设置：清空 INI 保存值，按全新安装状态重新初始化

        语言与首次启动一致按系统语言检测；主题回到默认深色；窗口几何复位。
        """
        from common.message_utils import show_error, show_info, show_question

        theme = self.parent.current_theme
        if not show_question(
                self.parent,
                t("settings.dialog.reset_title"),
                t("settings.dialog.reset_confirm"),
                theme=theme):
            return

        try:
            self._settings_ref.reset()
        except OSError as e:
            print(f"恢复默认设置失败：{e}")
            show_error(
                self.parent,
                t("settings.dialog.reset_title"),
                t("settings.dialog.reset_failed", error=e),
                theme=theme)
            return

        # 导航栏恢复默认顺序与全部可见
        self._populate_nav_list()
        if hasattr(self.parent, "rebuild_navigation"):
            self.parent.rebuild_navigation()

        # 主题回到默认深色
        self.switch_theme("dark")

        # 语言与首次启动一致：按系统语言重新检测（索引变化时触发全窗重放）
        code = i18n.detect_system_language()
        index = self.language_combo.findData(code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        # 索引未变化时不会触发持久化，这里统一写回检测结果
        self._persist_language(code)

        # 窗口布局恢复默认尺寸并居中
        if hasattr(self.parent, "apply_default_geometry"):
            self.parent.apply_default_geometry()

        show_info(
            self.parent,
            t("settings.dialog.reset_title"),
            t("settings.dialog.reset_done"),
            theme=self.parent.current_theme)

    def _persist_language(self, code):
        """把语言代码持久化到 INI [general] language"""
        if self._settings_ref is not None:
            self._settings_ref.set("general", "language", code)
            self._settings_ref.save()

    def _on_language_changed(self, index):
        """语言下拉变化：持久化到 INI 并切换语言（触发全窗 retranslate）"""
        code = self.language_combo.itemData(index)
        if not code or code == i18n.manager.current_language:
            return
        self._persist_language(code)
        i18n.set_language(code)
        install_qt_translator(QApplication.instance(), code)

    def retranslate_ui(self):
        """语言切换后重放设置页全部静态文本（语言下拉由 bind_combo 自动重放）"""
        self.title_label.setText(f"{self.icon} {t('plugin.settings.name')}")
        self._general_card.title_label.setText(t("settings.card.general"))
        self.theme_label.setText(t("settings.label.appearance"))
        self.language_label.setText(t("settings.label.language"))
        self.light_theme_btn.setText(t("settings.button.light_theme"))
        self.dark_theme_btn.setText(t("settings.button.dark_theme"))
        self.reset_label.setText(t("settings.label.reset_defaults"))
        self.reset_hint_label.setText(t("settings.label.reset_hint"))
        self.reset_btn.setText(t("settings.button.reset_defaults"))
        self._nav_card.title_label.setText(t("settings.card.nav"))
        self.nav_hint_label.setText(t("settings.label.nav_hint"))
        self.nav_show_all_btn.setText(t("settings.button.nav_show_all"))
        self.nav_reset_btn.setText(t("settings.button.nav_reset"))
        self._populate_nav_list()
        self._about_card.title_label.setText(t("settings.card.about"))
        self.version_label.setText(t("settings.label.version", version=APP_VERSION))
        self._update_label.setText(
            f"<a href='{APP_UPDATE_URL}' style='color: #6366f1; text-decoration: none;'>"
            f"{t('settings.link.check_update')}</a>")
        self._issue_label.setText(
            f"<a href='{APP_ISSUE_URL}' style='color: #6366f1; text-decoration: none;'>"
            f"{t('settings.link.feedback')}</a>")
        self.website_label.setText(
            f"<a href='{APP_WEBSITE_URL}' style='color: #6366f1; text-decoration: none;'>{t('app.website_link_text')}</a>")
        self.copyright_label.setText(t("app.copyright"))

class ToolboxWindow(QMainWindow):
    def __init__(self, app=None, settings=None):
        super().__init__()
        self._app = app
        # INI 配置（main.py 创建后传入；独立构造时兜底自建，保持向后兼容）
        if settings is None:
            from common.app_settings import AppSettings
            settings = AppSettings()
        self.app_settings = settings
        self.setWindowTitle(t("app.window_title", version=APP_VERSION))

        # 设置窗口图标
        self._set_window_icon()

        # 设置窗口最小尺寸（支持像素值或百分比）
        min_size = UI_CONFIG.get("window_min_size", (0.7, 0.8))
        min_w, min_h = self._resolve_size(min_size)
        self.setMinimumSize(min_w, min_h)

        # 设置窗口最大尺寸（可选，支持像素值或百分比）
        max_size = UI_CONFIG.get("window_max_size", None)
        if max_size:
            max_w, max_h = self._resolve_size(max_size)
            self.setMaximumSize(max_w, max_h)
        else:
            # 明确不限制最大尺寸，确保可以调整大小
            self.setMaximumSize(16777215, 16777215)  # QWIDGETSIZE_MAX

        self.load_geometry()

        self.plugins: Dict[str, ToolPlugin] = {}
        self.nav_buttons: Dict[str, SidebarButton] = {}  # 插件 id -> 导航按钮
        self._hidden_plugins = set()  # 被用户隐藏的插件 id，供切换时防护
        self.current_plugin = None
        self.sidebar_expanded = True
        self._sidebar_animating = False
        self._current_theme = Theme.DARK  # 初始默认主题，apply_theme 中会更新

        self.setup_ui()
        self.load_plugins()

        self.setup_tray()
        self.init_theme()
        self.setup_menu()

        # 语言切换：信号驱动全窗重放（构造时语言已由 main.py 设置，文本即正确）
        i18n.manager.language_changed.connect(self.retranslate_ui)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar_width = UI_CONFIG.get("sidebar_width", 260)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMaximumWidth(sidebar_width)
        self.sidebar.setMinimumWidth(sidebar_width)
        # 初始样式会在 apply_theme 中设置

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(SPACING_SMALL)

        logo_layout = QHBoxLayout()
        # 图标中心与下方导航图标列对齐，文字与导航项文字左边缘对齐
        logo_layout.setContentsMargins(10, 0, 0, 0)
        logo_layout.setSpacing(5)
        self.logo_icon = QLabel()
        # 加载 favicon.ico 作为 logo
        favicon_path = self._get_favicon_path()
        if favicon_path and os.path.exists(favicon_path):
            pixmap = QPixmap(favicon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo_icon.setPixmap(scaled_pixmap)
            else:
                self.logo_icon.setText("🧰")
                self.logo_icon.setStyleSheet("font-size: 28px;")
        else:
            self.logo_icon.setText("🧰")
            self.logo_icon.setStyleSheet("font-size: 28px;")
        self.logo_text = SelectableLabel(t("sidebar.logo_text"))
        logo_layout.addWidget(self.logo_icon)
        logo_layout.addWidget(self.logo_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        self.sidebar_line = QFrame()
        self.sidebar_line.setObjectName("sidebarLine")
        self.sidebar_line.setFrameShape(QFrame.Shape.HLine)
        self.sidebar_line.setMaximumHeight(1)
        sidebar_layout.addWidget(self.sidebar_line)

        # 首页按钮
        self.home_btn = SidebarButton(None, t("sidebar.home"), "🏠")
        self.home_btn.setChecked(True)
        self.home_btn.clicked.connect(self.switch_to_welcome)
        sidebar_layout.addWidget(self.home_btn)

        self.nav_widget = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(0, 8, 0, 0)
        self.nav_layout.setSpacing(4)
        sidebar_layout.addWidget(self.nav_widget)

        sidebar_layout.addStretch()

        self.version_label = SelectableLabel(t("sidebar.version", version=APP_VERSION))
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.version_label)

        # 侧边栏折叠按钮（位于 sidebar 右侧边缘，垂直居中）
        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setObjectName("sidebarToggle")
        self.sidebar_toggle_btn.setFixedWidth(36)
        self.sidebar_toggle_btn.setIconSize(QSize(22, 22))
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip(t("sidebar.tooltip.collapse"))
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        self.sidebar_toggle_btn.installEventFilter(self)
        self._set_toggle_icon()

        # 用于折叠时隐藏的侧边栏子控件列表
        self._sidebar_children = [
            self.logo_icon, self.logo_text, self.sidebar_line,
            self.home_btn, self.nav_widget, self.version_label
        ]

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.sidebar_toggle_btn)

        self.content = QStackedWidget()
        self.content.setStyleSheet("""
            QStackedWidget {
                background-color: #0f172a;
            }
        """)

        self.welcome_page = WelcomePage(self.plugins)
        welcome_scroll = QScrollArea()
        welcome_scroll.setWidgetResizable(True)
        welcome_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        welcome_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        welcome_scroll.setWidget(self.welcome_page)
        # 设置视口背景色为透明，避免白色背景
        welcome_scroll.viewport().setStyleSheet("background-color: transparent;")
        welcome_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                background: #1e293b; width: 8px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #475569; min-height: 20px; border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #64748b; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.welcome_scroll = welcome_scroll
        self.content.addWidget(welcome_scroll)

        main_layout.addWidget(self.content, 1)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QScrollArea { border: none; background-color: transparent; }
            QLabel { color: #f1f5f9; }
            QDialog { background-color: #0f172a; }
        """)

    def register_plugin(self, plugin_class):
        try:
            plugin = plugin_class(self)
            self.plugins[plugin.id] = plugin

            btn = SidebarButton(plugin.id, t(f"plugin.{plugin.id}.name"), plugin.icon)
            from functools import partial
            btn.clicked.connect(partial(self.switch_plugin, plugin.id))
            self.nav_layout.addWidget(btn)
            self.nav_buttons[plugin.id] = btn

            widget = plugin.get_widget()
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setWidget(widget)
            # 设置视口背景色为透明，避免白色背景
            scroll_area.viewport().setStyleSheet("background-color: transparent;")
            scroll_area.setStyleSheet("""
                QScrollArea { border: none; background-color: transparent; }
                QScrollBar:vertical {
                    background: #1e293b; width: 8px; margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #475569; min-height: 20px; border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover { background: #64748b; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """)
            plugin.scroll_area = scroll_area
            self.content.addWidget(scroll_area)
        except Exception as e:
            print(f"注册插件失败 {getattr(plugin_class, 'id', '?')}: {e}")

    def load_plugins(self):
        """从PLUGIN_MODULES配置加载插件，按order排序后注册"""
        plugin_classes = []

        for plugin_config in PLUGIN_MODULES:
            try:
                # 动态导入模块
                module = importlib.import_module(plugin_config["module"])
                # 获取插件类
                plugin_class = getattr(module, plugin_config["class"])
                # 动态设置属性（与配置保持一致，单一数据源）
                plugin_class.id = plugin_config["id"]
                plugin_class.name = plugin_config["name"]
                plugin_class.icon = plugin_config["icon"]
                plugin_class.order = plugin_config["order"]
                if "description" in plugin_config:
                    plugin_class.description = plugin_config["description"]
                plugin_classes.append(plugin_class)
            except Exception as e:
                print(f"加载插件失败 {plugin_config.get('name', 'unknown')}: {e}")

        # 按 order 排序（数值越小排在越前面）
        plugin_classes.sort(key=lambda x: getattr(x, 'order', 999))

        # 按顺序注册插件
        for plugin_class in plugin_classes:
            self.register_plugin(plugin_class)

        # 注册完成后按用户配置重排/隐藏导航项与首页卡片
        self.rebuild_navigation()

    def rebuild_navigation(self):
        """按用户配置重排侧边栏导航项，并同步首页功能卡片

        只调整已存在按钮的布局位置与可见性，不重建插件页面——页面在
        QStackedWidget 中按 plugin.scroll_area 定位，与导航顺序无关。
        """
        order, hidden = nav_config.load_nav_state(self.app_settings, PLUGIN_MODULES)
        self._hidden_plugins = set(hidden)

        position = 0
        for plugin_id in order:
            btn = self.nav_buttons.get(plugin_id)
            if btn is None:
                # 插件加载失败时没有对应按钮，跳过且不影响其余项顺序
                continue
            self.nav_layout.removeWidget(btn)
            self.nav_layout.insertWidget(position, btn)
            btn.setVisible(plugin_id not in self._hidden_plugins)
            position += 1

        # 当前停留的页面被隐藏时回到首页
        if self.current_plugin in self._hidden_plugins:
            self.switch_to_welcome()

        if hasattr(self, "welcome_page"):
            self.welcome_page.rebuild_feature_cards(
                [pid for pid in order if pid not in self._hidden_plugins])
            self.welcome_page.update_theme(self._current_theme)

    def _resolve_size(self, size):
        """解析尺寸配置，支持像素值或百分比（如(0.7, 0.8)表示70%宽、80%高）"""
        w, h = size
        screen = QApplication.primaryScreen().geometry()
        if isinstance(w, float) and isinstance(h, float):
            # 百分比：计算实际像素值
            return int(screen.width() * w), int(screen.height() * h)
        else:
            # 像素值：直接使用
            return w, h

    def switch_to_welcome(self):
        """切换到首页"""
        self.content.setCurrentIndex(0)
        self.current_plugin = None
        # 取消所有导航按钮的选中状态
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton):
                widget.setChecked(False)
        # 选中首页按钮
        self.home_btn.setChecked(True)

    def switch_plugin(self, plugin_id):
        # 被用户隐藏的导航项不可切入（防止程序化调用绕过可见性）
        if plugin_id in self._hidden_plugins:
            return
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton):
                widget.setChecked(widget.plugin_id() == plugin_id)

        # 取消首页按钮选中
        self.home_btn.setChecked(False)

        if plugin_id in self.plugins:
            plugin = self.plugins[plugin_id]
            if hasattr(plugin, 'scroll_area'):
                index = self.content.indexOf(plugin.scroll_area)
                if index >= 0:
                    self.content.setCurrentIndex(index)
                    self.current_plugin = plugin_id

    def _toggle_sidebar(self):
        """切换侧边栏展开/折叠"""
        if self._sidebar_animating:
            return
        sidebar_width = UI_CONFIG.get("sidebar_width", 260)
        if self.sidebar_expanded:
            # 折叠：宽度动画 + 子控件同步淡出
            self._animate_sidebar(sidebar_width, 0, False)
        else:
            # 展开：先宽度动画，完成后淡入子控件
            self._animate_sidebar(0, sidebar_width, True)

    def _set_sidebar_children_visible(self, visible):
        """设置侧边栏子控件可见性"""
        for w in self._sidebar_children:
            w.setVisible(visible)

    def _animate_sidebar(self, start, end, expand):
        """带动画切换侧边栏宽度（折叠时同步淡出子控件）"""
        self._sidebar_animating = True

        self.sidebar_anim = QParallelAnimationGroup(self)

        # —— 宽度动画 ——
        for prop in [b"minimumWidth", b"maximumWidth"]:
            anim = QPropertyAnimation(self.sidebar, prop)
            anim.setDuration(200)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.sidebar_anim.addAnimation(anim)

        # —— 折叠时同步淡出子控件 ——
        if not expand:
            for w in self._sidebar_children:
                effect = QGraphicsOpacityEffect(w)
                w.setGraphicsEffect(effect)
                anim = QPropertyAnimation(effect, b"opacity")
                anim.setDuration(150)
                anim.setStartValue(1.0)
                anim.setEndValue(0.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.sidebar_anim.addAnimation(anim)

        self.sidebar_anim.finished.connect(
            lambda e=expand: self._on_sidebar_animation_finished(e)
        )
        self.sidebar_anim.start()

    def _on_sidebar_animation_finished(self, expand):
        """侧边栏动画完成后的处理"""
        self.sidebar_expanded = expand

        if expand:
            # 重新锁定动画状态，防止淡入期间重复触发
            self._sidebar_animating = True
            # 设置可见后淡入
            self._set_sidebar_children_visible(True)
            self._expand_fadein_anims = QParallelAnimationGroup(self)
            for w in self._sidebar_children:
                effect = QGraphicsOpacityEffect(w)
                w.setGraphicsEffect(effect)
                anim = QPropertyAnimation(effect, b"opacity", self)
                anim.setDuration(150)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._expand_fadein_anims.addAnimation(anim)
            self._expand_fadein_anims.finished.connect(
                self._cleanup_expand_effects
            )
            self._expand_fadein_anims.start()
            self.sidebar_toggle_btn.setToolTip(t("sidebar.tooltip.collapse"))
        else:
            self._sidebar_animating = False
            # 子控件已在动画中淡出，此时彻底隐藏
            self._set_sidebar_children_visible(False)
            # 移除透明度效果，恢复常规渲染
            for w in self._sidebar_children:
                w.setGraphicsEffect(None)
            self.sidebar_toggle_btn.setToolTip(t("sidebar.tooltip.expand"))

        # 更新折叠态的按钮装饰线
        self._update_toggle_button_style()
        self._set_toggle_icon()

    def _cleanup_expand_effects(self):
        """淡入动画完成后清理 opacity effect，恢复常规渲染"""
        for w in self._sidebar_children:
            w.setGraphicsEffect(None)
        self._sidebar_animating = False

    def _get_favicon_path(self):
        """获取 favicon.ico 的路径，支持开发模式和打包模式"""
        if getattr(sys, 'frozen', False):
            # 打包模式：使用 PyInstaller 的 _MEIPASS 路径
            base_path = Path(sys._MEIPASS)
        else:
            # 开发模式：使用当前文件所在目录
            base_path = Path(__file__).parent
        return str(base_path / "favicon.ico")

    def _set_window_icon(self):
        """设置窗口图标，支持开发模式和打包模式"""
        icon_path = self._get_favicon_path()
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            # 同时设置应用程序图标
            if self._app:
                self._app.setWindowIcon(icon)

    def _create_chevron_icon(self, direction, color, size=24):
        """用 QPainter 绘制 chevron 箭头图标（含微妙的圆角容器背景）"""
        # 用更大尺寸绘制（分辨率 > setIconSize 的 22px），
        # 缩放后边缘更平滑（oversampling）
        draw_size = size + 4
        pixmap = QPixmap(draw_size, draw_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # —— 画圆角容器背景（pill / badge 样式）——
        bg_color = QColor(color)
        bg_color.setAlphaF(0.12)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)

        cw = draw_size - 4          # 容器宽
        ch = draw_size - 10         # 容器高
        cx = int((draw_size - cw) / 2)
        cy = int((draw_size - ch) / 2)
        painter.drawRoundedRect(cx, cy, cw, ch, 5, 5)

        # —— 画箭头主体 ——
        pen = QPen(QColor(color), 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()
        padding = 6
        mid = draw_size / 2
        if direction == 'left':
            path.moveTo(draw_size - padding, padding + 1)
            path.lineTo(padding + 1, mid)
            path.lineTo(draw_size - padding, draw_size - padding - 1)
        else:
            path.moveTo(padding + 1, padding + 1)
            path.lineTo(draw_size - padding, mid)
            path.lineTo(padding + 1, draw_size - padding - 1)

        painter.drawPath(path)
        painter.end()

        return QIcon(pixmap)

    def _set_toggle_icon(self, hover=False):
        """根据当前状态设置折叠按钮图标"""
        theme = self._current_theme
        # 默认用 primary 色（蓝色/紫色），hover 加亮
        color = theme['primary_hover'] if hover else theme['primary']
        direction = 'left' if self.sidebar_expanded else 'right'
        self.sidebar_toggle_btn.setIcon(
            self._create_chevron_icon(direction, color))

    def _update_toggle_button_style(self):
        """根据折叠/展开状态更新按钮样式"""
        theme = self._current_theme
        c = QColor(theme['primary'])
        hover_bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.12)"
        pressed_bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.22)"
        # 折叠态：左侧加 primary 色装饰线，提示可点击展开
        if self.sidebar_expanded:
            left_border = f"1px solid {theme['surface']}"
        else:
            left_border = f"2px solid {theme['primary']}"
        self.sidebar_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['bg_secondary']};
                border: none;
                border-left: {left_border};
                border-right: 1px solid {theme['surface']};
                border-radius: 0px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)

    def eventFilter(self, obj, event):
        """事件过滤器：用于折叠按钮悬停时图标颜色变化"""
        if obj is self.sidebar_toggle_btn:
            if event.type() == QEvent.Type.Enter:
                self._set_toggle_icon(hover=True)
            elif event.type() == QEvent.Type.Leave:
                self._set_toggle_icon(hover=False)
        return super().eventFilter(obj, event)

    def init_theme(self):
        """启动时从 INI 读取已保存主题应用；绝不写回（反覆盖旧 init_theme bug）"""
        theme_name = self.app_settings.get("general", "theme", "dark")
        theme = Theme.LIGHT if theme_name == "light" else Theme.DARK
        self.apply_theme(theme)

    @property
    def current_theme(self):
        """当前主题调色板（Theme.LIGHT / Theme.DARK）"""
        return self._current_theme

    def apply_theme(self, theme):
        self._current_theme = theme
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {theme['bg']}; }}
            QMenuBar {{ background-color: {theme['bg_secondary']}; color: {theme['text']}; }}
            QMenuBar::item {{ background: transparent; color: {theme['text']}; padding: 4px 10px; }}
            QMenuBar::item:selected {{ background-color: {theme['surface']}; }}
            QMenu {{
                background-color: {theme['bg_secondary']};
                color: {theme['text']};
                border: 1px solid {theme['surface']};
            }}
            QMenu::item {{ padding: 6px 20px; }}
            QMenu::item:selected {{ background-color: {theme['primary']}; color: white; }}
            QScrollArea {{ border: none; background-color: {theme['bg']}; }}
            QFrame#card {{
                background-color: {theme['bg_secondary']};
                border: 1px solid {theme['surface']};
                border-radius: 12px;
            }}
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
            QFrame#sidebarLine {{
                background-color: {theme['surface']};
            }}
        """)

        if hasattr(self, 'sidebar_toggle_btn'):
            self._update_toggle_button_style()
            self._set_toggle_icon()

        if hasattr(self, 'version_label'):
            self.version_label.setStyleSheet(
                f"color: {theme['text_secondary']}; font-size: {FONT_SIZE_12};"
            )

        if hasattr(self, 'logo_text'):
            self.logo_text.setStyleSheet(
                f"font-size: {FONT_SIZE_20}; font-weight: {FONT_WEIGHT_700}; color: {theme['text']};"
            )

        # 侧边栏导航按钮配色随主题更新（含首页与插件项）
        for nav_btn in self.findChildren(SidebarButton):
            nav_btn.apply_theme(theme)

        self.content.setStyleSheet(f"""
            QStackedWidget {{ background-color: {theme['bg']}; }}
        """)

        # 更新所有滚动区域的样式
        scrollbar_bg = theme['bg_secondary']
        scrollbar_handle = theme['surface']
        scrollbar_handle_hover = theme['text_secondary']
        viewport_bg = theme['bg']

        scroll_style = f"""
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{
                background: {scrollbar_bg}; width: 8px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scrollbar_handle}; min-height: 20px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {scrollbar_handle_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """

        viewport_style = f"background-color: {viewport_bg};"

        if hasattr(self, 'welcome_scroll'):
            self.welcome_scroll.setStyleSheet(scroll_style)
            self.welcome_scroll.viewport().setStyleSheet(viewport_style)

        for plugin_name, plugin in self.plugins.items():
            if hasattr(plugin, 'scroll_area'):
                plugin.scroll_area.setStyleSheet(scroll_style)
                plugin.scroll_area.viewport().setStyleSheet(viewport_style)
            if hasattr(plugin, 'update_theme'):
                plugin.update_theme(theme)

        # 更新欢迎页主题
        if hasattr(self, 'welcome_page') and hasattr(self.welcome_page, 'update_theme'):
            self.welcome_page.update_theme(theme)

    def setup_tray(self):
        self._tray_show_action = None
        self._tray_quit_action = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self)
            self.tray.setToolTip(t("tray.tooltip"))

            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "favicon.ico")
            if os.path.exists(icon_path):
                self.tray.setIcon(QIcon(icon_path))
            else:
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor("#6366f1"))
                self.tray.setIcon(QIcon(pixmap))

            menu = QMenu()
            self._tray_show_action = menu.addAction(t("tray.show"))
            self._tray_show_action.triggered.connect(self.show)
            self._tray_quit_action = menu.addAction(t("tray.quit"))
            self._tray_quit_action.triggered.connect(QApplication.quit)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()

    def setup_menu(self):
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu(t("menu.file"))
        self.exit_action = QAction(t("menu.exit"), self)
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.triggered.connect(QApplication.quit)
        self.file_menu.addAction(self.exit_action)

        self.tools_menu = menubar.addMenu(t("menu.tools"))
        self.settings_action = QAction(t("menu.settings"), self)
        self.settings_action.setShortcut('Ctrl+S')
        self.settings_action.triggered.connect(self.show_settings)
        self.tools_menu.addAction(self.settings_action)

        self.view_menu = menubar.addMenu(t("menu.view"))
        self.toggle_sidebar_action = QAction(t("menu.toggle_sidebar"), self)
        self.toggle_sidebar_action.setShortcut('Ctrl+B')
        self.toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        self.view_menu.addAction(self.toggle_sidebar_action)

    def show_settings(self):
        self.switch_plugin("settings")

    def retranslate_ui(self):
        """语言切换后重放主框架全部用户可见文本"""
        self.setWindowTitle(t("app.window_title", version=APP_VERSION))
        self.logo_text.setText(t("sidebar.logo_text"))
        self.home_btn.set_texts(t("sidebar.home"), "🏠")
        self.version_label.setText(t("sidebar.version", version=APP_VERSION))
        self.sidebar_toggle_btn.setToolTip(
            t("sidebar.tooltip.expand" if not self.sidebar_expanded else "sidebar.tooltip.collapse")
        )

        # 侧边栏插件按钮：按稳定 id 查词典
        for i in range(self.nav_layout.count()):
            widget = self.nav_layout.itemAt(i).widget()
            if isinstance(widget, SidebarButton) and widget.plugin_id() is not None:
                pid = widget.plugin_id()
                widget.set_texts(t(f"plugin.{pid}.name"), widget._icon_text)

        # 托盘（未托盘环境为 None）
        if getattr(self, "tray", None) is not None:
            self.tray.setToolTip(t("tray.tooltip"))
        if self._tray_show_action is not None:
            self._tray_show_action.setText(t("tray.show"))
        if self._tray_quit_action is not None:
            self._tray_quit_action.setText(t("tray.quit"))

        # 菜单
        self.file_menu.setTitle(t("menu.file"))
        self.exit_action.setText(t("menu.exit"))
        self.tools_menu.setTitle(t("menu.tools"))
        self.settings_action.setText(t("menu.settings"))
        self.view_menu.setTitle(t("menu.view"))
        self.toggle_sidebar_action.setText(t("menu.toggle_sidebar"))

        # 欢迎页与各插件（基类空实现兜底）
        if hasattr(self, "welcome_page"):
            self.welcome_page.retranslate_ui()
        for plugin in self.plugins.values():
            plugin.retranslate_ui()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        self.save_geometry()
        event.accept()

    def save_geometry(self):
        self.app_settings.set(
            "window", "geometry",
            bytes(self.saveGeometry().toBase64()).decode("ascii"),
        )
        self.app_settings.set(
            "window", "state",
            bytes(self.saveState().toBase64()).decode("ascii"),
        )
        self.app_settings.save()

    def load_geometry(self):
        from common.app_settings import bytes_to_qbytearray
        geometry = self.app_settings.get("window", "geometry", "")
        if geometry:
            self.restoreGeometry(bytes_to_qbytearray(geometry))
        state = self.app_settings.get("window", "state", "")
        if state:
            self.restoreState(bytes_to_qbytearray(state))
        if not geometry:
            self.apply_default_geometry()

    def apply_default_geometry(self):
        """窗口恢复为默认尺寸并居中（无已保存几何时使用）"""
        self.resize(1200, 800)
        self.move(
            QApplication.primaryScreen().geometry().center() -
            self.rect().center()
        )
