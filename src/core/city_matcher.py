"""
城市标识符匹配工具：在拼音、中文、英文 EPW 关键字之间转换，
以及在 Excel sheet 名 / 文件名中提取楼层数和聚类编号。
"""

import re


def parse_sheet_metadata(sheet_name):
    """
    从 Excel sheet 名解析建筑类型、聚类编号。

    Sheet 名形如：'..._<building_type>_<cluster_id>_<其他>...'

    返回：
        (building_type, cluster_id) 或 None
    """
    match = re.search(r'_(\d+)_(\d+)_', sheet_name)
    if not match:
        return None
    try:
        return int(match.group(1)), int(match.group(2))
    except ValueError:
        return None


def get_storey_number(col_or_prefix):
    """
    从列名或前缀中提取楼层数字。

    匹配 'STOREY 0' / 'STOREY_0' / 'STOREY0' 等形式。
    """
    match = re.search(r'STOREY\s*_?\s*(\d+)', str(col_or_prefix), re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_unique_sheet_name(existing_names, base_name):
    """
    生成不超过 31 字符的唯一 Excel sheet 名，避免与已存在名字冲突。

    优先保留末尾的标识符（如 _<num>_<num>_<year>...）。
    """
    match = re.search(r'(_\d+_\d+_\d{4}.*)$', base_name)
    if match:
        suffix = match.group(1)
        prefix = base_name[:len(base_name) - len(suffix)]
        max_prefix_len = 31 - len(suffix)
        safe_name = prefix[:max_prefix_len] + suffix
    else:
        safe_name = base_name[:31]

    counter = 0
    new_name = safe_name
    while new_name in existing_names:
        counter += 1
        suffix_len = len(str(counter)) + 1
        new_name = safe_name[:31 - suffix_len] + f"_{counter}"
    return new_name
