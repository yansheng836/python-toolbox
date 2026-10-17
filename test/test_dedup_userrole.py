# -*- encoding: utf-8 -*-
"""去重子节点文件路径存 UserRole，不依赖显示文本"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem


def test_sort_by_rule_uses_userrole(qapp):
    from plugins.file_deduplicator import FileDeduplicator
    from toolbox import Theme

    plugin = FileDeduplicator.__new__(FileDeduplicator)
    plugin.icon = "🧹"
    plugin.name = "文件去重"
    plugin.description = ""
    plugin.theme = Theme.DARK
    plugin.current_theme = Theme.DARK
    widget = plugin.create_ui()

    # 构造一个重复组：父节点带 hash，两个子节点带 UserRole 路径
    widget.duplicates = {"hash123": ["/a/x.jpg", "/a/y.jpg"]}
    tree = widget.results_tree
    tree.clear()
    parent = QTreeWidgetItem(tree)
    parent.setData(0, Qt.ItemDataRole.UserRole, "hash123")
    # 显示文本模拟翻译后的前缀（P3 状态），UserRole 仍存原始路径
    c1 = QTreeWidgetItem(parent)
    c1.setText(0, "✅ Keep: /a/x.jpg")
    c1.setData(0, Qt.ItemDataRole.UserRole, "/a/x.jpg")
    c2 = QTreeWidgetItem(parent)
    c2.setText(0, "❌ Del: /a/y.jpg")
    c2.setData(0, Qt.ItemDataRole.UserRole, "/a/y.jpg")

    # 规则 index 2：按文件名升序，保留首个（按 basename 排序，无需真实文件）
    widget.rule_combo.setCurrentIndex(2)
    widget._sort_by_rule()

    # 重建后子节点仍可通过 UserRole 拿到路径（不依赖显示文本前缀）
    paths = [parent.child(i).data(0, Qt.ItemDataRole.UserRole)
             for i in range(parent.childCount())]
    assert "/a/x.jpg" in paths
    assert "/a/y.jpg" in paths
    # 排序与保留/删除标记按 UserRole 中的路径完成，而非显示前缀反解析
    assert parent.child(0).text(0) == "✅ 保留: /a/x.jpg"
    assert parent.child(1).text(0) == "❌ 删除: /a/y.jpg"
