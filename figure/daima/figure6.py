import os
import glob
import pandas as pd
import numpy as np
import warnings

# 忽略 pandas 解析时的常规警告，保持终端输出整洁
warnings.filterwarnings('ignore')

# ================= 1. 核心路径配置 =================
ROOT_ENERGY = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_Energy"
ROOT_SCHEDULE = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv"
ROOT_CAPA = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_Capacity"
ROOT_POP_LOOKUP = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv\result\对比\Result_Analysis"

CITY_MAP = {
    'bei3jing1shi4': '北京', 'guang3zhou1shi4': '广州',
    'shang4hai3shi4': '上海', 'shen1zhen4shi4': '深圳',
    'wu3han4shi4': '武汉', 'xia4men2shi4': '厦门'
}
SCENARIOS = ["2040-rcp2.6", "2040-rcp4.5", "2040-rcp8.5", "2060-rcp2.6", "2060-rcp4.5", "2060-rcp8.5"]


# ================= 2. 数据提取与处理工具函数 =================

def load_city_weights(city_name_en):
    """读取城市 pop_lookup_summary 获取典型建筑的数量权重（按行数精准统计）"""
    city_cn_name = CITY_MAP.get(city_name_en, city_name_en.split('shi4')[0])
    if 'shi4' in city_name_en: city_full_cn = city_cn_name + "市"

    file_path = os.path.join(ROOT_POP_LOOKUP, city_full_cn, f"{city_full_cn}_pop_lookup_summary.xlsx")
    if not os.path.exists(file_path): return None

    try:
        df_weight = pd.read_excel(file_path, sheet_name='Aggregated_Source_Data')
        group_counts = df_weight.groupby(['LandNum', 'Cluster']).size()
        weight_map = {}
        for (l_num, c_num), count in group_counts.items():
            weight_map[(int(l_num), int(c_num))] = float(count)
        return weight_map
    except Exception as e:
        print(f"❌ 权重读取失败 ({city_cn_name}): {e}")
        return None


