# -*- encoding: utf-8 -*-
"""
main.py - Module for toolbox
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from common.app_settings import AppSettings, setup_app_identity
from common import i18n
from common.i18n import install_qt_translator
from toolbox import ToolboxWindow


def main():
    # 启动顺序（设计文档 §7.3，顺序不可调换）：
    # migrate_from_qsettings 必须紧跟 AppSettings 构造——首次构造落盘默认值后
    # _explicit_keys 仍为空，注册表值得以导入；INI 已存在时迁移不会覆盖已保存值
    app = QApplication(sys.argv)
    setup_app_identity(app)
    settings = AppSettings()
    settings.migrate_from_qsettings()

    code = settings.get("general", "language", i18n.DEFAULT_LANGUAGE)
    i18n.set_language(code)
    install_qt_translator(app, code)

    window = ToolboxWindow(app, settings=settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
