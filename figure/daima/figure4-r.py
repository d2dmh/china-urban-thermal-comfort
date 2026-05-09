import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe  # 引入路径效果，用于制作阴影
import os
import glob
import re
import warnings

# =====================================================================
# ======================== 1. 全局核心参数配置区 =========================
# =====================================================================

# ----------------- [绘图内容开关控制] -----------------
HIDE_ALL_TEXT = True       # 开关：设置为 True 时隐藏所有文字、标题、数字和图例（仅保留刻度线）

# ----------------- [路径配置] -----------------
epw_base_dir = r"E:\2.22最终版天气epw数据"
results_base_dir = r"E:\GeiMingHao_all\GeiMingHao\all_day_result\Future\shen1zhen4shi4"
pop_file = r"E:\GeiMingHao_0303\GeiMingHao\result\对比\Result_Analysis\深圳市\深圳市_pop_lookup_summary.xlsx"

# ----------------- [色彩与视觉配置] -----------------
COLOR_TOP = '#931832'          # 顶层主色调 (深红)
COLOR_NONTOP = '#475894'       # 非顶层主色调 (深蓝)
SHADOW_COLOR = 'dimgray'       # 平均线的阴影颜色


BG_LINE_ALPHA = 0.27          # 背景细线透明度
BG_LINE_WIDTH = 0.45            # 背景细线粗细
AVG_LINE_WIDTH = 1.73           # 时段平均粗线粗细

# ----------------- [字体大小配置] -----------------
FS_SUPTITLE = 24               # 全局主标题字体
FS_SUBTITLE = 20               # 各个子图标题字体
FS_LABEL = 14                  # X/Y轴标签字体
FS_TICK = 14                   # 刻度数字字体
FS_LEGEND = 14                 # 图例字体

# ----------------- [布局与间距配置] -----------------
FIG_SIZE = (22, 14)            # 画布整体尺寸
SPACE_W = 0.04                 # 子图水平间距
SPACE_H = 0.08                 # 子图垂直间距

# =====================================================================
# ======================== 2. 环境设置与数据提取 =========================
# =====================================================================

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

bldg_types = [2, 1, 0]
type_labels = ['高层 (Type 2)', '中层 (Type 1)', '低层 (Type 0)']

print("正在计算建筑物代表权重(总数统计)...")
pop_df = pd.read_excel(pop_file, sheet_name='Aggregated_Source_Data')
pop_df.columns = pop_df.columns.str.strip()

if 'LandNum' in pop_df.columns and 'Cluster' in pop_df.columns:
    pop_df['LandNum'] = pd.to_numeric(pop_df['LandNum'], errors='coerce').fillna(-1).astype(int)
    pop_df['Cluster'] = pd.to_numeric(pop_df['Cluster'], errors='coerce').fillna(-1).astype(int)
    weight_dict = pop_df[pop_df['LandNum'] != -1].groupby(['LandNum', 'Cluster']).size().to_dict()
    print(f"权重计算成功！共提取了 {len(weight_dict)} 种建筑类型的总数量。")
else:
    print(f"严重错误：找不到 LandNum 或 Cluster 列！当前列名有: {pop_df.columns.tolist()}")


def format_ep_datetime(dt_str):
    dt_str = str(dt_str).strip()
    parts = [p for p in dt_str.split(' ') if p]
    if len(parts) >= 2:
        d_part, t_part = parts[0], parts[1]
        if '/' in d_part:
            m, d = d_part.split('/')
            d_part = f"{int(m):02d}/{int(d):02d}"
        if ':' in t_part:
            h, min_, sec = t_part.split(':')
            t_part = f"{int(h):02d}:{min_}:{sec}"
        return f"{d_part}{t_part}"
    return dt_str.replace(' ', '')


def get_storey_num(col_name):
    match = re.search(r'STOREY_(\d+)', str(col_name), re.IGNORECASE)
    return int(match.group(1)) if match else -1


required_scenarios = ['2020', '2040-rcp8.5', '2060-rcp8.5']

