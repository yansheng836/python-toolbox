# -*- encoding: utf-8 -*-
"""
统一的消息框工具
所有插件使用此模块弹出消息，保证风格一致
"""

from PyQt6.QtWidgets import QMessageBox

from toolbox import Theme


def _apply_style(msg_box, theme=None):
    """
    为消息框应用统一样式
    设置白色背景和深色文字，按钮用主题色
    """
    if theme is None:
        theme = Theme.LIGHT
    msg_box.setStyleSheet(f"""
        QMessageBox {{
            background-color: {theme['bg']};
            color: {theme['text']};
        }}
        QMessageBox QLabel {{
            color: {theme['text']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {theme['primary']};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 20px;
            font-weight: 600;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {theme['primary_hover']};
            color: #ffffff;
        }}
    """)


def show_info(widget, title, message, theme=None):
    """信息弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg, theme)
    msg.exec()


def show_warning(widget, title, message, theme=None):
    """警告弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg, theme)
    msg.exec()


def show_error(widget, title, message, theme=None):
    """错误弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg, theme)
    msg.exec()


def show_question(widget, title, message, theme=None):
    """确认弹窗，返回 True（Yes）或 False（No/关闭）"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    _apply_style(msg, theme)
    reply = msg.exec()
    return reply == QMessageBox.StandardButton.Yes
