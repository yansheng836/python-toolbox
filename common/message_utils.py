"""
统一的消息框工具
所有插件使用此模块弹出消息，保证风格一致
"""

from PyQt6.QtWidgets import QMessageBox


def _apply_style(msg_box):
    """
    为消息框应用统一样式
    只设置按钮样式（背景用主题色、文字白色），背景和文字交给系统/主题处理
    """
    msg_box.setStyleSheet("""
        QMessageBox QPushButton {
            background-color: #4f46e5;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 20px;
            font-weight: 600;
        }
        QMessageBox QPushButton:hover {
            background-color: #4338ca;
        }
    """)


def show_info(widget, title, message):
    """信息弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg)
    msg.exec()


def show_warning(widget, title, message):
    """警告弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg)
    msg.exec()


def show_error(widget, title, message):
    """错误弹窗"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    _apply_style(msg)
    msg.exec()


def show_question(widget, title, message):
    """确认弹窗，返回 True（Yes）或 False（No/关闭）"""
    parent = widget if widget else None
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    _apply_style(msg)
    reply = msg.exec()
    return reply == QMessageBox.StandardButton.Yes