data_ts_top = {s: {bt: pd.Series(dtype=float) for bt in bldg_types} for s in required_scenarios}
data_ts_nontop = {s: {bt: pd.Series(dtype=float) for bt in bldg_types} for s in required_scenarios}

for scenario in required_scenarios:
    file_name = f"shen1zhen4shi4_{scenario}_Results.xlsx"
    file_path = os.path.join(results_base_dir, file_name)
    if not os.path.exists(file_path):
        continue

    print(f"---> 正在处理 Excel: {file_name} ...")
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"打开 Excel 失败 {file_name}, 跳过。")
        continue

    for b_type in bldg_types:
        for b_id in range(1, 13):
            real_bldg_count = weight_dict.get((b_type, b_id), 0)
            if real_bldg_count == 0: continue

            pattern = f"^shen1zhen4shi4_{b_type}_{b_id}_"
            matched_sheets = [s for s in xls.sheet_names if re.match(pattern, s)]

            if matched_sheets:
                df = pd.read_excel(xls, sheet_name=matched_sheets[0])
                set_cols = [col for col in df.columns if 'SET' in str(col)]

                if not df.empty and set_cols:
                    df['Date_Clean'] = df['Date/Time'].apply(format_ep_datetime)
                    df.drop_duplicates(subset=['Date_Clean'], inplace=True)
                    df.set_index('Date_Clean', inplace=True)

                    set_cols_sorted = sorted(set_cols, key=get_storey_num)
                    top_col = set_cols_sorted[-1]
                    nontop_cols = set_cols_sorted[:-1]

                    is_disc_top = (df[top_col] > 30).fillna(False).astype(int) * real_bldg_count

                    if nontop_cols:
                        is_disc_nontop = (df[nontop_cols].max(axis=1) > 30).fillna(False).astype(int) * real_bldg_count
                    else:
                        is_disc_nontop = pd.Series(0, index=df.index)

                    if data_ts_top[scenario][b_type].empty:
                        data_ts_top[scenario][b_type] = is_disc_top
                        data_ts_nontop[scenario][b_type] = is_disc_nontop
                    else:
                        data_ts_top[scenario][b_type] = data_ts_top[scenario][b_type].add(is_disc_top, fill_value=0)
                        data_ts_nontop[scenario][b_type] = data_ts_nontop[scenario][b_type].add(is_disc_nontop, fill_value=0)

# =========================================================================
# ======================== 3. 图表绘制与视觉渲染 ==========================
# =========================================================================
print("\n正在绘制图1：基于绝对时间对齐的顶层/非顶层叠加图...")

time_cols_config = {
    '2020': {'era_label': '2020', 'scenario': '2020'},
    '2040': {'era_label': '2040 (RCP8.5)', 'scenario': '2040-rcp8.5'},
    '2060': {'era_label': '2060 (RCP8.5)', 'scenario': '2060-rcp8.5'}
}

fig1, axes1 = plt.subplots(nrows=3, ncols=3, figsize=FIG_SIZE, sharex=True, sharey='row')

# 仅在不隐藏文字时绘制全局主标题
if not HIDE_ALL_TEXT:
    fig1.suptitle(
        '深圳各层建筑热不适楼栋数演变 (顶层与非顶层对比)\n(阴影为每日波动，粗线为时段平均)',
        fontsize=FS_SUPTITLE, fontweight='bold', y=0.97)

x_hours = np.arange(24)
xticks_h = [0, 5, 11, 17, 23]
xtick_labels_h = ['1am', '6am', 'Noon', '6pm', 'Midnight']

def get_daily_profiles(series):
    if series is None or series.empty:
        return None
    df_plot = series.reset_index()
    df_plot.columns = ['DateTime', 'Count']
    df_plot['Date'] = df_plot['DateTime'].str[:5]
    df_plot['Hour'] = df_plot['DateTime'].str[5:7].astype(int) - 1
    daily_df = df_plot.pivot_table(index='Date', columns='Hour', values='Count', aggfunc='sum')
    daily_df = daily_df.reindex(columns=range(24))
    return daily_df.values

