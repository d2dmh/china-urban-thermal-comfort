"""
Step 1：扫描三策略×城市×情景目录，对每个建筑 CSV：
1. 与 EPW 大气压时间轴对齐
2. 筛选夜间 + HVAC 启用时段
3. 向量化计算各楼层的 SET
4. 统计 SET > 阈值的不舒适小时数

输出：
- 每个 (策略, 城市, 情景) 一个 Excel：每 sheet 是一个建筑的逐时 SET/RH
- 一个总 summary CSV：每行 (策略, 城市, 情景, 建筑, 楼层) 的不舒适小时数
"""

import os
# 必须最先设置（限制 Numba 多线程）
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import sys
import re
import glob
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

# 添加项目根到 sys.path 以便子模块导入
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import (
    get_strategy_dirs, EPW_ROOT, SET_OUTPUT_DIR, ensure_output_dirs,
)
from config.parameters import (
    MET, CLO, AIR_VELOCITY, RH_LIMIT, SET_THRESHOLD,
    NIGHT_HOURS, CITY_CONFIGS, SCENARIOS, MAX_WORKERS, TEMPERATURE_BASELINE,
)
from src.core.epw_handler import (
    extract_epw_pressure, get_epw_start_offset, find_epw_file,
)
from src.core.set_calculator import (
    calculate_constrained_rh, compute_set_vectorized, warm_up_numba,
)
from src.core.city_matcher import get_storey_number, get_unique_sheet_name


# ================= 单建筑处理（子进程执行）=================

def process_single_building(args):
    """
    处理单个建筑 CSV：返回 (summary_rows, hourly_dataframe, sheet_base_name)。

    summary_rows: list[dict]，每楼层一行的不舒适小时数统计
    hourly_dataframe: DataFrame，逐时 SET/RH 大表
    sheet_base_name: 写入 Excel 时使用的 sheet 基础名
    """
    csv_file, strategy, city_pinyin, scenario_label, scenario_keyword, epw_pressure = args

    try:
        # 读取 CSV（兼容 utf-8 / gbk）
        try:
            df = pd.read_csv(csv_file, low_memory=False, encoding='utf-8', engine='c')
        except Exception:
            df = pd.read_csv(csv_file, low_memory=False, encoding='gbk', engine='c')

        if len(df) == 0 or len(epw_pressure) == 0:
            return None, None, None

        # ---- 时间轴对齐：将 EPW 大气压裁切到与 CSV 起始日期对齐 ----
        start_date_str = str(df.iloc[0, 0])
        start_idx = get_epw_start_offset(start_date_str)
        end_idx = start_idx + len(df)
        pressure = epw_pressure[start_idx:end_idx]

        min_len = min(len(df), len(pressure))
        if min_len == 0:
            return None, None, None
        df = df.iloc[:min_len].reset_index(drop=True)
        pressure = pressure[:min_len]

        # ---- 筛选夜间 + HVAC 开启 + 制冷期 ----
        # 提取小时
        try:
            hours = df.iloc[:, 0].astype(str).str.strip().str.extract(r'(\d{2}):00:00')[0].astype(int)
        except Exception:
            return None, None, None

        # EnergyPlus 中 24:00 表示当天结束（即次日 0:00），统一处理
        night_mask = hours.isin([h if h != 24 else 0 for h in NIGHT_HOURS]) | hours.isin(NIGHT_HOURS)

        cool_cols = [c for c in df.columns if "COOLING_PERIOD_SCHEDULE" in c]
        hvac_cols = [c for c in df.columns if "HVAC_CONDITIONEDTIME_SCHEDULE" in c]
        sched_mask = pd.Series([True] * len(df))
        if cool_cols and hvac_cols:
            sched_mask = (df[cool_cols[0]] > 0) & (df[hvac_cols[0]] > 0)

        final_mask = night_mask & sched_mask
        if final_mask.sum() == 0:
            return None, None, None

        df_f = df[final_mask].copy().reset_index(drop=True)
        pressure_f = pressure[final_mask.values]

        # ---- 各楼层向量化计算 SET ----
        temp_cols = [c for c in df_f.columns if "Zone Air Temperature" in c]
        prefixes = sorted(set(c.split(":Zone Air Temperature")[0] for c in temp_cols),
                          key=lambda p: get_storey_number(p) or 99999)

        out = pd.DataFrame()
        out['Date/Time'] = df_f.iloc[:, 0].values
        out['Outdoor_Pressure_Pa'] = pressure_f

        summary_rows = []
        building_id = os.path.basename(csv_file).replace('.csv', '')

        for prefix in prefixes:
            try:
                col_ta = next(c for c in df_f.columns
                              if c.startswith(f"{prefix}:") and "Zone Air Temperature" in c)
                col_mrt = next(c for c in df_f.columns
                               if c.startswith(f"{prefix}:") and "Mean Radiant Temperature" in c)
                col_hr = next(c for c in df_f.columns
                              if c.startswith(f"{prefix}:") and "Humidity Ratio" in c)
            except StopIteration:
                continue

            tdb = df_f[col_ta].values.astype(float)
            tr = df_f[col_mrt].values.astype(float)
            w = df_f[col_hr].values.astype(float)

            rh = calculate_constrained_rh(tdb, w, pressure_f, RH_LIMIT)
            set_vals = compute_set_vectorized(tdb, tr, AIR_VELOCITY, rh, MET, CLO)

            storey_num = get_storey_number(prefix)
            simple_name = f"STOREY_{storey_num}" if storey_num is not None else prefix[-10:].replace(" ", "_")

            out[f"{simple_name}_SET"] = set_vals
            out[f"{simple_name}_RH"] = rh

            # 统计该楼层的夜间不舒适小时数
            uncomfortable_hours = int(np.nansum(set_vals > SET_THRESHOLD))
            summary_rows.append({
                '策略': strategy,
                '城市': city_pinyin,
                '情景': scenario_label,
                '建筑ID': building_id,
                '楼层': simple_name,
                '夜间总时数': len(set_vals),
                '不舒适小时数': uncomfortable_hours,
            })

        if not summary_rows:
            return None, None, None

        return summary_rows, out, building_id

    except Exception as e:
        print(f"   ❌ 处理失败 {os.path.basename(csv_file)}: {e}")
        return None, None, None


