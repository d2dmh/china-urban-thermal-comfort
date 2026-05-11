"""
路径配置：所有外部数据和输出路径集中管理。
项目内部模块通过导入此文件获取路径，避免硬编码。

路径智能检测：优先使用项目内路径，如果不存在则回退到外部路径（向后兼容）。
"""

import os


# ================= 项目根目录 =================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================= 智能路径检测函数 =================

def get_data_path(new_path, old_path, path_type="directory"):
    """
    智能路径检测：优先使用新路径，不存在则回退到旧路径。

    Args:
        new_path: 项目内路径
        old_path: 外部路径（备用）
        path_type: "directory" 或 "file"

    Returns:
        实际可用的路径
    """
    if path_type == "directory":
        if os.path.isdir(new_path):
            return new_path
        elif os.path.isdir(old_path):
            return old_path
    else:  # file
        if os.path.isfile(new_path):
            return new_path
        elif os.path.isfile(old_path):
            return old_path

    # 都不存在，返回新路径（让后续代码报错时显示期望的路径）
    return new_path


# ================= 项目内数据路径（新）=================

DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
INPUT_DATA_ROOT = os.path.join(DATA_ROOT, "input data")
OTHER_DATA_ROOT = os.path.join(DATA_ROOT, "other data")


# ================= 外部输入数据路径（旧，备用）=================

# EnergyPlus 仿真结果根目录（旧路径，仅 27°C 数据）
SIMULATION_ROOT_OLD = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv"

# EPW 气象文件根目录（旧路径，备用）
EPW_ROOT_OLD = r"E:\BaiduNetdiskDownload\newcity"

# 建筑人口属性数据根目录（旧路径）
POPULATION_ROOT_OLD = r"E:\城市建筑_AOI_小区_POI_用途分类_人口结构_version4"

# Cluster 映射文件目录（旧路径）
CLUSTER_MAP_ROOT_OLD = r"E:\映射"


# ================= 动态路径构建（支持温度基准切换）=================

def get_simulation_root(temp_baseline):
    """
    根据温度基准获取仿真数据根目录。

    Args:
        temp_baseline: 温度基准（26 或 27）

    Returns:
        仿真数据根目录路径
    """
    from config.parameters import TEMP_BASELINE_DIRS
    baseline_dir = TEMP_BASELINE_DIRS.get(temp_baseline, "GeiMingHao_27Degree")

    # 新路径（项目内）
    new_path = os.path.join(INPUT_DATA_ROOT, baseline_dir, "GeiMingHao_IndoorEnv")

    # 旧路径（外部，仅 27°C）
    old_path = SIMULATION_ROOT_OLD if temp_baseline == 27 else None

    if old_path:
        return get_data_path(new_path, old_path, "directory")
    else:
        # 26°C 数据只在项目内，直接返回新路径
        return new_path


def get_strategy_dirs(temp_baseline):
    """
    获取三种策略对应的子文件夹。

    Args:
        temp_baseline: 温度基准（26 或 27）

    Returns:
        策略名 → 策略目录路径的字典
    """
    sim_root = get_simulation_root(temp_baseline)
    return {
        "现状": os.path.join(sim_root, "Baseline_2020"),
        "扩容": os.path.join(sim_root, "Capacity_expansion"),
        "定容": os.path.join(sim_root, "Fixed_capacity"),
    }


# ================= 导出的路径变量 =================

# EPW 气象文件根目录
EPW_ROOT_NEW = os.path.join(INPUT_DATA_ROOT, "epw_files")
EPW_ROOT = get_data_path(EPW_ROOT_NEW, EPW_ROOT_OLD, "directory")

# 建筑人口属性数据根目录
POPULATION_ROOT_NEW = os.path.join(OTHER_DATA_ROOT, "城市建筑_AOI_小区_POI_用途分类_人口结构_version4")
POPULATION_ROOT = get_data_path(POPULATION_ROOT_NEW, POPULATION_ROOT_OLD, "directory")

# Cluster 映射文件目录
CLUSTER_MAP_ROOT_NEW = os.path.join(OTHER_DATA_ROOT, "映射")
CLUSTER_MAP_ROOT = get_data_path(CLUSTER_MAP_ROOT_NEW, CLUSTER_MAP_ROOT_OLD, "directory")


# ================= 输出路径（项目内部，按温度基准分目录）=================

RESULTS_ROOT = os.path.join(PROJECT_ROOT, "results")


def get_set_output_dir(baseline):
    """Step 1 输出：SET 计算结果 + 夜间过热统计"""
    return os.path.join(RESULTS_ROOT, f"{baseline}Degree", "set_calculations")


def get_per_capita_output_dir(baseline):
    """Step 2 输出：人均不舒适小时数汇总表"""
    return os.path.join(RESULTS_ROOT, f"{baseline}Degree", "per_capita_hours")


def get_pivot_output_dir(baseline):
    """Step 3 输出：透视表"""
    return os.path.join(RESULTS_ROOT, f"{baseline}Degree", "pivot_tables")


def get_figures_dir(baseline=None):
    """图表输出目录"""
    if baseline:
        return os.path.join(RESULTS_ROOT, "figures", f"{baseline}Degree")
    return os.path.join(RESULTS_ROOT, "figures")


def ensure_output_dirs(baseline=None):
    """确保所有输出目录存在"""
    baselines = [baseline] if baseline else [26, 27]
    for b in baselines:
        for d in [get_set_output_dir(b), get_per_capita_output_dir(b),
                  get_pivot_output_dir(b)]:
            os.makedirs(d, exist_ok=True)
    os.makedirs(get_figures_dir(), exist_ok=True)