shadow_effect = [
    pe.SimpleLineShadow(shadow_color=SHADOW_COLOR, alpha=0.3, offset=(1.5, -1.5)),
    pe.Normal()
]

for row_idx, bt in enumerate(bldg_types):
    for col_idx, time_era in enumerate(['2020', '2040', '2060']):
        ax = axes1[row_idx, col_idx]
        actual_scenario = time_cols_config[time_era]['scenario']

        prof_top = get_daily_profiles(data_ts_top[actual_scenario][bt])
        prof_nontop = get_daily_profiles(data_ts_nontop[actual_scenario][bt])
        has_data = False

        # --- 绘制非顶层 ---
        if prof_nontop is not None:
            has_data = True
            for day_idx in range(prof_nontop.shape[0]):
                ax.plot(x_hours, prof_nontop[day_idx, :], color=COLOR_NONTOP, alpha=BG_LINE_ALPHA, linewidth=BG_LINE_WIDTH, zorder=1)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                avg_nontop = np.nanmean(prof_nontop, axis=0)

            ax.plot(x_hours, avg_nontop, color=COLOR_NONTOP, linewidth=AVG_LINE_WIDTH, label='非顶层平均', zorder=10, path_effects=shadow_effect)

        # --- 绘制顶层 ---
        if prof_top is not None:
            has_data = True
            for day_idx in range(prof_top.shape[0]):
                ax.plot(x_hours, prof_top[day_idx, :], color=COLOR_TOP, alpha=BG_LINE_ALPHA, linewidth=BG_LINE_WIDTH, zorder=2)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                avg_top = np.nanmean(prof_top, axis=0)

            ax.plot(x_hours, avg_top, color=COLOR_TOP, linewidth=AVG_LINE_WIDTH, label='顶层平均', zorder=11, path_effects=shadow_effect)

        # 未找到数据的文本提示也受开关控制
        if not has_data and not HIDE_ALL_TEXT:
            ax.text(0.5, 0.5, '未找到数据', ha='center', va='center', transform=ax.transAxes, color=COLOR_TOP, fontsize=FS_LABEL)

        # 设置坐标轴范围与网格
        ax.set_ylim(bottom=0)
        ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
        ax.set_xlim(0, 23)

        # 保留刻度线本身
        ax.tick_params(axis='both', which='major', labelsize=FS_TICK)

        # ======== 文本与数字控制逻辑 ========
        if HIDE_ALL_TEXT:
            # 隐藏坐标轴上的数字，但保留刻度线
            ax.tick_params(labelbottom=False, labelleft=False)
        else:
            # 正常显示标题和Y轴标签
            if row_idx == 0:
                ax.set_title(f"【{time_cols_config[time_era]['era_label']} 时期】", fontsize=FS_SUBTITLE, fontweight='bold', pad=10)
            if col_idx == 0:
                ax.set_ylabel(f"{type_labels[row_idx]}\n不适大楼总数", fontsize=FS_LABEL, fontweight='bold', labelpad=10)

        # 处理 X 轴刻度 (无论是否隐藏文字，底部的刻度线位置都需要被正确设置)
        if row_idx == 2:
            ax.set_xticks(xticks_h)
            if not HIDE_ALL_TEXT:
                ax.set_xticklabels(xtick_labels_h, fontsize=FS_TICK)
                if col_idx == 1:
                    ax.set_xlabel('一天内的时间 (Hour Ending)', fontsize=FS_LABEL, fontweight='bold', labelpad=10)
            else:
                ax.set_xticklabels([])  # 强制清空自定义的 x 轴标签

        # 统一添加图例
        if has_data and not HIDE_ALL_TEXT:
            ax.legend(loc='upper left', fontsize=FS_LEGEND, frameon=True, framealpha=0.9, edgecolor='lightgray')

# 调整子图间距
plt.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.06, wspace=SPACE_W, hspace=SPACE_H)

plt.show()