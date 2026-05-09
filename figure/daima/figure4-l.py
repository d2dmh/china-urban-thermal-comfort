import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================================
#                                  全局参数配置区
# ==============================================================================

# ----------------- 1. 路径与输出文件设置 -----------------
BASE_DIR = r"E:\GeiMingHao_all\GeiMingHao\result\对比\SET_Hourly_27_2\Future\shen1zhen4shi4"
OUT_DIR = r"C:\Users\31080\Desktop\figure\图4"
DPI = 600  # 【参数解释】分辨率（Dots Per Inch），600是达到学术期刊发表标准的高清晰度

# ----------------- 2. 数据文件设置 (仅保留2020和未来的RCP8.5) -----------------
FILE_2020 = ["shen1zhen4shi4_2020_HourlyStats.xlsx"]
FILES_2040 = ["shen1zhen4shi4_2040-rcp8.5_HourlyStats.xlsx"]
FILES_2060 = ["shen1zhen4shi4_2060-rcp8.5_HourlyStats.xlsx"]

BUILDINGS_CONFIG = [
    ("High-rise", "shen1zhen4shi4_2_6_2005_S0"),
    ("Mid-rise", "shen1zhen4shi4_1_10_2005_S0"),
    ("Low-rise", "shen1zhen4shi4_0_6_1980_S0")
]

# ----------------- 3. SCI 尺寸与配色方案设置 -----------------
FIG_WIDTH = 2.5                 # 【参数解释】图片宽度（英寸），3.5英寸约等于单栏排版的标准宽度
STOREY_HEIGHT_FACTOR = 0.12     # 【参数解释】每个楼层在Y轴上占据的高度比例系数
MIN_FIG_HEIGHT = 3           # 【参数解释】图片的最小高度（英寸），防止楼层太少时图片被压扁

COLOR_2020 = '#4575b4'  # Cool Navy
COLOR_2040 = '#fdae61'  # Warm Sand/Orange
COLOR_2060 = '#d73027'  # Brick Red

# ----------------- 4. SCI 字体与线条样式设置 -----------------
FONT_FAMILY = 'serif'
FONT_SERIF = ['Times New Roman', 'DejaVu Serif']
FONT_SIZE_LABEL = 12           # 【参数解释】坐标轴标题文字大小 (如 "Thermal Discomfort Hours")
FONT_SIZE_TICK = 10            # 【参数解释】坐标轴刻度数字大小 (如 0, 10, 20)

LINE_WIDTH_AXES = 1.0          # 【参数解释】坐标轴边框的粗细
LINE_WIDTH_DATA = 1.5          # 【参数解释】数据折线的粗细
MARKER_SIZE = 6                # 【参数解释】折线上数据点（圆圈、方块、三角）的大小

# ----------------- 5. 特殊显示开关设置 -----------------
SHOW_LABELS = True


# ==============================================================================
#                                  核心执行区
# ==============================================================================

# 【参数解释】rcParams 是 Matplotlib 的全局运行时配置字典，修改这里会影响整个图表的样式
plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['font.serif'] = FONT_SERIF
plt.rcParams['axes.labelsize'] = FONT_SIZE_LABEL            
plt.rcParams['axes.linewidth'] = LINE_WIDTH_AXES           
plt.rcParams['xtick.labelsize'] = FONT_SIZE_TICK
plt.rcParams['ytick.labelsize'] = FONT_SIZE_TICK

# 【参数解释】设置刻度线的方向。'in'为朝向图表内部，'out'为朝向图表外部，'inout'为穿过坐标轴
plt.rcParams['xtick.direction'] = 'out'  # X轴（底边）刻度线朝外
plt.rcParams['ytick.direction'] = 'out'  # Y轴（左边）刻度线朝外

# 【参数解释】控制图表四个边框是否显示刻度线。True为显示，False为隐藏
plt.rcParams['xtick.top'] = False        # 隐藏上方边框的X轴刻度线
plt.rcParams['ytick.right'] = False      # 隐藏右侧边框的Y轴刻度线

# 【参数解释】设置主刻度线（带有数字的刻度）的粗细和长度
plt.rcParams['xtick.major.width'] = LINE_WIDTH_AXES # X轴刻度线的粗细，和边框保持一致
plt.rcParams['ytick.major.width'] = LINE_WIDTH_AXES # Y轴刻度线的粗细
plt.rcParams['xtick.major.size'] = 4                # X轴刻度线的长度（伸出多长）
plt.rcParams['ytick.major.size'] = 4                # Y轴刻度线的长度

os.makedirs(OUT_DIR, exist_ok=True)

def process_files(file_list, sheet_name):
    all_data = []
    storeys = None
    for f in file_list:
        path = os.path.join(BASE_DIR, f)
        try:
            df = pd.read_excel(path, sheet_name=sheet_name)
            storey_cols = [col for col in df.columns if 'STOREY' in str(col).upper()]
            if storeys is None:
                storeys = [int(str(col).split('_')[-1]) for col in storey_cols]
            total_hours = df[storey_cols].sum().values
            all_data.append(total_hours)
        except Exception as e:
            print(f"读取异常 {path}: {e}")
    return np.array(all_data), storeys

