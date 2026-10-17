# -*- encoding: utf-8 -*-
"""列定义稳定 id 与列宽键一致性"""

from common.utils import IMAGE_COLUMNS, PDF_COLUMNS, Column
from common.file_list_panel import FileListPanel


def test_columns_are_column_namedtuple():
    for col in IMAGE_COLUMNS + PDF_COLUMNS:
        assert isinstance(col, Column), f"{col} 不是 Column"
        assert col.id
        assert callable(col.func)


def test_column_ids_unique():
    # id 在每个列定义列表内唯一（列宽按 id 在单表内匹配）
    for cols in (IMAGE_COLUMNS, PDF_COLUMNS):
        ids = [c.id for c in cols]
        assert len(ids) == len(set(ids)), f"列 id 重复: {ids}"


def test_default_widths_keyed_by_id():
    for cid, _ in FileListPanel.DEFAULT_COLUMN_WIDTHS.items():
        assert isinstance(cid, str)
        # 每个默认列宽键都能在某列定义中找到
        all_ids = [c.id for c in IMAGE_COLUMNS + PDF_COLUMNS] + [
            "filename", "size", "pages", "dimensions", "created", "modified"
        ]
        assert cid in all_ids, f"默认列宽键未对应任何列: {cid}"


def test_file_panel_accepts_legacy_tuple(qapp):
    # 旧式 (label, func) 元组仍能工作（向后兼容）
    import os
    panel = FileListPanel(columns=[("文件名", lambda f: os.path.basename(f))])
    assert panel.table.columnCount() == 1
