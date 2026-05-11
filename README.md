# 城市住宅夜间热不舒适分析项目

> 气候变化背景下中国城市住宅夜间（22:00-7:00）热不舒适状况研究  
> 基于 EnergyPlus 仿真 + SET 热舒适指标 + 人口数据

---

## 📋 目录

- [项目概述](#项目概述)
- [快速开始](#快速开始)
- [数据准备](#数据准备)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [运行指南](#运行指南)
- [输出说明](#输出说明)
- [核心算法](#核心算法)
- [常见问题](#常见问题)
- [扩展指南](#扩展指南)

---

## 项目概述

### 研究目标

评估气候变化背景下中国主要城市住宅建筑在夜间睡眠时段（22:00-7:00）的热不舒适状况。核心指标为 **人均不舒适小时数（Hours/Resident）**——即每位居民在夜间经历 SET > 30°C 的总小时数。

### 研究范围

| 维度 | 内容 |
|------|------|
| **城市（6 个）** | 北京、上海、广州、深圳、武汉、厦门 |
| **气候情景（7 个）** | 2020 Baseline、2040 RCP 2.6/4.5/8.5、2060 RCP 2.6/4.5/8.5 |
| **空调策略（3 个）** | **现状**（Baseline_2020）、**扩容**（Capacity_expansion，autosize 27°C）、**定容**（Fixed_capacity，未来不加空调） |
| **温度基准（2 个）** | **27°C**（节能推荐，默认）、**26°C**（更舒适，敏感性分析） |
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
| MAX_WORKERS | 3 | 并行进程数（防 Numba 内存爆炸） |

---

## 快速开始

### 环境要求

- **Python**：3.8 或更高版本
- **操作系统**：Windows / Linux / macOS
- **内存**：建议 8GB 以上（多进程计算需要）

### 安装步骤

1. **克隆或下载项目**
   ```bash
   cd "E:\cc data\thermal_comfort_analysis"
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

   核心依赖包括：
   - `pythermalcomfort`：SET 热舒适计算
   - `pandas`、`numpy`：数据处理
   - `matplotlib`、`seaborn`：可视化
   - `openpyxl`、`xlsxwriter`：Excel 读写
   - `jupyter`：交互式画图

3. **准备数据**（详见[数据准备](#数据准备)章节）
   - 将输入数据放到 `data/input data/` 目录
   - 或使用外部路径（代码会自动检测）

4. **运行**
   ```bash
   python scripts/run_all.py
   ```

### 最简运行示例

```bash
# 一键运行完整流程（Step 1 → Step 2）
python scripts/run_all.py

# 查看结果
ls results/per_capita_hours/

# 打开 Jupyter Notebook 画图
jupyter notebook notebooks/01_per_capita_grouped_bar.ipynb
```

---

## 数据准备

### 数据组织结构

项目支持两种数据存放方式：

1. **项目内路径**（推荐）：`data/input data/` 和 `data/other data/`
2. **外部路径**（向后兼容）：`E:\GeiMingHao_all\`、`E:\映射\` 等

代码会**自动检测**：优先使用项目内路径，如果不存在则回退到外部路径。

### 项目内数据结构

```
data/
├── input data/
│   ├── GeiMingHao_26Degree/        # 26°C 温度基准（敏感性分析）
│   │   └── GeiMingHao_IndoorEnv/
│   │       ├── Baseline_2020/
│   │       ├── Capacity_expansion/
│   │       └── Fixed_capacity/
│   └── GeiMingHao_27Degree/        # 27°C 温度基准（默认）
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
└── README.md                       # 数据目录详细说明
```

详细的数据文件说明请查看 [data/README.md](data/README.md)。

### 外部路径（备用）

如果 `data/` 目录下没有数据，代码会自动使用以下外部路径：

- 仿真数据：`E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv\`
- EPW 文件：`E:\BaiduNetdiskDownload\newcity\`
- 人口数据：`E:\城市建筑_AOI_小区_POI_用途分类_人口结构_version4\`
- 映射文件：`E:\映射\`

---

## 配置说明

### 温度基准配置

**文件**：`config/parameters.py`

```python
# 当前使用的温度基准（26 或 27）
TEMPERATURE_BASELINE = 27  # 默认 27°C
```

**说明**：
- **27°C**：扩容策略下空调目标温度设为 27°C（节能推荐温度，默认）
- **26°C**：扩容策略下空调目标温度设为 26°C（更舒适但能耗更高）

**切换方式**：修改 `TEMPERATURE_BASELINE` 的值，然后重新运行。

**注意**：26°C 数据目前只有 3 个城市（广州、上海、厦门），代码会自动跳过没有数据的城市。

### 城市配置

**文件**：`config/parameters.py`

```python
CITY_CONFIGS = [
    {
        "pinyin": "bei3jing1shi4",
        "chn_name": "北京市",
        "code": "110000",
        "prov_folder": "110000北京市",
        "epw_keyword": "BEIJING",
    },
    # ... 其他城市
]
```

**添加新城市**：
1. 在 `CITY_CONFIGS` 列表中添加城市配置
2. 准备对应的仿真数据、映射文件、人口文件
3. 确保文件命名符合规范

### 路径配置

**文件**：`config/paths.py`

路径配置采用智能检测机制，通常不需要手动修改。如需自定义路径，可以修改：

```python
# 项目内数据路径
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
INPUT_DATA_ROOT = os.path.join(DATA_ROOT, "input data")
OTHER_DATA_ROOT = os.path.join(DATA_ROOT, "other data")

# 外部数据路径（备用）
SIMULATION_ROOT_OLD = r"E:\GeiMingHao_all\GeiMingHao_5.3\GeiMingHao_IndoorEnv"
# ...
```

### 计算参数配置

**文件**：`config/parameters.py`

```python
# SET 热舒适计算参数
MET = 0.7                # 代谢率（睡眠场景）
CLO = 0.8                # 服装热阻（被褥保温）
AIR_VELOCITY = 0.1       # 室内空气流速 [m/s]
RH_LIMIT = 60.0          # 空调环境相对湿度上限 [%]
SET_THRESHOLD = 30.0     # 夜间不舒适阈值 [°C SET]

# 多进程配置
MAX_WORKERS = 3          # 并行进程数（建议 2-4）
```

---

## 项目结构

```
E:\cc data\thermal_comfort_analysis\
│
├── config/                          # 配置层
│   ├── paths.py                     # 路径配置（智能检测）
│   ├── parameters.py                # 参数配置（温度基准、城市、情景）
│   └── __init__.py
│
├── src/                             # 核心代码层
│   ├── core/                        # 基础工具（不可变）
│   │   ├── epw_handler.py           # EPW 大气压读取、时间轴对齐
│   │   ├── set_calculator.py        # 向量化 SET 计算
│   │   ├── city_matcher.py          # Sheet 解析、建筑物编号提取
│   │   └── __init__.py
│   ├── pipeline/                    # 数据处理流程（可变）
│   │   ├── step1_compute_set.py     # SET 计算 + 夜间过热统计
│   │   ├── step2_per_capita_hours.py# 人均不舒适小时数计算
│   │   └── __init__.py
│   ├── plotting/                    # 可视化模块
│   │   ├── style.py                 # SCI 风格配置
│   │   ├── grouped_bar.py           # 分组柱状图
│   │   └── __init__.py
│   └── __init__.py
│
├── data/                            # 数据目录
│   ├── input data/                  # 输入数据（仿真结果）
│   ├── other data/                  # 辅助数据（人口、映射）
│   └── README.md                    # 数据目录说明
│
├── results/                         # 结果输出
│   ├── set_calculations/            # Step 1 输出
│   ├── per_capita_hours/            # Step 2 输出
│   └── figures/                     # 图表输出
│
├── notebooks/                       # 交互式画图
│   ├── 01_per_capita_grouped_bar.ipynb
│   └── 02_three_strategies_compare.ipynb
│
├── scripts/
│   └── run_all.py                   # 一键运行脚本
│
├── figure/daima/                    # 论文画图脚本（原始代码）
│
├── README.md                        # 本文件
├── algorithm.md                     # 算法实现说明
├── requirements.txt                 # Python 依赖
└── .gitignore
```

### 模块职责

| 模块 | 职责 | 关键函数/类 |
|------|------|-----------|
| `config/paths.py` | 路径管理，智能检测 | `get_data_path()`, `get_simulation_root()`, `get_strategy_dirs()` |
| `config/parameters.py` | 参数配置 | `TEMPERATURE_BASELINE`, `CITY_CONFIGS`, `SCENARIOS` |
| `src/core/epw_handler.py` | EPW 处理 | `extract_epw_pressure()`, `get_epw_start_offset()` |
| `src/core/set_calculator.py` | SET 计算 | `calculate_constrained_rh()`, `compute_set_vectorized()` |
| `src/core/city_matcher.py` | 标识符匹配 | `parse_sheet_metadata()`, `get_storey_number()` |
| `src/pipeline/step1_compute_set.py` | SET 计算流程 | `process_single_building()`, `build_task_list()` |
| `src/pipeline/step2_per_capita_hours.py` | 人均小时数 | `build_population_lookup()`, `process_single_excel()` |
| `src/plotting/style.py` | 绘图风格 | `apply_sci_style()`, `SCENARIO_PALETTE` |
| `src/plotting/grouped_bar.py` | 分组柱状图 | `plot_grouped_bar()`, `plot_scenario_grouped()` |

---

## 运行指南

### 一键运行

```bash
python scripts/run_all.py
```

这会依次执行：
1. Step 1：SET 计算 + 夜间过热统计
2. Step 2：人均不舒适小时数计算

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

### 切换温度基准

```bash
# 1. 修改配置
# 编辑 config/parameters.py，将 TEMPERATURE_BASELINE 改为 26

# 2. 重新运行
python scripts/run_all.py

# 3. 结果会保存到同一个 results/ 目录
# 注意：26°C 只有 3 个城市的数据
```

### 查看结果

```bash
# 查看 Step 1 输出
ls results/set_calculations/

# 查看 Step 2 输出
cat results/per_capita_hours/per_capita_hours_summary.csv

# 查看图表
ls results/figures/
```

---

## 输出说明

### Step 1 输出

**目录**：`results/set_calculations/`

**文件结构**：
```
set_calculations/
├── summary_uncomfortable_hours.csv    # 总汇总表
├── 现状/
│   └── {城市}/
│       └── {城市}_{情景}_SET.xlsx     # 逐时 SET/RH 大表
├── 扩容/
│   └── {城市}/
│       └── {城市}_{情景}_SET.xlsx
└── 定容/
    └── {城市}/
        └── {城市}_{情景}_SET.xlsx
```

**summary_uncomfortable_hours.csv 字段**：
- `策略`：现状 / 扩容 / 定容
- `城市`：城市拼音
- `情景`：2020 Baseline / 2040 RCP 2.6 等
- `建筑ID`：建筑文件名
- `楼层`：STOREY_0, STOREY_1 等
- `夜间总时数`：筛选后的夜间小时数
- `不舒适小时数`：SET > 30°C 的小时数

**逐时 SET Excel**：
- 每个 sheet 是一个建筑
- 列：Date/Time, Outdoor_Pressure_Pa, STOREY_X_SET, STOREY_X_RH
- 行：夜间 + HVAC 启用的时段

### Step 2 输出

**目录**：`results/per_capita_hours/`

**文件**：
- `per_capita_hours_summary.csv`：CSV 格式
- `per_capita_hours_summary.xlsx`：Excel 格式

**字段说明**：
- `策略`：现状 / 扩容 / 定容
- `城市`：城市中文名
- `城市拼音`：如 bei3jing1shi4
- `城市标签`：如 Bei3jing1s（用于画图）
- `情景`：2020 Baseline / 2040 RCP 2.6 等
- `Total_Person_Hours`：总人时（小时 × 人口）
- `Total_Population`：总人口
- `Hours_Per_Resident`：人均不舒适小时数（核心指标）

**数据规模**：
- 27°C 数据：约 126 行（3 策略 × 6 城市 × 7 情景）
- 26°C 数据：约 63 行（3 策略 × 3 城市 × 7 情景）

### 图表输出

**目录**：`results/figures/`

**文件**：
- `Grouped_BarChart_扩容_SCI_600DPI.png`：扩容策略跨城市对比
- `Grouped_BarChart_定容_SCI_600DPI.png`：定容策略跨城市对比
- `three_strategies_{情景}.png`：各情景下三策略对比

---

## 核心算法

详细的算法说明请查看 [algorithm.md](algorithm.md)。

### 数据处理流程

```
EnergyPlus CSV (三策略×城市×情景)
    ↓
[Step 1: SET 计算]
    ├─ 读取 EPW 大气压
    ├─ 时间轴对齐
    ├─ 筛选夜间 + HVAC 启用
    ├─ 向量化计算 SET
    └─ 统计不舒适小时数
    ↓
逐时 SET/RH Excel + 不舒适小时数 CSV
    ↓
[Step 2: 人均不舒适小时数]
    ├─ 加载人口数据 (Cluster 映射 + 建筑属性)
    ├─ 按 (Cluster, Fnum) 聚合人口
    ├─ 计算 Hours/Resident
    └─ 输出汇总表
    ↓
per_capita_hours_summary.csv
    ↓
[Notebooks 画图]
    ├─ 01_per_capita_grouped_bar.ipynb (跨城市分组柱状图)
    └─ 02_three_strategies_compare.ipynb (三策略对比)
```

### 关键设计假设

1. **楼层人口均匀分配**：每层楼住的人数 = 建筑总人口 / Fnum
2. **典型建筑代表性**：仿真的某栋建筑代表同 (Cluster, Fnum) 组合下所有建筑
3. **HVAC schedule 三策略一致**：定容下空调容量不够也仿照 schedule 启用
4. **RH 60% 上限**：模拟空调除湿效果，假设夏季空调环境下相对湿度不会超过 60%

---

## 常见问题

### Q1: 路径找不到怎么办？

**症状**：运行时报错 `FileNotFoundError` 或 `No such file or directory`

**解决方案**：
1. 检查数据是否已放到 `data/input data/` 或 `data/other data/` 目录
2. 如果使用外部路径，检查 `config/paths.py` 中的路径是否正确
3. 运行时会显示使用的路径，确认是否符合预期

### Q2: Numba 内存问题

**症状**：运行时内存占用过高，或出现 `MemoryError`

**解决方案**：
1. 减少 `config/parameters.py` 中的 `MAX_WORKERS`（默认 3，可改为 2 或 1）
2. 确保 `NUMBA_NUM_THREADS=1` 已设置（代码中已自动设置）
3. 关闭其他占用内存的程序

### Q3: 如何处理缺失数据？

**症状**：某些城市或情景没有数据

**解决方案**：
- 代码会自动跳过没有数据的城市/情景
- 检查日志输出，确认哪些数据被跳过
- 如需补充数据，按照 [data/README.md](data/README.md) 的说明准备数据文件

### Q4: 如何调整并行进程数？

**修改**：`config/parameters.py` 中的 `MAX_WORKERS`

```python
MAX_WORKERS = 3  # 改为 2 或 4
```

**建议**：
- 内存 8GB：MAX_WORKERS = 2
- 内存 16GB：MAX_WORKERS = 3-4
- 内存 32GB+：MAX_WORKERS = 4-6

### Q5: 26°C 和 27°C 数据可以同时处理吗？

**不可以**。每次运行只能处理一种温度基准。

**流程**：
1. 设置 `TEMPERATURE_BASELINE = 27`，运行一次
2. 设置 `TEMPERATURE_BASELINE = 26`，运行一次
3. 结果会保存到同一个 `results/` 目录，可以手动对比

### Q6: 如何验证结果正确性？

**验证方法**：
1. 对北京 2020 Baseline 运行 step1，检查输出行数和均值
2. 对比 `Hours_Per_Resident` 数值是否在合理范围（0-1000）
3. 检查三策略的趋势：扩容 < 现状，定容最高
4. 查看 Notebook 输出的图表，目测趋势是否合理

---

## 扩展指南

### 添加新的气候情景

1. **准备数据**：将新情景的 EnergyPlus 仿真结果放到对应目录
2. **更新配置**：在 `config/parameters.py` 的 `SCENARIOS` 字典中添加：
   ```python
   SCENARIOS = {
       # ... 现有情景
       "2080 RCP 8.5": "2080-rcp8.5",  # 新增
   }
   ```
3. **重新运行**：`python scripts/run_all.py`

### 修改 SET 计算参数

**文件**：`config/parameters.py`

```python
# 修改不舒适阈值
SET_THRESHOLD = 28.0  # 从 30°C 改为 28°C

# 修改服装热阻
CLO = 0.6  # 从 0.8 改为 0.6（更轻薄的被褥）
```

**注意**：修改参数后需要重新运行 Step 1 和 Step 2。

### 自定义可视化

**方式一**：修改现有 Notebook
- 打开 `notebooks/01_per_capita_grouped_bar.ipynb`
- 修改颜色、字体、图表类型等
- 重新运行 Notebook

**方式二**：使用 `src/plotting/` 模块
```python
from src.plotting.style import apply_sci_style, SCENARIO_PALETTE
from src.plotting.grouped_bar import plot_grouped_bar

# 应用 SCI 风格
apply_sci_style()

# 绘制自定义图表
plot_grouped_bar(data, x='城市', y='Hours_Per_Resident', hue='情景')
```

### 添加新城市

1. **准备数据**：
   - EnergyPlus 仿真结果（三策略 × 七情景）
   - Cluster 映射文件：`cluster_{code}_{城市名}.csv`
   - 人口属性文件：`T{code}_{城市名}_building_pop_attributes.csv`

2. **更新配置**：在 `config/parameters.py` 的 `CITY_CONFIGS` 中添加：
   ```python
   {
       "pinyin": "tian1jin1shi4",
       "chn_name": "天津市",
       "code": "120000",
       "prov_folder": "120000天津市",
       "epw_keyword": "TIANJIN",
   },
   ```

3. **重新运行**：`python scripts/run_all.py`

---

## 项目历史与维护

### 版本历史

- **2026-05-11**：重构路径系统，支持温度基准切换，完善文档
- **2026-05-09**：项目重构，模块化代码结构
- **2025-2026**：初始版本，基础功能实现

### 维护者

- **D2DMH**（用户）

### 引用

如果使用本项目的代码或数据，请引用：

```
[待补充论文引用信息]
```

---

## 许可证

[待补充]

---

*最后更新：2026-05-11*  
*README 重写原因：会话经 compact 后 context 清空，此文件作为项目知识库以便后续会话快速恢复认知。*
