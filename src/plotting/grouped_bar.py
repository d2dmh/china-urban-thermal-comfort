"""
分组柱状图：跨城市 × 情景，或 跨城市 × 策略。
通用函数，由 notebook 调用。
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.plotting.style import (
    SIZE_CITY_NAME, SIZE_YLABEL, SIZE_TICK, SIZE_BAR_TXT, SIZE_LEGEND,
    SCENARIO_PALETTE, STRATEGY_PALETTE, STRATEGY_LABEL_EN,
    apply_sci_style, despine_ax,
)


def plot_grouped_bar(
    df, x, y, hue,
    palette=None,
    hue_order=None,
    title=None,
    ylabel='Hours / Resident',
    figsize=(24, 10),
    save_path=None,
    add_grand_total=True,
    grand_total_label='Grand Total',
):
    """
    通用 SCI 风格分组柱状图。

    参数：
        df: 含 x, y, hue 三列的 DataFrame
        x, y, hue: 列名
        palette: dict {hue_value: color}
        hue_order: hue 显示顺序
        add_grand_total: 是否在最右侧加一根"总计"柱（按 hue 求 y 平均）
    """
    apply_sci_style()

    df_plot = df.copy()

    if add_grand_total:
        # 总计 = 每个 hue 在所有 x 类别上的均值
        grand = df_plot.groupby(hue)[y].mean().reset_index()
        grand[x] = grand_total_label
        df_plot = pd.concat([df_plot, grand], ignore_index=True)

    fig, ax = plt.subplots(figsize=figsize)
    sns.set_style("white")

    # X 轴顺序：原 x 类别 + Grand Total 在最右
    x_order = [v for v in df_plot[x].unique() if v != grand_total_label]
    if grand_total_label in df_plot[x].values:
        x_order.append(grand_total_label)

    sns.barplot(
        data=df_plot,
        x=x, y=y, hue=hue,
        order=x_order,
        hue_order=hue_order,
        palette=palette,
        ax=ax,
        edgecolor='black',
        linewidth=1.2,
    )

    # 柱顶数值标签
    for p in ax.patches:
        h = p.get_height()
        if pd.notna(h) and h > 0:
            ax.text(
                p.get_x() + p.get_width() / 2.,
                h + (ax.get_ylim()[1] * 0.015),
                f'{h:.1f}',
                ha="center", va="bottom", rotation=90,
                fontsize=SIZE_BAR_TXT, color='black', fontweight='bold',
            )

    ax.set_title(title or '', fontsize=SIZE_YLABEL, fontweight='bold', pad=20)
    ax.set_xlabel('')
    ax.set_ylabel(ylabel, fontsize=SIZE_YLABEL, fontweight='bold', labelpad=20)
    ax.tick_params(axis='x', labelsize=SIZE_CITY_NAME, pad=15)
    ax.tick_params(axis='y', labelsize=SIZE_TICK, width=2.0)

    despine_ax(ax)

    # 留出图例空间
    cur_ymax = ax.get_ylim()[1]
    ax.set_ylim(0, cur_ymax * 1.25)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels, loc='upper right', bbox_to_anchor=(0.99, 0.99),
        ncol=1, fontsize=SIZE_LEGEND, frameon=False,
        prop={'weight': 'bold', 'size': SIZE_LEGEND},
    )

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
        print(f"✅ 图已保存: {save_path}")

    return fig, ax


def plot_scenario_grouped(df, save_path=None, **kwargs):
    """跨城市 × 7 情景的分组柱状图（默认配色，使用拼音标签）"""
    from config.parameters import SCENARIO_ORDER
    x_col = '城市标签' if '城市标签' in df.columns else '城市'
    return plot_grouped_bar(
        df, x=x_col, y='Hours_Per_Resident', hue='情景',
        palette=SCENARIO_PALETTE,
        hue_order=SCENARIO_ORDER,
        save_path=save_path,
        **kwargs,
    )


def plot_strategy_grouped(df, save_path=None, **kwargs):
    """跨城市 × 3 策略的分组柱状图（英文图例避免中文字体问题）"""
    df = df.copy()
    df['Strategy_EN'] = df['策略'].map(STRATEGY_LABEL_EN).fillna(df['策略'])
    x_col = '城市标签' if '城市标签' in df.columns else '城市'
    palette_en = {STRATEGY_LABEL_EN[k]: v for k, v in STRATEGY_PALETTE.items()}
    return plot_grouped_bar(
        df, x=x_col, y='Hours_Per_Resident', hue='Strategy_EN',
        palette=palette_en,
        hue_order=['Baseline', 'Capacity Expansion', 'Fixed Capacity'],
        save_path=save_path,
        **kwargs,
    )
