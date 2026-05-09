# 算法实现说明

本文档描述 `thermal_comfort_analysis` 项目当前已实现的核心算法。

---

## 一、研究目标

评估 **气候变化背景下中国主要城市住宅居民在夜间睡眠时段（22:00-7:00）** 的热不舒适状况，并对比三种空调策略下的差异。

- **研究城市**：北京、上海、广州、深圳、武汉、厦门（共 6 个）
- **气候情景**：2020 基准 + 2040/2060 × RCP 2.6/4.5/8.5（共 7 个）
- **空调策略**：
  - **现状**：2020 EPW 气象 + 现有空调
  - **扩容**：未来气象 + EnergyPlus autosize 加装空调，目标室温 27°C
  - **定容**：未来气象 + 不加装空调，沿用现状容量
- **核心指标**：人均不舒适小时数（Hours / Resident）

---

## 二、整体流程

```
EnergyPlus 仿真 CSV ──┐
                      ├──► Step 1: 计算 SET，统计夜间过热小时数
EPW 气象大气压 ────────┘            │
                                   ▼
                          ┌── 每建筑各楼层逐时 SET 大表
                          └── 不舒适小时数 summary CSV
                                   │
建筑人口属性 + Cluster 映射 ──────►Step 2: 按 (Cluster, Fnum) 聚合人口
                                   │      → 计算 Hours / Resident
                                   ▼
                       per_capita_hours_summary.csv
                                   │
                                   ▼
                          notebooks 画图（SCI 风格）
```

---

## 三、Step 1：SET 计算与夜间过热统计

文件：`src/pipeline/step1_compute_set.py`

### 3.1 数据对齐

EnergyPlus CSV 是按 8760 小时仿真但起始日期可能不是 1/1。EPW 气象文件是全年 8760 小时。需要按 CSV 第一行的 `Date/Time` 字段（如 `05/01 01:00:00`）计算 EPW 的起始小时索引：

```python
start_idx = sum(每月天数前缀和) * 24 + (day - 1) * 24
end_idx = start_idx + len(df)
pressure_aligned = epw_pressure[start_idx:end_idx]
```

### 3.2 时段筛选

只保留满足以下条件的小时：

```
night_mask  = 小时 ∈ {22, 23, 24, 1, 2, 3, 4, 5, 6, 7}
sched_mask  = (COOLING_PERIOD_SCHEDULE > 0) & (HVAC_CONDITIONEDTIME_SCHEDULE > 0)
final_mask  = night_mask AND sched_mask
```

**说明**：HVAC schedule 是预设固定时段（不是温度触发），三策略下 HVAC 启用小时数完全相同（典型值 1416 小时 = 制冷季夜间）。

### 3.3 相对湿度计算（带 60% 上限）

由 EnergyPlus 输出的含湿量 `w [kg/kg]` 和 EPW 大气压 `p [Pa]` 计算相对湿度：

```python
es = 611.2 * exp(17.67 * tdb / (tdb + 243.5))     # 饱和水蒸气压 (Magnus 公式)
e  = p * w / (0.62198 + w)                         # 实际水蒸气压
rh = clip(e / es * 100, 0.1, 100)
rh_constrained = min(rh, RH_LIMIT)                 # RH_LIMIT = 60%
```

**60% 上限的含义**：模拟空调除湿效果，假设夏季空调环境下相对湿度不会超过 60%。

### 3.4 SET 计算

调用 `pythermalcomfort.set_tmp` 向量化计算每楼层的标准有效温度：

```python
set_vals = set_tmp(
    tdb = 该层室内空气温度,
    tr  = 该层平均辐射温度,
    v   = AIR_VELOCITY,        # 0.1 m/s
    rh  = rh_constrained,
    met = MET,                 # 0.7 (睡眠代谢率)
    clo = CLO,                 # 0.8 (睡衣 + 薄被)
    limit_inputs = False
)
```

**NaN 处理**：任一输入字段为 NaN 时，对应位置的 SET 也设为 NaN（不强制替换为占位值），调用方使用 `np.nansum` 自动排除。

### 3.5 夜间过热小时统计

```python
uncomfortable_hours = sum(SET > 30°C)   # 在 final_mask 时段内
```

每个 sheet 输出每楼层一行，写入：

- 逐时 SET/RH 大表 → `results/set_calculations/<策略>/<城市>/<城市>_<情景>_SET.xlsx`
- 汇总 CSV → `results/set_calculations/summary_uncomfortable_hours.csv`

字段：策略、城市、情景、建筑ID、楼层、夜间总时数、不舒适小时数

---

## 四、Step 2：人均不舒适小时数

文件：`src/pipeline/step2_per_capita_hours.py`

### 4.1 人口字典构建

按城市加载两份数据：

| 数据源 | 内容 |
|---|---|
| `cluster_<code>_<城市>.csv` | BuildingID → Cluster, landUseTyp, Fnum |
| `T<code>_<城市>_building_pop_attributes.csv` | BuildingID → Fnum, popNum_2 |

合并后：
1. 仅保留 `landUseTyp` 以 `Residential` 开头的建筑
2. 按 (Cluster, Fnum) 分组聚合 `popNum_2`，得到 `pop_lookup`

