# -*- encoding: utf-8 -*-
"""
menu_system.py - Module for toolbox
"""

from PyQt6.QtWidgets import (QMainWindow, QMenu, QAction, QApplication)

from toolbox import Theme


class MenuSystem(QMainWindow):
    def __init__(self, theme=None):
        super().__init__()
        self.theme = theme or Theme.DARK
        self.setWindowTitle('工具箱 - 设置菜单示例')
        self.setMinimumSize(400, 300)
        self.apply_theme()

        # 添加菜单栏
        self.create_menu()

    def apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f'''QMainWindow {{
            background-color: {self.theme['bg']};
        }}
        QMenu {{
            background-color: {self.theme['bg_secondary']};
            color: {self.theme['text']};
        }}
        QMenu::item {{
            padding: 8px;
        }}
        QMenu::item:selected {{
            background-color: {self.theme['primary']};
        }}''')

    def create_menu(self):
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = QMenu('文件', self)
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = QMenu('工具', self)
        settings_action = QAction('设置', self)
        settings_action.setShortcut('Ctrl+S')
        settings_action.triggered.connect(self.show_settings)

        # 将菜单添加到菜单栏
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(tools_menu)

    def show_settings(self):
        print('设置页面展示功能')
        # 这里可以添加设置页面的实现

    def update_theme(self, theme):
        """更新主题"""
        self.theme = theme
        self.apply_theme()
