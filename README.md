# 城市住宅夜间热不舒适分析项目

> 气候变化背景下中国城市住宅夜间（22:00-7:00）热不舒适状况研究  
> 基于 EnergyPlus 仿真 + SET 热舒适指标 + 人口数据

---

## 项目概述

### 研究目标

评估气候变化背景下中国主要城市住宅建筑在夜间睡眠时段（22:00-7:00）的热不舒适状况。核心指标为 **人均不舒适小时数（Hours/Resident）**——即每位居民在夜间经历 SET > 30°C 的总小时数。

### 研究范围

| 维度 | 内容 |
|------|------|
| **城市（6 个）** | 北京、上海、广州、深圳、武汉、厦门 |
| **气候情景（7 个）** | 2020 Baseline、2040 RCP 2.6/4.5/8.5、2060 RCP 2.6/4.5/8.5 |
| **空调策略（3 个）** | **现状**（Baseline_2020）、**扩容**（Capacity_expansion，autosize 目标温度）、**定容**（Fixed_capacity，未来不加空调） |
| **温度基准（2 个）** | **27°C**（节能推荐，6 城市）、**26°C**（敏感性分析，3 城市） |
| **建筑类型** | 0 = 低层、1 = 中层、2 = 高层 |
| **夜间窗口** | 22:00-7:00（共 10 小时） |

### 核心参数

| 参数 | 取值 | 说明 |
|------|------|------|
| MET | 0.7 | 代谢率（睡眠场景） |
| CLO | 0.8 | 服装热阻（睡衣 + 薄被） |
| AIR_VELOCITY | 0.1 m/s | 室内空气流速 |
| RH_LIMIT | 60% | 相对湿度上限（模拟空调除湿） |
| SET_THRESHOLD | 30°C | 夜间不舒适阈值 |
| MAX_WORKERS | 4 | 并行进程数（防 Numba 内存爆炸） |

---

## 快速开始

### 环境要求

- **Python**：3.8 或更高版本
- **操作系统**：Windows / Linux / macOS
- **内存**：建议 8GB 以上（多进程计算需要）

### 安装步骤

