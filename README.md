# 城市住宅夜间热不舒适分析项目

> 气候变化下中国城市住宅夜间（22:00-7:00）热不舒适状况研究
> 基于 EnergyPlus 仿真 + SET 指标 + 人口数据

---

## 一、研究概述

### 1.1 研究目标

评估气候变化背景下中国主要城市住宅建筑在夜间（22:00-7:00）的热不舒适状况。核心指标为 **人均不舒适小时数（Hours/Resident）**——即每位居民在夜间经历的 SET > 30°C 的总小时数。

### 1.2 研究范围

| 维度 | 内容 |
|------|------|
| **城市** | 北京、上海、广州、深圳、武汉、厦门
| **气候情景（7 个）** | 2020 Baseline、2040 RCP 2.6/4.5/8.5、2060 RCP 2.6/4.5/8.5 |
| **空调策略（3 个）** | **现状**（Baseline_2020）、**扩容**（Capacity_expansion，autosize 27°C）、**定容**（Fixed_capacity，未来不加空调） |
| **建筑类型** | 0 = 低层、1 = 中层、2 = 高层 |
| **夜间窗口** | 22, 23, 24(=0), 1, 2, 3, 4, 5, 6, 7（共 10 小时） |

### 1.3 核心参数

| 参数 | 旧值 | 当前值 | 说明 |
|------|------|--------|------|
| MET | — | 0.7 | 代谢率（睡眠场景） |
| CLO | 0.8（5.7） | **0.8** | 服装热阻（被褥保温），已统一为 0.8 |
| AIR_VELOCITY | — | 0.1 m/s | 室内空气流速 |
| RH_LIMIT | — | 60% | 空调环境湿度上限（模拟除湿效果） |
| SET_THRESHOLD | 30°C | **30°C** | 夜间不舒适阈值 |
| MAX_WORKERS | — | 3 | 并行进程数（防 Numba 内存爆炸） |



## 二、项目结构（2025-2026 重构版）

```
E:\cc data\thermal_comfort_analysis\
│
├── config/                          # 【集中配置层】
│   ├── paths.py                     #   所有外部数据路径（仿真/EPW/人口/映射）
│   └── parameters.py                #   计算参数 + 城市列表 + 情景列表
│
├── src/                             # 【核心代码层】
│   ├── core/                        #   不可变基础工具
│   │   ├── epw_handler.py           #     EPW 大气压读取、时间轴对齐
│   │   ├── set_calculator.py        #     向量化 SET 计算（融合 5.7+1.py）
│   │   └── city_matcher.py          #     Sheet 解析、建筑物编号提取
│   ├── pipeline/                    #   可变数据处理流程
│   │   ├── step1_compute_set.py     #     扫描策略×城市×情景 → 计算 SET → 统计过热
│   │   └── step2_per_capita_hours.py#     人口匹配 → 人均不舒适小时数
│   └── plotting/                    #   可视化模块
│       ├── style.py                 #     SCI 风格：字号/调色板/去框线
│       └── grouped_bar.py           #     通用分组柱状图函数
│
├── figure/
│   └── daima/                       # 【论文画图脚本原始代码】（共 11 个文件，未重构）
│       ├── fig2-1地图-建筑气候区划.py
│       ├── figure2-b-去除文字.py
│       ├── figure2-c.py
│       ├── figure2-d.py
│       ├── figure3-a.py
│       ├── figure3-b.py
│       ├── figure3-c.py
│       ├── figure4-l.py
│       ├── figure4-r.py
│       ├── figure5.py
│       └── figure6.py
│
├── notebooks/                       # 【交互式画图】
│   ├── 01_per_capita_grouped_bar.ipynb     # 跨城市分组柱状图
│   └── 02_three_strategies_compare.ipynb   # 三策略对比图
│
├── results/                         # 【结果输出】
│   ├── set_calculations/            #   step1 输出（逐时 SET + 过热统计）
│   ├── per_capita_hours/            #   step2 输出（人均不舒适小时数汇总）
│   └── figures/                     #   图表输出
│
├── scripts/
│   └── run_all.py                   # 一键运行 step1 → step2
│
├── requirements.txt
├── README.md                        # 本文件
└── docs/
    └── algorithm.md                 # 算法说明
```

---

## 三、数据来源（路径不动）

所有原始数据保留在原路径，`config/paths.py` 中引用，**不复制**。