# ================= 主流程 =================

def build_task_list():
    """
    扫描三策略目录，构建 (csv_file, strategy, city_pinyin, scenario_label,
    scenario_keyword, epw_pressure) 任务列表。

    EPW 大气压数据按 (city, scenario) 缓存复用。
    """
    tasks = []
    epw_cache = {}

    # 获取当前温度基准对应的策略目录
    strategy_dirs = get_strategy_dirs()

    for strategy_zh, strategy_dir in strategy_dirs.items():
        if not os.path.isdir(strategy_dir):
            print(f"!! 策略目录不存在: {strategy_dir}")
            continue

        for city_folder in os.listdir(strategy_dir):
            city_path = os.path.join(strategy_dir, city_folder)
            if not os.path.isdir(city_path):
                continue

            # 找到该城市的配置项以便取 epw_keyword
            city_conf = next(
                (c for c in CITY_CONFIGS if c['pinyin'] == city_folder),
                None
            )
            if city_conf is None:
                continue

            for scenario_folder in os.listdir(city_path):
                scenario_path = os.path.join(city_path, scenario_folder)
                if not os.path.isdir(scenario_path):
                    continue

                # 匹配该子文件夹对应的情景标签
                scenario_label = None
                scenario_keyword = None
                for label, keyword in SCENARIOS.items():
                    if keyword.lower() in scenario_folder.lower():
                        scenario_label = label
                        scenario_keyword = keyword
                        break
                if scenario_label is None:
                    continue

                # 加载 EPW 大气压（按城市+情景缓存）
                cache_key = (city_folder, scenario_keyword)
                if cache_key not in epw_cache:
                    epw_file = find_epw_file(EPW_ROOT, scenario_keyword,
                                             city_conf['epw_keyword'])
                    epw_cache[cache_key] = (
                        extract_epw_pressure(epw_file)
                        if epw_file else np.full(8760, 101325.0)
                    )
                pressure = epw_cache[cache_key]

                # 收集 CSV 文件（排除 _SET_Result 和 _dup 副本）
                csv_files = glob.glob(os.path.join(scenario_path, "*.csv"))
                csv_files = [
                    f for f in csv_files
                    if "_SET_Result" not in f and not re.search(r'_dup\d*', os.path.basename(f), re.IGNORECASE)
                ]

                for csv_file in csv_files:
                    tasks.append((
                        csv_file, strategy_zh, city_folder,
                        scenario_label, scenario_keyword, pressure
                    ))

    return tasks


def main():
    ensure_output_dirs()
    print("=" * 70)
    print("  Step 1: SET 计算 + 夜间过热统计")
    print(f"  温度基准: {TEMPERATURE_BASELINE}°C")
    print(f"  输出目录: {SET_OUTPUT_DIR}")
    print("=" * 70)

    print(">> 主进程预热 Numba 缓存...")
    warm_up_numba()
    print(">> 预热完成。")

    print(">> 扫描任务列表...")
    tasks = build_task_list()
    print(f"   共发现 {len(tasks)} 个建筑文件待处理")
    if not tasks:
        print("!! 没有任务可执行，退出。")
        return

    # 按 (策略, 城市, 情景) 分组，每组一个 Excel
    excel_buffers = {}
    all_summary = []
    safe_workers = min(MAX_WORKERS, os.cpu_count() or 2)

    print(f">> 启动 {safe_workers} 个并行进程...")
    start = time.time()

    with ProcessPoolExecutor(max_workers=safe_workers) as executor:
        futures = {executor.submit(process_single_building, t): t for t in tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            summary_rows, out_df, building_id = future.result()
            if summary_rows is None:
                continue
            task = futures[future]
            _, strategy, city, scenario_label, _, _ = task
            group_key = (strategy, city, scenario_label)
            excel_buffers.setdefault(group_key, []).append((building_id, out_df))
            all_summary.extend(summary_rows)

            if done % 20 == 0 or done == len(tasks):
                print(f"   进度: {done}/{len(tasks)}  耗时 {time.time()-start:.1f}s")

    # 写出 Excel
    print("\n>> 写入逐时 SET Excel 文件...")
    for (strategy, city, scenario_label), buildings in excel_buffers.items():
        out_dir = os.path.join(SET_OUTPUT_DIR, strategy, city)
        os.makedirs(out_dir, exist_ok=True)
        safe_label = scenario_label.replace(" ", "_")
        excel_path = os.path.join(out_dir, f"{city}_{safe_label}_SET.xlsx")
        try:
            with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                used = set()
                for building_id, df in buildings:
                    sheet_name = get_unique_sheet_name(used, building_id)
                    used.add(sheet_name)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"   [OK] {excel_path}  ({len(buildings)} sheets)")
        except Exception as e:
            print(f"   [ERROR] 写入失败 {excel_path}: {e}")

    # 写出总 summary
    if all_summary:
        summary_df = pd.DataFrame(all_summary)
        summary_path = os.path.join(SET_OUTPUT_DIR, "summary_uncomfortable_hours.csv")
        summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
        print(f"\n>> 总汇总表: {summary_path}  ({len(summary_df)} 行)")

    print(f"\n>> Step 1 完成。总耗时 {time.time()-start:.1f}s")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