1. **进入项目目录**
   ```bash
   cd "E:\cc data\thermal_comfort_analysis"
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

   核心依赖：`pythermalcomfort`、`pandas`、`numpy`、`matplotlib`、`seaborn`、`openpyxl`、`xlsxwriter`、`jupyter`

3. **准备数据**（详见[数据准备](#数据准备)章节）

4. **一键运行**
   ```bash
   python scripts/run_all.py
   ```

---

## 数据准备

### 项目内数据结构

```
data/
├── input data/
│   ├── epw_files/                   # EPW 气象文件（按情景分目录）
│   │   ├── 2020/
│   │   ├── 2040-rcp2.6/
│   │   ├── 2040-rcp4.5/
│   │   ├── 2040-rcp8.5/
│   │   ├── 2060-rcp2.6/
│   │   ├── 2060-rcp4.5/
│   │   └── 2060-rcp8.5/
│   ├── GeiMingHao_26Degree/        # 26°C 温度基准
│   │   └── GeiMingHao_IndoorEnv/
│   │       ├── Baseline_2020/
│   │       ├── Capacity_expansion/
│   │       └── Fixed_capacity/
│   └── GeiMingHao_27Degree/        # 27°C 温度基准
│       └── GeiMingHao_IndoorEnv/
│           ├── Baseline_2020/
│           ├── Capacity_expansion/
│           └── Fixed_capacity/
│               └── {城市拼音}/     # 如 bei3jing1shi4
│                   └── {情景}/     # 如 2020, 2040-rcp2.6
│                       └── *.csv   # EnergyPlus 仿真结果
├── other data/
│   ├── 映射/
│   │   └── cluster_{code}_{城市名}.csv
│   └── 城市建筑_AOI_小区_POI_用途分类_人口结构_version4/
│       └── {省份文件夹}/
│           └── T{code}_{城市名}_building_pop_attributes.csv
└── README.md
```

详细说明见 [data/README.md](data/README.md)。

### 智能路径检测

代码优先使用 `data/` 下的项目内路径，如果不存在则回退到外部路径（E:\ 盘）。一般无需手动修改路径配置。

---

## 配置说明

### 温度基准

**文件**：`config/parameters.py`

```python
BASELINES = [26, 27]  # 一次运行同时处理两个温度基准
```

- **27°C**：扩容策略下空调目标温度 27°C（节能推荐，覆盖 6 城市）
- **26°C**：扩容策略下空调目标温度 26°C（敏感性分析，覆盖 3 城市：广州、上海、厦门）

不再需要手动切换温度基准，`run_all.py` 自动处理两个基准并将结果输出到不同子目录。

### 城市配置

```python
CITY_CONFIGS = [
    {"pinyin": "bei3jing1shi4", "chn_name": "北京市", "code": "110000",
     "prov_folder": "110000北京市", "epw_keyword": "BEIJING"},
    # ... 其他 5 个城市
]
```

### 计算参数

```python
MET = 0.7           # 代谢率（睡眠场景）
CLO = 0.8           # 服装热阻（被褥保温）
AIR_VELOCITY = 0.1  # 室内空气流速 [m/s]
RH_LIMIT = 60.0     # 空调环境相对湿度上限 [%]
SET_THRESHOLD = 30.0  # 夜间不舒适阈值 [°C SET]
MAX_WORKERS = 4     # 并行进程数
```

---

## 项目结构

```
E:\cc data\thermal_comfort_analysis\
│
├── config/                          # 配置层
│   ├── paths.py                     # 路径配置（智能检测）
│   ├── parameters.py                # 参数配置
│   └── __init__.py
│
├── src/                             # 核心代码层
│   ├── core/                        # 基础工具
│   │   ├── epw_handler.py           # EPW 大气压读取
│   │   ├── set_calculator.py        # 向量化 SET 计算
│   │   ├── city_matcher.py          # Sheet 解析、编号提取
│   │   └── __init__.py
│   ├── pipeline/                    # 数据处理流程
│   │   ├── step1_compute_set.py     # SET 计算 + 夜间过热统计
│   │   ├── step2_per_capita_hours.py# 人均不舒适小时数
│   │   ├── step3_pivot_tables.py    # 透视表生成
│   │   └── __init__.py
│   ├── plotting/                    # 可视化模块
│   │   ├── style.py                 # SCI 风格配置
│   │   ├── grouped_bar.py           # 分组柱状图
│   │   └── __init__.py
│   └── __init__.py
│
├── data/                            # 数据目录（.gitignore）
│   ├── input data/                  # 仿真输入数据
│   ├── other data/                  # 辅助数据
│   └── README.md
│
├── results/                         # 结果输出
│   ├── 26Degree/                    # 26°C 结果
│   │   ├── set_calculations/        # Step 1 输出
│   │   ├── per_capita_hours/        # Step 2 输出
│   │   └── pivot_tables/           # Step 3 输出
│   ├── 27Degree/                    # 27°C 结果
│   │   ├── set_calculations/
│   │   ├── per_capita_hours/
│   │   └── pivot_tables/
│   └── figures/                     # 图表输出
│       ├── 26Degree/
│       └── 27Degree/
│
├── notebooks/                       # 交互式画图
│   └── 01_per_capita_grouped_bar.ipynb
│
├── scripts/
│   └── run_all.py                   # 一键运行脚本
│
├── figure/daima/                    # 论文画图脚本（原始代码）
│
├── README.md                        # 本文件
├── requirements.txt                 # Python 依赖
└── .gitignore
```

---

## 运行指南

### 一键运行

```bash
python scripts/run_all.py
```

依次执行：
1. Step 1：SET 计算 + 夜间过热统计（26°C + 27°C）
2. Step 2：人均不舒适小时数（26°C + 27°C）
3. Step 3：透视表生成（26°C + 27°C）

### 分步运行

```bash
python src/pipeline/step1_compute_set.py
python src/pipeline/step2_per_capita_hours.py
python src/pipeline/step3_pivot_tables.py
```

### 画图

```bash
jupyter notebook notebooks/01_per_capita_grouped_bar.ipynb
```

图表自动适配两个温度基准，保存到 `results/figures/26Degree/` 和 `results/figures/27Degree/`。

---

## 输出说明

### Step 1 输出

**目录**：`results/{26,27}Degree/set_calculations/`

```
set_calculations/
├── summary_uncomfortable_hours.csv    # 总汇总表
├── 现状/
│   └── {城市}/
│       └── {城市}_{情景}_SET.xlsx     # 逐时 SET/RH 大表
├── 扩容/
│   └── ...
└── 定容/
    └── ...
