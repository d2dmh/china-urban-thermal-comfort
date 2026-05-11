"""
Step 3：从 Step 1 的 SET Excel 文件生成透视表。

输出（每个温度基准各一份）：
- hourly_set_detail.csv：逐时 SET 明细（因行数巨大，用 CSV）
- annual_uncomfortable_summary.xlsx：每建筑每楼层的不舒适小时汇总
"""

import os
import sys
import csv

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.paths import get_set_output_dir, get_pivot_output_dir, ensure_output_dirs
from config.parameters import BASELINES, SET_THRESHOLD


def process_baseline(baseline):
    set_dir = get_set_output_dir(baseline)
    pivot_dir = get_pivot_output_dir(baseline)
    os.makedirs(pivot_dir, exist_ok=True)

    hourly_path = os.path.join(pivot_dir, "hourly_set_detail.csv")
    annual_path = os.path.join(pivot_dir, "annual_uncomfortable_summary.xlsx")

    print(f"\n{'='*70}")
    print(f"  Step 3: 透视表 [{baseline}°C]")
    print(f"  数据源: {set_dir}")
    print(f"  输出: {pivot_dir}")
    print(f"{'='*70}")

    annual_rows = []
    hourly_count = 0

    with open(hourly_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['温度基准', '城市', '策略', '情景', '建筑ID', '楼层',
                         'Date/Time', 'SET', 'RH', 'Outdoor_Pressure_Pa'])

        for strategy in os.listdir(set_dir):
            strategy_path = os.path.join(set_dir, strategy)
            if not os.path.isdir(strategy_path):
                continue

            for city in os.listdir(strategy_path):
                city_path = os.path.join(strategy_path, city)
                if not os.path.isdir(city_path):
                    continue

                for fname in os.listdir(city_path):
                    if not fname.endswith('_SET.xlsx'):
                        continue

                    excel_path = os.path.join(city_path, fname)
                    # 从文件名解析情景：{city}_{scenario}_SET.xlsx
                    scenario_label = fname.replace(city + '_', '').replace('_SET.xlsx', '').replace('_', ' ')

                    try:
                        xls = pd.ExcelFile(excel_path, engine='openpyxl')
                    except Exception as e:
                        print(f"   [ERROR] 打开失败 {fname}: {e}")
                        continue

                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(xls, sheet_name=sheet_name)
                        building_id = sheet_name

                        set_cols = [c for c in df.columns if str(c).endswith('_SET')]
                        rh_cols = [c for c in df.columns if str(c).endswith('_RH')]

                        if not set_cols:
                            continue

                        # 逐时明细：每个楼层展开一行
                        for set_col in set_cols:
                            floor = set_col.replace('_SET', '')
                            rh_col = f"{floor}_RH"
                            rh_vals = df[rh_col].values if rh_col in df.columns else [None] * len(df)

                            # 统计不舒适小时数
                            set_vals = df[set_col].values
                            uncomfortable = int((set_vals > SET_THRESHOLD).sum())

                            annual_rows.append({
                                '温度基准': f"{baseline}°C",
                                '城市': city,
                                '策略': strategy,
                                '情景': scenario_label,
                                '建筑ID': building_id,
                                '楼层': floor,
                                '夜间总时数': len(set_vals),
                                '不舒适小时数(SET>30)': uncomfortable,
                            })

                            # 写入逐时数据
                            for i in range(len(df)):
                                writer.writerow([
                                    f"{baseline}°C", city, strategy, scenario_label,
                                    building_id, floor,
                                    df.iloc[i, 0],  # Date/Time
                                    set_vals[i] if not pd.isna(set_vals[i]) else '',
                                    rh_vals[i] if not (isinstance(rh_vals[i], float) and (pd.isna(rh_vals[i]) if hasattr(pd, 'isna') else False)) else '',
                                    df['Outdoor_Pressure_Pa'].iloc[i] if 'Outdoor_Pressure_Pa' in df.columns else '',
                                ])
                                hourly_count += 1

                    xls.close()
                    print(f"   [OK] {strategy}/{city}/{fname}")

    print(f"\n   逐时明细: {hourly_count} 行 → {hourly_path}")

    if annual_rows:
        df_annual = pd.DataFrame(annual_rows)
        df_annual.to_excel(annual_path, index=False)
        print(f"   年度汇总: {len(df_annual)} 行 → {annual_path}")


def main():
    ensure_output_dirs()
    for baseline in BASELINES:
        set_dir = get_set_output_dir(baseline)
        if not os.path.isdir(set_dir):
            print(f"!! [{baseline}°C] 数据目录不存在，跳过: {set_dir}")
            continue
        process_baseline(baseline)

    print("\n>> Step 3 完成。")


if __name__ == "__main__":
    main()
