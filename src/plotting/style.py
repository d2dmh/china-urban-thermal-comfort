"""
SCI 风格画图配置：字体、字号、调色板。
所有画图模块共享。
"""

import matplotlib.pyplot as plt


# ================= 字号配置 =================
SIZE_CITY_NAME = 24    # X 轴城市名称
SIZE_YLABEL = 24       # Y 轴标签
SIZE_TICK = 20         # 轴刻度数字
SIZE_BAR_TXT = 16      # 柱子上方数据文本
SIZE_LEGEND = 20       # 图例文字
SIZE_TITLE = 18        # 子图标题（多策略对比时使用）


# ================= 7 情景调色板 =================
SCENARIO_PALETTE = {
    '2020 Baseline': '#4e79a7',
    '2040 RCP 2.6':  '#8cd17d',
    '2060 RCP 2.6':  '#59a14f',
    '2040 RCP 4.5':  '#f1ce63',
    '2060 RCP 4.5':  '#f28e2b',
    '2040 RCP 8.5':  '#ff9d9a',
    '2060 RCP 8.5':  '#e15759',
}


# ================= 三策略调色板（用于策略对比图）=================
STRATEGY_PALETTE = {
    '现状': '#4e79a7',
    '扩容': '#59a14f',
    '定容': '#e15759',
}

# 三策略的英文标签（用于纯英文画图避免中文字体问题）
STRATEGY_LABEL_EN = {
    '现状': 'Baseline',
    '扩容': 'Capacity Expansion',
    '定容': 'Fixed Capacity',
}


def apply_sci_style():
    """应用 SCI 学术绘图全局样式（Times New Roman 主字体 + 中文后备字体）"""
    plt.rcParams.update({
        # 优先 Times New Roman，缺字符时回落到 Microsoft YaHei / SimHei
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
        'font.sans-serif': ['Times New Roman', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
        'axes.unicode_minus': False,  # 负号正常显示
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def despine_ax(ax, linewidth=2.0):
    """去掉上、右边框，加粗下、左边框（极简学术风）"""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(linewidth)
    ax.spines['bottom'].set_color('black')
    ax.spines['left'].set_linewidth(linewidth)
    ax.spines['left'].set_color('black')
