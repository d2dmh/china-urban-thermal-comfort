# 数据目录说明

本目录存放项目的所有输入数据。代码会自动检测此目录下的数据，如果不存在则回退到外部路径（向后兼容）。

---

## 目录结构

```
data/
├── input data/              # 仿真输入数据
│   ├── epw_files/           # EPW 气象文件（按情景分目录）
│   │   ├── 2020/
│   │   ├── 2040-rcp2.6/
│   │   ├── 2040-rcp4.5/
│   │   ├── 2040-rcp8.5/
│   │   ├── 2060-rcp2.6/
│   │   ├── 2060-rcp4.5/
│   │   └── 2060-rcp8.5/
│   ├── GeiMingHao_26Degree/ # 26°C 温度基准数据
│   │   └── GeiMingHao_IndoorEnv/
│   │       ├── Baseline_2020/
│   │       ├── Capacity_expansion/
│   │       └── Fixed_capacity/
│   └── GeiMingHao_27Degree/ # 27°C 温度基准数据（默认）
│       └── GeiMingHao_IndoorEnv/
│           ├── Baseline_2020/
│           ├── Capacity_expansion/
│           └── Fixed_capacity/
│               └── {城市拼音}/
│                   └── {情景}/
│                       └── *.csv
├── other data/              # 辅助数据
│   ├── 映射/                # Cluster 映射文件
│   └── 城市建筑_AOI_小区_POI_用途分类_人口结构_version4/
└── output data/             # 输出数据（未使用）
```

## 温度基准说明

| 温度基准 | 含义 | 数据覆盖城市 |
|---------|------|------------|
| **27°C** | 扩容策略下空调目标温度 27°C（默认） | 6 城市 |
| **26°C** | 扩容策略下空调目标温度 26°C | 3 城市（广州、上海、厦门） |

处理方式：`config/parameters.py` 中 `BASELINES = [26, 27]`，一次运行自动处理两个温度基准。

## EPW 文件

42 个 EPW 气象文件（7 情景 x 6 城市），来源：`C:\Users\31080\Desktop\zhongzi1`

## 外部路径备用

如果此目录没有数据，代码自动回退到外部路径（E:\ 盘），详见 `config/paths.py`。