```

**逐时 SET Excel**：每个 sheet 是一个建筑，列包含 Date/Time、Outdoor_Pressure_Pa、STOREY_X_SET、STOREY_X_RH。

### Step 2 输出

**目录**：`results/{26,27}Degree/per_capita_hours/`

- `per_capita_hours_summary.csv` / `.xlsx`

字段：温度基准、策略、城市、城市拼音、城市标签、情景、Total_Person_Hours、Total_Population、Hours_Per_Resident

### Step 3 输出

**目录**：`results/{26,27}Degree/pivot_tables/`

- `hourly_set_detail.csv`：逐时 SET 明细（所有建筑×楼层×时刻）
- `annual_uncomfortable_summary.xlsx`：每建筑每楼层的不舒适小时汇总

---

## 核心算法

### 数据处理流程

```
EnergyPlus CSV (三策略×城市×情景, 26°C + 27°C)
    ↓
[Step 1: SET 计算]
    ├─ 读取 EPW 大气压
    ├─ 时间轴对齐
    ├─ 筛选夜间 + HVAC 启用
    ├─ 向量化计算 SET
    └─ 统计不舒适小时数
    ↓
逐时 SET/RH Excel → results/{26,27}Degree/set_calculations/
    ↓
[Step 2: 人均不舒适小时数]
    ├─ 加载人口数据
    ├─ 按 (Cluster, Fnum) 聚合
    └─ 计算 Hours/Resident
    ↓
per_capita_hours_summary.csv → results/{26,27}Degree/per_capita_hours/
    ↓
[Step 3: 透视表]
    ├─ hourly_set_detail.csv
    └─ annual_uncomfortable_summary.xlsx
    ↓
[Notebook 画图]
    读取 per_capita_hours/ → 分组柱状图 → results/figures/
```

详细算法说明见 [algorithm.md](algorithm.md)。

---

## 常见问题

### Q1: 路径找不到

检查数据是否已放到 `data/input data/` 或 `data/other data/` 目录。代码会自动检测并显示使用的路径。

### Q2: Numba 内存问题

减少 `config/parameters.py` 中的 `MAX_WORKERS`（建议 2-4）。

### Q3: 26°C 数据缺失

26°C 目前只有广州、上海、厦门 3 个城市的数据，代码会自动跳过没有数据的城市。

### Q4: 如何验证结果

1. 检查 `summary_uncomfortable_hours.csv` 的行数和均值
2. Hours_Per_Resident 应在合理范围（0-1000）
3. 三策略趋势：扩容 < 现状，定容最高

---

## 扩展指南

### 添加新城市

在 `config/parameters.py` 的 `CITY_CONFIGS` 中添加配置，准备对应的仿真数据、映射文件和人口文件。

### 修改 SET 参数

编辑 `config/parameters.py` 中的 MET、CLO、SET_THRESHOLD 等参数，重新运行 Step 1-3。

---

*最后更新：2026-05-11*
