# -*- encoding: utf-8 -*-
"""
统一的文件对话框工具
所有插件使用此模块弹出文件对话框，保证风格一致
"""

from PyQt6.QtWidgets import QFileDialog
from toolbox import Theme


def _get_dialog_style(theme=None):
    """返回文件对话框的统一样式"""
    if theme is None:
        theme = Theme.LIGHT
    return f"""
        QFileDialog {{
            background-color: {theme['bg_secondary']};
        }}
        QFileDialog QWidget {{
            background-color: {theme['bg_secondary']};
            color: {theme['text']};
        }}
        QFileDialog QLineEdit {{
            background-color: {theme['bg']};
            color: {theme['text']};
            border: 1px solid {theme['border']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QFileDialog QPushButton {{
            background-color: {theme['primary']};
            color: {theme['text']};
            border: none;
            border-radius: 6px;
            padding: 6px 20px;
            font-weight: 600;
        }}
        QFileDialog QPushButton:hover {{
            background-color: {theme['primary_hover']};
        }}
        QFileDialog QListView, QFileDialog QTreeView {{
            background-color: {theme['bg_secondary']};
            color: {theme['text']};
        }}
    """


def get_save_file_name(parent, title, directory="", filter_str="", options=None, theme=None):
    """
    弹出"保存文件"对话框
    参数与 QFileDialog.getSaveFileName 类似，返回选中的文件路径（为空则用户取消）
    """
    file_dialog = QFileDialog(parent)
    file_dialog.setWindowTitle(title)
    file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    if filter_str:
        file_dialog.setNameFilter(filter_str)
    if directory:
        file_dialog.setDirectory(directory)
    if options:
        file_dialog.setOptions(options)
    file_dialog.setStyleSheet(_get_dialog_style(theme))
    if file_dialog.exec():
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            return selected_files[0]
    return ""


def get_existing_directory(parent, title, directory="", options=None, theme=None):
    """
    弹出"选择目录"对话框
    参数与 QFileDialog.getExistingDirectory 类似，返回选中的目录路径（为空则用户取消）
    """
    file_dialog = QFileDialog(parent)
    file_dialog.setWindowTitle(title)
    file_dialog.setFileMode(QFileDialog.FileMode.Directory)
    file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    if directory:
        file_dialog.setDirectory(directory)
    if options:
        file_dialog.setOptions(options)
    file_dialog.setStyleSheet(_get_dialog_style(theme))
    if file_dialog.exec():
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            return selected_files[0]
    return ""


def get_open_file_names(parent, title, directory="", filter_str="", options=None, theme=None):
    """
    弹出"打开文件"对话框（多选）
    返回选中的文件路径列表（为空则用户取消）
    """
    file_dialog = QFileDialog(parent)
    file_dialog.setWindowTitle(title)
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    if filter_str:
        file_dialog.setNameFilter(filter_str)
    if directory:
        file_dialog.setDirectory(directory)
    if options:
        file_dialog.setOptions(options)
    file_dialog.setStyleSheet(_get_dialog_style(theme))
    if file_dialog.exec():
        return file_dialog.selectedFiles()
    return []