| 数据类型 | 路径 | 说明 |
|---------|------|------|
| EnergyPlus 仿真结果 | `E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv\` | 含 Baseline_2020 / Capacity_expansion / Fixed_capacity 三子文件夹 |
| EPW 气象文件 | `E:\BaiduNetdiskDownload\newcity\` | 含 2020 / 2040-rcp2.6 / 2040-rcp4.5 / 2040-rcp8.5 / 2060-rcp2.6 / 2060-rcp4.5 / 2060-rcp8.5 子文件夹 |
| 建筑人口属性 | `E:\城市建筑_AOI_小区_POI_用途分类_人口结构_version4\` | 各省份子文件夹下的 CSV |
| 聚类映射文件 | `E:\映射\` | `cluster_<code>_<城市名>.csv` 格式 |
| 建筑物属性表 | `城市建筑物属性表字段说明.xlsx` | 项目根目录下副本 |

---

## 四、数据处理流程

### Step 1：SET 计算 + 夜间过热统计（`step1_compute_set.py`）

```
三策略目录
  └─ 城市文件夹
       └─ 情景文件夹
            └─ 建筑 CSV  →  ① 读取 EPW 大气压 + 时间轴对齐
                            ② 筛选夜间 × HVAC 启用时段
                            ③ 各楼层向量化计算 SET（pythermalcomfort.set_tmp）
                            ④ 统计 SET > 30°C 的不舒适小时数
                            ⑤ 输出：逐时 Excel + 总 summary CSV
```

**输出文件**：
- `results/set_calculations/<策略>/<城市>/<城市>_<情景>_SET.xlsx`（每建筑一 sheet）
- `results/set_calculations/summary_uncomfortable_hours.csv`（总汇总表）

**关键**：融合了 5.7 的整体框架 + 1.py 的向量化 SET 计算（避免逐小时循环）。

**Numba 内存注意**：`set_calculator.py` 在导入 pythermalcomfort 前设置 `NUMBA_NUM_THREADS=1`；主进程启动前调用 `warm_up_numba()` 预热缓存。`MAX_WORKERS` 默认 3（视机器内存调整）。

### Step 2：人均不舒适小时数（`step2_per_capita_hours.py`）

```
Step 1 输出的 SET Excel
  + 人口查找表（Cluster × Fnum → Total_Pop）
    ├── cluster_<code>_<城市名>.csv（BuildingID → Cluster）
    └── <城市>_building_pop_attributes.csv（BuildingID → Fnum, popNum_2）
  → 对每建筑：Σ(各楼层 SET>30 小时数 × 均摊人口) / 总人口
  → 输出：Hours_Per_Resident
```

**输出文件**：
- `results/per_capita_hours/per_capita_hours_summary.csv`
- `results/per_capita_hours/per_capita_hours_summary.xlsx`

**删除指标**：旧脚本中的 Person-Hours（人时）已被移除，仅保留 Hours/Resident（人均小时数）。

---

## 五、画图模块

### 5.1 模块化画图系统（`src/plotting/`）

| 文件 | 功能 |
|------|------|
| `style.py` | SCI 风格配置：Times New Roman + 中文后备字体、字号常量、7 情景调色板、3 策略调色板、`apply_sci_style()`、`despine_ax()` |
| `grouped_bar.py` | `plot_grouped_bar()` 通用函数 + `plot_scenario_grouped()`（情景对比）+ `plot_strategy_grouped()`（策略对比） |

### 5.2 论文画图脚本（`figure/daima/`）

**这些文件在项目重构后仍未被读取分析**。共 11 个文件，命名规则不明（如 figure2-b 和 figure2-b-去除文字 的关系不明）：

```
fig2-1地图-建筑气候区划.py     # 地图？建筑气候区划
figure2-b-去除文字.py           # "去除文字"版本含义待理解
figure2-c.py
figure2-d.py                    # 以上可能构成 Figure 2 的四个子图
figure3-a.py                    # Figure 3 子图
figure3-b.py
figure3-c.py
figure4-l.py                    # Figure 4 左/右子图
figure4-r.py
figure5.py
figure6.py                      # 涉及策略 A/B/C 决策（已推迟讨论）
```

> **待办**：这些文件包含作者原始的绘图逻辑和风格，建议未来读取代分析，提取其风格模式注入 `src/plotting/style.py`，然后逐步用 notebook + `grouped_bar.py` 替代脚本绘图。

---

## 六、已遇到的问题与待讨论事项

### 6.1 已解决

| 问题 | 决策 |
|------|------|
| 新旧版本并存（1.py+2.py vs 5.7） | 已重构融合为 step1_compute_set.py |
| 路径硬编码 | 已集中到 config/paths.py |
| CLO 值不统一（0.6 vs 0.8） | 统一为 0.8 |
| Person-Hours 冗余指标 | 已删除，仅保留 Hours/Resident |
| 命名混乱（1.py~5.py） | 已分解为有意义的模块名 |

### 6.2 待讨论/待确认

| 问题 | 说明 |
|------|------|
| **哈尔滨 / 天津是否包括** | 记忆文件记录 6 城市（不含哈尔滨），但 parameters.py 仍有哈尔滨配置。天津状态不明。待确认最终城市列表。 |
| **CLO 值 0.8 的影响** | 若未来与旧结果（CLO=0.6）对比，SET 值会有系统偏差。是否需要在论文中说明？ |
| **Figure 6 策略 A/B/C 选择** | 上一轮讨论中 deferred，内容丢失。需重新讨论。 |
| **天津的去留** | 旧项目有天津，重构版 cities 没有天津。是删除了还是遗漏？ |
| **画图代码风格统一** | figure/daima/ 下的 11 个脚本风格未经分析，不确定与 src/plotting/ 风格是否一致。 |

### 6.3 技术问题记录

| 问题 | 详情 |
|------|------|
| **Numba 内存爆炸** | pythermalcomfort.set_tmp 在 Numba 首次编译时消耗大量内存。多进程并发时需限制线程数（NUMBA_NUM_THREADS=1）并预热缓存。 |
| **Prompt Injection 中断工作流** | 在试图读取 figure/daima/ 脚本时，系统返回了嵌入注入文本的响应，导致多次读取失败和用户困惑。后续会话若需读取这些文件，应直接用 Read 工具读取。 |
| **Excel sheet 名 31 字符限制** | city_matcher.py 中有 `get_unique_sheet_name()` 处理此限制。 |
| **EPW 时间轴对齐** | 仿真 CSV 可能从年中开始，需通过 `get_epw_start_offset()` 对齐到 EPW 大气压序列。 |
| **EnergyPlus 24:00 问题** | EnergyPlus 在 24:00 表示当天结束（=次日 0:00），step1 中有特殊处理。 |

---

## 七、运行指南

### 安装依赖

```bash
cd "E:\cc data\thermal_comfort_analysis"
pip install -r requirements.txt
```

**核心依赖**：pythermalcomfort、pandas、numpy、matplotlib、seaborn、openpyxl、xlsxwriter、jupyter

### 一键运行

```bash
python scripts/run_all.py
```

### 分步运行

```bash
# Step 1: SET 计算
python src/pipeline/step1_compute_set.py

