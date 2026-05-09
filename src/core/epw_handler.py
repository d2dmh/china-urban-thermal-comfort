"""
EPW 气象文件处理：读取大气压、时间轴对齐。
"""

import os
import re
import glob
import numpy as np
import pandas as pd


def extract_epw_pressure(epw_file):
    """
    从 EPW 文件中提取逐时大气压（全年 8760 小时）。

    EPW 文件前 8 行是元数据，第 9 列是大气压（Pa）。
    """
    try:
        epw_data = pd.read_csv(epw_file, skiprows=8, header=None,
                               encoding='utf-8', engine='python', usecols=[9])
        return epw_data.iloc[:, 0].values.astype(float)
    except Exception:
        # 标准大气压回退值
        return np.full(8760, 101325.0)


def get_epw_start_offset(date_str):
    """
    根据 EnergyPlus 的日期字符串（如 ' 05/01  01:00:00'）计算其在
    全年 8760 小时序列中的起始小时索引。

    用于将 CSV 仿真数据（可能从年中开始）与 EPW 全年大气压对齐。
    """
    try:
        match = re.search(r'(\d{2})/(\d{2})', str(date_str))
        if not match:
            return 0
        month, day = int(match.group(1)), int(match.group(2))
        # EPW 平年处理
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        past_days = sum(days_in_month[:month]) + (day - 1)
        return past_days * 24
    except Exception:
        return 0


def find_epw_file(epw_root, scenario_keyword, city_epw_keyword):
    """
    在 EPW 根目录下按情景子文件夹和城市关键字查找 EPW 文件。

    参数：
        epw_root: EPW 根目录
        scenario_keyword: 情景关键字（如 '2020', '2040-rcp2.6'）
        city_epw_keyword: 城市英文关键字（如 'BEIJING', 'SHENZHENSHI'）
    """
    scenario_dir = os.path.join(epw_root, scenario_keyword)
    if not os.path.exists(scenario_dir):
        scenario_dir = epw_root

    # 优先匹配同时包含城市和情景的文件
    patterns = [
        os.path.join(scenario_dir, f"*{city_epw_keyword}*{scenario_keyword}*.epw"),
        os.path.join(scenario_dir, f"*{city_epw_keyword}*.epw"),
    ]

    for pattern in patterns:
        matched = glob.glob(pattern)
        if matched:
            return matched[0]

    return None
