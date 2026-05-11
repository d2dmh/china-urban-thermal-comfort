"""
Step 2：将 step1 的 SET 大表 + 建筑人口数据，合并计算
"人均不舒适小时数" (Hours/Resident) 指标。

核心逻辑：
- 对每个建筑：(楼层 SET>30 总和) × (该建筑/楼数组人口) / 楼层数  → 每居民贡献的小时数
- 对城市汇总：sum(每居民小时数) / sum(总人口)  =  Hours/Resident

输出：每个 (温度基准, 策略, 城市, 情景) 一行汇总，便于后续画图。
"""

import os
import sys
import re

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import (
    get_set_output_dir, get_per_capita_output_dir, POPULATION_ROOT,
    CLUSTER_MAP_ROOT, ensure_output_dirs, get_strategy_dirs,
)
from config.parameters import CITY_CONFIGS, SCENARIOS, SCENARIO_ORDER, BASELINES, SET_THRESHOLD
from src.core.city_matcher import parse_sheet_metadata


# ================= 人口数据加载 =================

def _read_csv_robust(path):
    for enc in ['gbk', 'utf-8-sig', 'utf-8']:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    raise ValueError(f"无法读取 {path}")


def build_population_lookup(city_conf):
    pinyin = city_conf['pinyin']
    chn_name = city_conf['chn_name']
    code = city_conf['code']
    prov_folder = city_conf['prov_folder']

    map_file = os.path.join(CLUSTER_MAP_ROOT, f"cluster_{code}_{chn_name}.csv")
    pop_filename = city_conf.get(
        'custom_pop_filename',
        f"T{code}_{chn_name}_building_pop_attributes.csv"
    )
    pop_file = os.path.join(POPULATION_ROOT, prov_folder, pop_filename)

    if not os.path.exists(pop_file):
        alt = os.path.join(POPULATION_ROOT, prov_folder,
                           f"{code}_{chn_name}_building_pop_attributes.csv")
        if os.path.exists(alt):
            pop_file = alt

    if not os.path.exists(map_file) or not os.path.exists(pop_file):
        print(f"   [ERROR] {chn_name}: 基础文件缺失，跳过")
        return None

    df_cluster = _read_csv_robust(map_file)
    df_pop = _read_csv_robust(pop_file)
    df_cluster.columns = df_cluster.columns.str.strip()
    df_pop.columns = df_pop.columns.str.strip()

    if 'landUseTyp' in df_cluster.columns:
        df_cluster['landUseTyp'] = df_cluster['landUseTyp'].astype(str).str.strip()
        df_cluster = df_cluster[df_cluster['landUseTyp'].str.startswith('Residential', na=False)].copy()

    for df in (df_cluster, df_pop):
        df['BuildingID'] = df['BuildingID'].astype(str).str.replace(r'\.0$', '', regex=True)

    merged = pd.merge(df_cluster, df_pop, on='BuildingID', how='inner')

    fnum_col = next((c for c in ['Fnum', 'Fnum_x', 'Fnum_y'] if c in merged.columns), None)
    if fnum_col is None:
        return None

    merged['Cluster'] = pd.to_numeric(merged['Cluster'], errors='coerce').fillna(0).astype(int)
    merged[fnum_col] = pd.to_numeric(merged[fnum_col], errors='coerce').fillna(0).astype(int)
    merged['popNum_2'] = pd.to_numeric(merged['popNum_2'], errors='coerce').fillna(0)

    lookup = (
        merged.groupby(['Cluster', fnum_col])['popNum_2']
        .sum()
        .reset_index()
        .rename(columns={fnum_col: 'Fnum', 'popNum_2': 'Total_Pop'})
    )
    return lookup


# ================= 单 (策略, 城市, 情景) 处理 =================

