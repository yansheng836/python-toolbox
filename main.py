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
from common.message_utils import show_info, show_warning
from toolbox import ToolboxWindow


def resolve_startup_language(settings):
    """确定启动语言：已有保存值则沿用，首次启动按系统语言初始化并写回

    is_explicit 为 False 说明 language 键只是 load() 填充的默认值，
    尚未经用户选择，此时用系统语言覆盖并持久化，之后以用户选择为准。

    返回 (语言代码, 是否为首次启动自动检测)。
    """
    if settings.is_explicit("setting", "language"):
        return settings.get("setting", "language", i18n.DEFAULT_LANGUAGE), False

    code = i18n.detect_system_language()
    settings.set("setting", "language", code)
    try:
        settings.save()
    except OSError as e:
        # 此时 QApplication 已创建，可用弹窗替代 print 保证用户可见
        show_warning(
            None, i18n.t("app.dialog.warning_title"),
            i18n.t("common.error.config_write", error=e))
    return code, True


def main():
    # 启动顺序（设计文档 §7.3，顺序不可调换）：
    # migrate_from_qsettings 必须紧跟 AppSettings 构造——首次构造落盘默认值后
    # _explicit_keys 仍为空，注册表值得以导入；INI 已存在时迁移不会覆盖已保存值
    app = QApplication(sys.argv)
    setup_app_identity(app)
    settings = AppSettings()
    settings.migrate_from_qsettings()

    code, auto_detected = resolve_startup_language(settings)
    i18n.set_language(code)
    install_qt_translator(app, code)

    window = ToolboxWindow(app, settings=settings)
    window.show()

    if auto_detected:
        show_info(
            window,
            i18n.t("settings.dialog.auto_language_title"),
            i18n.t(
                "settings.dialog.auto_language_message",
                language=i18n.LANGUAGES[code],
            ),
            theme=window.current_theme,
        )
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
