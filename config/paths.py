"""
路径配置：所有外部数据和输出路径集中管理。
项目内部模块通过导入此文件获取路径，避免硬编码。
"""

import os

# ================= 项目根目录 =================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================= 外部输入数据路径 =================

# EnergyPlus 仿真结果根目录（包含三种策略子文件夹）
SIMULATION_ROOT = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv"

# 三种策略对应的子文件夹
STRATEGY_DIRS = {
    "现状": os.path.join(SIMULATION_ROOT, "Baseline_2020"),
    "扩容": os.path.join(SIMULATION_ROOT, "Capacity_expansion"),
    "定容": os.path.join(SIMULATION_ROOT, "Fixed_capacity"),
}

# EPW 气象文件根目录（按情景子文件夹组织）
EPW_ROOT = r"E:\BaiduNetdiskDownload\newcity"

# 建筑人口属性数据根目录
POPULATION_ROOT = r"E:\城市建筑_AOI_小区_POI_用途分类_人口结构_version4"

# Cluster 映射文件目录（cluster_<code>_<城市名>.csv）
CLUSTER_MAP_ROOT = r"E:\映射"


# ================= 输出路径（项目内部）=================

RESULTS_ROOT = os.path.join(PROJECT_ROOT, "results")

# Step 1 输出：SET 计算结果 + 夜间过热统计
SET_OUTPUT_DIR = os.path.join(RESULTS_ROOT, "set_calculations")

# Step 2 输出：人均不舒适小时数汇总表
PER_CAPITA_OUTPUT_DIR = os.path.join(RESULTS_ROOT, "per_capita_hours")

# 图表输出目录
FIGURES_DIR = os.path.join(RESULTS_ROOT, "figures")


def ensure_output_dirs():
    """确保所有输出目录存在"""
    for d in [SET_OUTPUT_DIR, PER_CAPITA_OUTPUT_DIR, FIGURES_DIR]:
        os.makedirs(d, exist_ok=True)