def process_single_excel(excel_path, pop_lookup):
    if not os.path.exists(excel_path):
        return None

    sum_person_hours = 0.0
    sum_total_pop = 0.0
    processed = set()

    try:
        xls = pd.ExcelFile(excel_path, engine='openpyxl')
    except Exception as e:
        print(f"      [ERROR] 打开失败 {os.path.basename(excel_path)}: {e}")
        return None

    for sheet_name in xls.sheet_names:
        meta = parse_sheet_metadata(sheet_name)
        if meta is None:
            continue
        _, cluster_id = meta

        base = re.sub(r'_\d+$', '', sheet_name)
        if base in processed:
            continue
        processed.add(base)

        df = pd.read_excel(xls, sheet_name=sheet_name)
        set_cols = [c for c in df.columns if str(c).endswith('_SET')]
        fnum = len(set_cols)
        if fnum == 0:
            continue

        match = pop_lookup[(pop_lookup['Cluster'] == cluster_id) &
                           (pop_lookup['Fnum'] == fnum)]
        if match.empty:
            continue
        total_pop = float(match['Total_Pop'].values[0])
        if total_pop <= 0:
            continue

        avg_pop_per_floor = total_pop / fnum
        sum_total_pop += total_pop

        for col in set_cols:
            uncomfortable_hours = (df[col] > SET_THRESHOLD).sum()
            if uncomfortable_hours > 0:
                sum_person_hours += avg_pop_per_floor * uncomfortable_hours

    xls.close()
    return sum_person_hours, sum_total_pop


# ================= 主流程 =================

def main():
    ensure_output_dirs()

    for baseline in BASELINES:
        set_output_dir = get_set_output_dir(baseline)
        per_capita_output_dir = get_per_capita_output_dir(baseline)
        os.makedirs(per_capita_output_dir, exist_ok=True)

        print("\n" + "=" * 70)
        print(f"  Step 2: 人均不舒适小时数 (Hours/Resident) [{baseline}°C]")
        print(f"  数据源: {set_output_dir}")
        print(f"  输出目录: {per_capita_output_dir}")
        print("=" * 70)

        all_results = []
        strategies = list(get_strategy_dirs(baseline).keys())

        for city_conf in CITY_CONFIGS:
            chn_name = city_conf['chn_name']
            pinyin = city_conf['pinyin']
            print(f"\n>> {chn_name} ({pinyin})")

            pop_lookup = build_population_lookup(city_conf)
            if pop_lookup is None:
                continue
            print(f"   人口字典: {len(pop_lookup)} 条 (Cluster, Fnum) 组合")

            for strategy in strategies:
                for scenario_label in SCENARIO_ORDER:
                    safe_label = scenario_label.replace(" ", "_")
                    excel_path = os.path.join(
                        set_output_dir, strategy, pinyin,
                        f"{pinyin}_{safe_label}_SET.xlsx"
                    )
                    if not os.path.exists(excel_path):
                        continue

                    res = process_single_excel(excel_path, pop_lookup)
                    if res is None:
                        continue
                    sum_ph, sum_pop = res
                    hours_per_resident = (sum_ph / sum_pop) if sum_pop > 0 else 0

                    city_label = pinyin.capitalize()[:-3]
                    all_results.append({
                        '温度基准': f"{baseline}°C",
                        '策略': strategy,
                        '城市': chn_name,
                        '城市拼音': pinyin,
                        '城市标签': city_label,
                        '情景': scenario_label,
                        'Total_Person_Hours': sum_ph,
                        'Total_Population': sum_pop,
                        'Hours_Per_Resident': hours_per_resident,
                    })
                    print(f"   {strategy} | {scenario_label}  →  "
                          f"Hours/Resident = {hours_per_resident:.2f}")

        if all_results:
            out_df = pd.DataFrame(all_results)
            out_path = os.path.join(per_capita_output_dir, "per_capita_hours_summary.csv")
            out_df.to_csv(out_path, index=False, encoding='utf-8-sig')
            out_xlsx = os.path.join(per_capita_output_dir, "per_capita_hours_summary.xlsx")
            out_df.to_excel(out_xlsx, index=False)
            print(f"\n>> [{baseline}°C] 已保存: {out_path}")
            print(f"   共 {len(out_df)} 行 (策略 × 城市 × 情景)")
        else:
            print(f"\n!! [{baseline}°C] 无结果生成。")


if __name__ == "__main__":
    main()