# Step 2: 人均不舒适小时数
python src/pipeline/step2_per_capita_hours.py

# 画图：打开 Jupyter Notebook
jupyter notebook notebooks/01_per_capita_grouped_bar.ipynb
jupyter notebook notebooks/02_three_strategies_compare.ipynb
```

### 验证方法

1. 对北京 2020 Baseline 跑 step1 → 行数和均值对照原 5.7 输出
2. 跑 step2 对北京 → 对照原 5.py 输出的 Hours/Resident 数值
3. Notebook 01 输出应与原 5.py 图片视觉一致
4. Notebook 02（三策略对比）：目测趋势合理性（扩容 < 现状，定容居中）

---

## 八、深圳热不舒适的建筑物理解释（导师问答备忘）

之前被导师追问"深圳缺乏保温标准，那散热不是更快吗"，以下是核心回答要点：

- **U 值（保温）** vs **ρc（蓄热）** 是两个独立维度
- 深圳建筑特点是 **保温差（高 U）+ 蓄热大（重混凝土 + 玻璃幕墙）** = 白天"快充"、晚上"慢放"
- 夜间散热率 = U × ΔT。深圳夜间室外 25-28°C，墙体内部 30-32°C → ΔT 仅 3-5°C
- 高 U 的优势被小 ΔT 抵消，且墙体不能降到 26°C 以下（与室外平衡）
- **建筑同期群效应**：深圳住宅 1990s-2010s 集中建成，同时进入热工性能衰退期，不像广深有 70-80 年代骑楼等被动设计建筑可以拉平均值

---

## 九、过去会话摘要与交接点

本项目经历过多次会话中断（context limit + prompt injection），以下是交接点：

1. **重构阶段**：已完成 project initialization（目录骨架、config、src/core、src/pipeline、src/plotting、notebooks、run_all）
2. **画图代码分析未完成**：figure/daima/ 下 11 个脚本从未成功读取
3. **Figure 6 决策未完成**：Strategy A/B/C 的优劣对比被推迟
4. **论文讨论**：前几图（Fig 1-5）的细节解读需继续，等画图代码理解后推进

**下次会话起始点**：读取 figure/daima/ 全部脚本 → 给出风格建议 → 回归 Fig 6 讨论。

---

## 十、联系方式与引用

项目维护者：D2DMH（用户）
论文引用：待补充

---

*最后更新：2026-05-09*
*README 重写原因：会话经 compact 后 context 清空，此文件作为项目知识库以便后续会话快速恢复认知。*