for b_label, sheet_name in BUILDINGS_CONFIG:
    d2020, storeys = process_files(FILE_2020, sheet_name)
    d2040, _ = process_files(FILES_2040, sheet_name)
    d2060, _ = process_files(FILES_2060, sheet_name)
    
    if storeys is None:
        continue
        
    v2020 = d2020[0] if d2020.size > 0 else None
    v2040 = d2040[0] if d2040.size > 0 else None
    v2060 = d2060[0] if d2060.size > 0 else None

    # 计算出当前的全局最大X值，以保证坐标轴比例稳定
    max_val = 0
    if v2060 is not None: max_val = max(max_val, np.max(v2060))
    if v2040 is not None: max_val = max(max_val, np.max(v2040))
    if v2020 is not None: max_val = max(max_val, np.max(v2020))

    fig_height = max(MIN_FIG_HEIGHT, len(storeys) * STOREY_HEIGHT_FACTOR + 1.5)
    
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, fig_height))

    # --- 始终绘制数据线与多面形 ---
    if v2060 is not None:
        # 【参数解释】fill_betweenx: 在Y轴方向填充面积。这里是在0和v2060数据之间填充
        # alpha=0.2: 填充颜色的透明度，0为全透明，1为不透明
        ax.fill_betweenx(storeys, 0, v2060, color=COLOR_2060, alpha=0.2)
        ax.plot(v2060, storeys, color=COLOR_2060, linewidth=LINE_WIDTH_DATA, 
                marker='^', markersize=MARKER_SIZE) # marker='^' 是正三角形标记

    if v2040 is not None:
        ax.fill_betweenx(storeys, 0, v2040, color=COLOR_2040, alpha=0.4)
        ax.plot(v2040, storeys, color=COLOR_2040, linewidth=LINE_WIDTH_DATA, 
                marker='s', markersize=MARKER_SIZE) # marker='s' 是正方形(square)标记

    if v2020 is not None:
        ax.fill_betweenx(storeys, 0, v2020, color=COLOR_2020, alpha=0.6)
        ax.plot(v2020, storeys, color=COLOR_2020, linewidth=LINE_WIDTH_DATA, 
                marker='o', markersize=MARKER_SIZE) # marker='o' 是圆形标记

    # --- 坐标轴细节与标签开关逻辑 ---
    # 【参数解释】强制Y轴（楼层）只显示整数刻度，避免出现 1.5 层这种不存在的楼层
    ax.yaxis.get_major_locator().set_params(integer=True) 
    
    # 【参数解释】设置X轴和Y轴的显示范围 (limits)
    # left=-5: 让X轴起点稍微往左偏一点，留出一点空白，图表不至于贴紧左边缘
    # right=max_val * 1.05: 右侧留出 5% 的空白余量
    ax.set_xlim(left=-5, right=max_val * 1.05 if max_val > 0 else 10) 
    ax.set_ylim(bottom=min(storeys) - 0.5, top=max(storeys) + 0.5) # 上下各留0.5层的空间
    
    # 获取Matplotlib自动计算出的美观最大刻度值
    max_tick = max(ax.get_xticks())
    
    # 【参数解释】np.linspace(start, stop, num) 
    # 在 0 到 max_tick 之间，等间距生成 5 个数字。
    # 例如如果 max_tick 是 100，生成的刻度就是 [0, 25, 50, 75, 100]
    ax.set_xticks(np.linspace(0, max_tick, 5))

    if SHOW_LABELS:
        # 【参数解释】fontweight='bold': 设置字体为粗体
        ax.set_xlabel("Thermal Discomfort Hours (h)", fontweight='bold')
        ax.set_ylabel("Storey Level", fontweight='bold')
    else:
        ax.set_xlabel("")
        ax.set_ylabel("")
        # 【参数解释】labelbottom=False: 隐藏X轴底部的数字（刻度线还在，但数字没了）
        # labelleft=False: 隐藏Y轴左侧的数字
        ax.tick_params(labelbottom=False, labelleft=False)

    # 【参数解释】grid: 绘制网格线。
    # axis='y': 仅仅绘制横向（平行于X轴，对应Y轴刻度）的网格线
    # linestyle='--': 网格线样式为虚线
    ax.grid(True, axis='y', linestyle='--', linewidth=0.5, alpha=0.5)

    # 【参数解释】自动调整子图参数，使之填充整个图像区域，防止坐标轴标签被裁掉
    plt.tight_layout()

    save_filename = f"Discomfort_{b_label.replace(' ', '_')}.png"
    save_path = os.path.join(OUT_DIR, save_filename)
    
    # 【参数解释】bbox_inches='tight': 保存图片时，自动裁掉图片边缘多余的空白区域，只保留紧凑的图表本身
    plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    plt.close()
    
    print(f"[{b_label}] 绘图完成 -> {save_path}")

print("\n所有独立图片渲染完毕！")