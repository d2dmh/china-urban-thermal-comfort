"""
热舒适计算参数 + 城市/情景配置。
"""

# ================= 温度基准配置 =================

# 当前使用的温度基准（26 或 27）
# 26°C：扩容策略下空调目标温度设为 26°C（更舒适但能耗更高）
# 27°C：扩容策略下空调目标温度设为 27°C（节能推荐温度，默认）
TEMPERATURE_BASELINE = 26  # 默认 27°C

# 温度基准对应的数据子目录名
TEMP_BASELINE_DIRS = {
    26: "GeiMingHao_26Degree",
    27: "GeiMingHao_27Degree",
}


# ================= SET 热舒适计算参数 =================

# 代谢率（睡眠场景）
MET = 0.7

# 服装热阻（被褥保温）
CLO = 0.8

# 室内空气流速 [m/s]
AIR_VELOCITY = 0.1

# 空调环境相对湿度上限 [%]
RH_LIMIT = 60.0

# 夜间不舒适阈值 [°C SET]
SET_THRESHOLD = 30.0

# 夜间时段（小时索引），24 代表 0:00
NIGHT_HOURS = [22, 23, 24, 1, 2, 3, 4, 5, 6, 7]


# ================= 城市配置 =================

CITY_CONFIGS = [
    {
        "pinyin": "bei3jing1shi4",
        "chn_name": "北京市",
        "code": "110000",
        "prov_folder": "110000北京市",
        "epw_keyword": "BEIJING",
    },
    {
        "pinyin": "shang4hai3shi4",
        "chn_name": "上海市",
        "code": "310000",
        "prov_folder": "310000上海市",
        "epw_keyword": "SHANGHAI",
        "custom_pop_filename": "T310000_上海市_building_pop.csv",
    },
    {
        "pinyin": "guang3zhou1shi4",
        "chn_name": "广州市",
        "code": "440100",
        "prov_folder": "440000广东省",
        "epw_keyword": "GUANGZHOU",
    },
    {
        "pinyin": "shen1zhen4shi4",
        "chn_name": "深圳市",
        "code": "440300",
        "prov_folder": "440000广东省",
        "epw_keyword": "SHENZHENSHI",
    },
    {
        "pinyin": "wu3han4shi4",
        "chn_name": "武汉市",
        "code": "420100",
        "prov_folder": "420000湖北省",
        "epw_keyword": "WUHAN",
    },
    {
        "pinyin": "xia4men2shi4",
        "chn_name": "厦门市",
        "code": "350200",
        "prov_folder": "350000福建省",
        "epw_keyword": "XIAMEN",
        "custom_pop_filename": "T350200_厦门市_building_pop.csv",
    },
]


# ================= 情景配置 =================

# 标签 → EnergyPlus 子文件夹/文件名关键字
SCENARIOS = {
    "2020 Baseline": "2020",
    "2040 RCP 2.6": "2040-rcp2.6",
    "2040 RCP 4.5": "2040-rcp4.5",
    "2040 RCP 8.5": "2040-rcp8.5",
    "2060 RCP 2.6": "2060-rcp2.6",
    "2060 RCP 4.5": "2060-rcp4.5",
    "2060 RCP 8.5": "2060-rcp8.5",
}

# 情景标签的展示顺序（画图用）
SCENARIO_ORDER = list(SCENARIOS.keys())


# ================= 多进程配置 =================

# 并行进程数（受 Numba/pythermalcomfort 内存影响，建议 2-4）
MAX_WORKERS = 4