def get_capacity_and_area(htm_path, prioritize_user_specified=False):
    """
    【双模雷达版】从 HTML 提取制冷装机容量和建筑面积
    prioritize_user_specified: 针对 Fixed 情景，优先搜索 User-Specified 字段
    """
    cap_w, area_m2 = 0.0, 0.0
    if not os.path.exists(htm_path): return cap_w, area_m2

    # 定义搜索优先级
    if prioritize_user_specified:
        targets = ["User-Specified Gross Rated Total Cooling Capacity",
                   "Design Size Gross Rated Total Cooling Capacity"]
    else:
        targets = ["Design Size Gross Rated Total Cooling Capacity",
                   "User-Specified Gross Rated Total Cooling Capacity"]

    try:
        with open(htm_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_str = f.read()

        tables = pd.read_html(html_str)

        for df in tables:
            # 1. 提取建筑面积
            for col in df.columns:
                mask = df[col].astype(str).str.contains("Total Building Area", na=False)
                if mask.any():
                    idx = df[mask].index[0]
                    col_idx = df.columns.get_loc(col)
                    if col_idx + 1 < len(df.columns):
                        try:
                            area_m2 = float(df.iloc[idx, col_idx + 1])
                        except:
                            pass

            # 2. 提取制冷容量 (双目标探测)
            if cap_w == 0.0:
                for target_str in targets:
                    # 策略 A: 表头匹配
                    matching_cols = [c for c in df.columns if target_str in str(c)]
                    if matching_cols:
                        col_name = matching_cols[0]
                        temp_cap = pd.to_numeric(df[col_name], errors='coerce').sum()
                        if temp_cap > 0:
                            cap_w = temp_cap
                            break  # 找到就停止当前表格搜索

                    # 策略 B: 表内数据匹配
                    if cap_w == 0.0:
                        for r_idx in range(len(df)):
                            for c_idx, col_name in enumerate(df.columns):
                                cell_val = str(df.iloc[r_idx, c_idx])
                                if target_str in cell_val:
                                    if r_idx + 1 < len(df):
                                        try:
                                            vals = pd.to_numeric(df.iloc[r_idx + 1:, c_idx], errors='coerce')
                                            temp_cap = vals.sum()
                                            if temp_cap > 0: cap_w = temp_cap
                                        except:
                                            pass
                            if cap_w > 0: break
                    if cap_w > 0: break  # 跳出目标字符串循环
    except Exception as e:
        pass

    return cap_w, area_m2


# ================= 3. 核心大循环运算 =================

print("🚀 开始跨区域建筑能耗扩容仿真分析 (包含三方容量对账与溯源日志)...")
results = []
building_logs = []

for city_en, city_cn in CITY_MAP.items():
    print(f"\n▶ 正在处理城市: {city_cn}")

    city_weights = load_city_weights(city_en)
    if city_weights is None: continue

    for sce in SCENARIOS:
        fixed_dir = os.path.join(ROOT_ENERGY, "Fixed_capacity", city_en, sce)
        expand_dir = os.path.join(ROOT_ENERGY, "Capacity_expansion", city_en, sce)

        if not os.path.exists(fixed_dir): continue

        csv_files = glob.glob(os.path.join(fixed_dir, "*-meter.csv"))

        # 宏观累加器
        city_cap_base_total = 0.0  # 2020 基准容量
        city_cap_fixed_total = 0.0  # 未来不扩容容量
        city_cap_expand_total = 0.0  # 未来扩容后容量

        city_area_total = 0.0
        city_hvac_nrg_fixed = 0.0
        city_hvac_nrg_expand = 0.0

        for f_path in csv_files:
            fname = os.path.basename(f_path)
            parts = fname.split('_')

            try:
                l_num, c_num = int(parts[1]), int(parts[2])
                weight = city_weights.get((l_num, c_num), 0)
            except:
                continue

            if weight == 0: continue

            base_name = fname.replace("-meter.csv", "")

            # ---------------- A. 处理 HTML 容量数据 ----------------
            # 1. Baseline 2020 容量
            htm_base = os.path.join(ROOT_CAPA, "Baseline_2020", city_en, "2020", f"{base_name}-table.htm")
            cap_b_w, area_b = get_capacity_and_area(htm_base, prioritize_user_specified=False)

            # 2. Fixed 容量 (优先寻找 User-Specified)
            htm_fixed = os.path.join(ROOT_CAPA, "Fixed_capacity", city_en, sce, f"{base_name}-table.htm")
            cap_f_w, area_f = get_capacity_and_area(htm_fixed, prioritize_user_specified=True)

            # 3. Expand 容量 (优先寻找 Design Size)
            htm_expand = os.path.join(ROOT_CAPA, "Capacity_expansion", city_en, sce, f"{base_name}-table.htm")
            cap_e_w, area_e = get_capacity_and_area(htm_expand, prioritize_user_specified=False)

            # 【日志写入】：三方容量完全并列呈现
            building_logs.append({
                '城市': city_cn,
                '气候情景': sce,
                '典型建筑名称': base_name,
                'LandNum': l_num,
                'Cluster': c_num,
                '全市代表数量(Weight)': weight,
                '单栋建筑面积(m2)': area_f if area_f > 0 else area_b,
                '单栋基准2020容量_Baseline(W)': cap_b_w,
                '单栋未来不扩容容量_Fixed(W)': cap_f_w,
                '单栋未来扩容后容量_Expand(W)': cap_e_w
            })

            # 累加全市容量总和
            city_cap_base_total += (cap_b_w / 1000.0) * weight
            city_cap_fixed_total += (cap_f_w / 1000.0) * weight
            city_cap_expand_total += (cap_e_w / 1000.0) * weight
            city_area_total += (area_f if area_f > 0 else area_b) * weight

            # ---------------- B. 智能匹配 Schedule ----------------
            s_path = os.path.join(ROOT_SCHEDULE, "Fixed_capacity", city_en, sce, f"{base_name}.csv")
            if not os.path.exists(s_path):
                s_path_alt = os.path.join(ROOT_SCHEDULE, "Baseline_2020", city_en, "2020", f"{base_name}.csv")
                if os.path.exists(s_path_alt):
                    s_path = s_path_alt
                else:
                    continue

            # ---------------- C. 处理 CSV 能量数据 ----------------
            try:
                df_f = pd.read_csv(f_path)
                df_e = pd.read_csv(os.path.join(expand_dir, fname))
                df_s = pd.read_csv(s_path)

                df_f.columns = df_f.columns.str.strip()
                df_e.columns = df_e.columns.str.strip()
                df_s.columns = df_s.columns.str.strip()

                fac_col = [c for c in df_f.columns if 'Electricity:Facility' in c][0]
                cool_sch_col = [c for c in df_s.columns if 'COOLING_PERIOD_SCHEDULE' in c][0]
                hvac_sch_col = [c for c in df_s.columns if 'HVAC_CONDITIONEDTIME' in c][0]

                f_kw = (df_f[fac_col] / 3.6e6).values
                e_kw = (df_e[fac_col] / 3.6e6).values

                bld_cols = [c for c in df_f.columns if 'Electricity:Building' in c]
                if len(bld_cols) > 0:
                    bld_col = bld_cols[0]
                    f_bld_kw = (df_f[bld_col] / 3.6e6).values
                    e_bld_kw = (df_e[bld_col] / 3.6e6).values
                else:
                    f_bld_kw = np.zeros(len(f_kw))
                    e_bld_kw = np.zeros(len(e_kw))

                mask = (df_s[cool_sch_col] == 1) & (df_s[hvac_sch_col] == 1)

                f_hvac = np.maximum(f_kw - f_bld_kw, 0)
                e_hvac = np.maximum(e_kw - e_bld_kw, 0)

                city_hvac_nrg_fixed += f_hvac[mask].sum() * weight
                city_hvac_nrg_expand += e_hvac[mask].sum() * weight

            except Exception as e:
                continue

        # ---------------- D. 整合全市尺度宏观指标 ----------------
        results.append({
            '城市': city_cn,
            '气候情景': sce,
            '全市总建筑面积(百万m2)': city_area_total / 1e6,
            '基准2020容量_Baseline(MW)': city_cap_base_total / 1000.0,
            '未来不扩容容量_Fixed(MW)': city_cap_fixed_total / 1000.0,
            '未来扩容后容量_Expand(MW)': city_cap_expand_total / 1000.0,
            '扩容带来的装机增量(MW)': (city_cap_expand_total - city_cap_fixed_total) / 1000.0,
            '基准总制冷能耗_Fixed(GWh)': city_hvac_nrg_fixed / 1e6,
            '扩容后总制冷能耗_Expand(GWh)': city_hvac_nrg_expand / 1e6,
            '扩容导致的能耗激增(GWh)': (city_hvac_nrg_expand - city_hvac_nrg_fixed) / 1e6
        })

# ================= 4. 导出最终成果 =================

df_final = pd.DataFrame(results)
output_filename = "城市级_空调扩容与能耗增量分析.xlsx"
df_final.to_excel(output_filename, index=False)

df_log = pd.DataFrame(building_logs)
log_filename = "建筑级别_容量与面积溯源日志.xlsx"
df_log.to_excel(log_filename, index=False)

print(f"\n🎉 完美收官！全盘数据计算完毕。")
print(f"📊 宏观分析报告已导出至: {output_filename}")
print(f"🔍 建筑明细日志已导出至: {log_filename}")