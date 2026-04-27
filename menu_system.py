from PyQt6.QtWidgets import (QMainWindow, QMenu, QAction, QApplication)


class MenuSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('工具箱 - 设置菜单示例')
        self.setMinimumSize(400, 300)
        self.setStyleSheet('''QMainWindow {
            background-color: #0f1729;
        }
        QMenu {
            background-color: #1e293b;
            color: #f1f5f9;
        }
        QMenu::item {
            padding: 8px;
        }
        QMenu::item:selected {
            background-color: #6366f1;
        }''')

        # 添加菜单栏
        self.create_menu()

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