```
pop_lookup: (Cluster, Fnum) → Total_Pop
```

### 4.2 单建筑（单 sheet）处理

对 step1 输出的每个 sheet：

1. **从 sheet 名提取**：通过正则 `_(\d+)_(\d+)_` 解析出 `(BuildingType, cluster_id)`
   - BuildingType: 0=低层, 1=多层, 2=高层（隐含在 Fnum 里，无需额外过滤）
   - cluster_id: 城市内的聚类编号（不同城市互不通用）

2. **从 SET 列推断 Fnum**：
   ```python
   set_cols = [c for c in df.columns if c.endswith('_SET')]
   fnum = len(set_cols)
   ```
   即 STOREY 0, 1, 2, ..., n-1 共 n 层 → Fnum = n。

3. **查总人口**（精确匹配 Cluster + Fnum）：
   ```python
   total_pop = pop_lookup[(Cluster == cluster_id) & (Fnum == fnum)].Total_Pop.sum()
   ```
   该 (cluster, fnum) 组合下所有建筑的人口之和。

   > **关键**：由于 BuildingType 隐含在 Fnum 范围里（0=Fnum∈[0,3]，1=[4,6]，2=[7+]），不同 sheet 的 (cluster, fnum) 组合**完全不重叠**，不会重复计入人口。

4. **逐层累加人时**：
   ```python
   avg_pop_per_floor = total_pop / fnum     # 楼层人口均匀分配
   for col in set_cols:                     # 遍历每楼层
       uncomfortable_hours = sum(df[col] > 30)
       sum_person_hours += avg_pop_per_floor * uncomfortable_hours
   ```

5. **建筑总人口累加**：
   ```python
   sum_total_pop += total_pop
   ```

### 4.3 城市级聚合

对 (策略, 城市, 情景) 内的所有 sheet 累加，最后：

```python
Hours_Per_Resident = sum_person_hours / sum_total_pop
```

输出：`results/per_capita_hours/per_capita_hours_summary.csv`

字段：策略、城市、城市拼音、城市标签、情景、Total_Person_Hours、Total_Population、Hours_Per_Resident

---

## 五、关键参数与文献依据

| 参数 | 取值 | 含义 | 依据 |
|---|---|---|---|
| MET | 0.7 | 代谢率（睡眠场景） | 文献推荐值 |
| CLO | 0.8 | 服装热阻（睡衣 + 薄被） | 参考亚洲睡眠舒适研究 |
| AIR_VELOCITY | 0.1 m/s | 室内空气流速 | 静止空气近似 |
| RH_LIMIT | 60% | 相对湿度上限 | 模拟空调除湿 |
| SET_THRESHOLD | 30°C | 夜间不舒适阈值 | 参考论文 SET 不舒适度范围 |
| 夜间窗口 | 22:00-7:00 | 10 小时睡眠时段 | 研究设计 |

> **TODO**：在论文 method 部分需要明确引用 CLO=0.8、SET>30°C 阈值、MET=0.7 各自的文献来源。

---

## 六、关键设计假设

1. **楼层人口均匀分配**：每层楼住的人数 = 建筑总人口 / Fnum
2. **典型建筑代表性**：仿真的某栋建筑（BuildingType, cluster_id, fnum）的不舒适度，代表同 (Cluster, Fnum) 组合下所有建筑的居民
3. **HVAC schedule 三策略一致**：定容下空调容量不够也仿照 schedule 启用，相当于"空调一直开但温度降不下来"
4. **Grand Total 用人口加权平均**：跨城市汇总时按总人时除以总人口，与单城市口径一致

---

## 七、输出汇总

```
results/
├── set_calculations/
│   ├── summary_uncomfortable_hours.csv      ← 建筑 × 楼层级不舒适小时数
│   ├── 现状/<城市>/<城市>_<情景>_SET.xlsx     ← 逐时 SET/RH 大表
│   ├── 扩容/<城市>/<城市>_<情景>_SET.xlsx
│   └── 定容/<城市>/<城市>_<情景>_SET.xlsx
├── per_capita_hours/
│   ├── per_capita_hours_summary.csv         ← 78 行：策略 × 城市 × 情景
│   └── per_capita_hours_summary.xlsx
└── figures/
    ├── Grouped_BarChart_扩容_SCI_600DPI.png  ← 扩容版跨城市对比
    ├── Grouped_BarChart_定容_SCI_600DPI.png  ← 定容版跨城市对比
    └── three_strategies_<情景>.png            ← 各情景下三策略对比
```

---

## 八、待讨论 / 待优化

1. **RH 60% 上限**：实测显示扩容下 RH > 60% 比例 39%、定容 41%，差异不大，但定容下湿热不舒适可能被低估。论文需在 method 中明确说明此假设。
2. **代表性建筑的覆盖度**：当前 (Cluster, Fnum) 精确匹配会漏算 cluster 内未仿真的 fnum 对应的居民。武汉旧版/新版差异 5-7% 可能源于此。可考虑增加近似 fnum fallback。
3. **画图叙事**：后续画图思路待用户进一步说明。
