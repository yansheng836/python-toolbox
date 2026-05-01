"""
统一的消息框工具
所有插件使用此模块弹出消息，保证风格一致
"""


def get_parent(widget):
    """获取弹窗的 parent，统一处理 None 情况"""
    return widget if widget else None


def show_info(widget, title, message):
    """信息弹窗"""
    from PyQt6.QtWidgets import QMessageBox
    parent = get_parent(widget)
    QMessageBox.information(parent, title, message)


def show_warning(widget, title, message):
    """警告弹窗"""
    from PyQt6.QtWidgets import QMessageBox
    parent = get_parent(widget)
    QMessageBox.warning(parent, title, message)


def show_error(widget, title, message):
    """错误弹窗"""
    from PyQt6.QtWidgets import QMessageBox
    parent = get_parent(widget)
    QMessageBox.critical(parent, title, message)


def show_question(widget, title, message):
    """确认弹窗，返回 True（Yes）或 False（No/关闭）"""
    from PyQt6.QtWidgets import QMessageBox
    parent = get_parent(widget)
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes
