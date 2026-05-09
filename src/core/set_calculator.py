"""
SET（标准有效温度）计算：
- 由温度、含湿量、气压计算受限相对湿度
- 调用 pythermalcomfort 的向量化 set_tmp 接口

为了避免 Numba 多线程在子进程中导致内存爆炸，调用方应在导入
pythermalcomfort 之前设置 NUMBA_NUM_THREADS=1。
"""

import os

# 必须在导入 pythermalcomfort 之前设置（限制 Numba 线程，防多进程时内存爆炸）
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numpy as np
from pythermalcomfort.models import set_tmp


def calculate_constrained_rh(tdb, w_kg_kg, p_pa, rh_limit):
    """
    根据干球温度、含湿量、大气压计算相对湿度，并对超过 rh_limit 的值截断。

    向量化实现，输入为 numpy 数组。

    参数：
        tdb: 干球温度 [°C]
        w_kg_kg: 含湿量 [kg/kg]
        p_pa: 大气压 [Pa]
        rh_limit: 相对湿度上限 [%]（模拟空调除湿效果）

    返回：
        受限的相对湿度数组 [%]
    """
    try:
        tdb = np.asarray(tdb, dtype=float)
        w = np.maximum(np.asarray(w_kg_kg, dtype=float), 1e-6)
        p = np.asarray(p_pa, dtype=float)

        # 饱和水蒸气压（Magnus 公式）
        es = 611.2 * np.exp(17.67 * tdb / (tdb + 243.5))
        # 实际水蒸气压
        e = p * w / (0.62198 + w)
        rh = (e / es) * 100
        rh = np.clip(rh, 0.1, 100.0)

        # 应用空调除湿上限
        return np.where(rh > rh_limit, rh_limit, rh)
    except Exception:
        return np.full_like(np.asarray(tdb, dtype=float), np.nan)


def compute_set_vectorized(tdb, tr, v, rh, met, clo):
    """
    向量化计算 SET。利用 pythermalcomfort.set_tmp 的数组输入支持。

    参数：
        tdb: 干球温度数组 [°C]
        tr: 平均辐射温度数组 [°C]
        v: 空气流速（标量或数组）[m/s]
        rh: 相对湿度数组 [%]
        met: 代谢率（标量）
        clo: 服装热阻（标量）

    返回：
        SET 数组 [°C]，输入中含 NaN 的位置返回 NaN（由调用方决定是否跳过）
    """
    try:
        tdb_arr = np.asarray(tdb, dtype=float)
        tr_arr = np.asarray(tr, dtype=float)
        rh_arr = np.asarray(rh, dtype=float)

        # 标记任一输入为 NaN 的位置（这些位置 SET 不可信）
        nan_mask = np.isnan(tdb_arr) | np.isnan(tr_arr) | np.isnan(rh_arr)

        # 给 NaN 位置先填占位值供 set_tmp 计算（结果会被覆盖为 NaN）
        tdb_calc = np.where(nan_mask, 25.0, tdb_arr)
        tr_calc = np.where(nan_mask, 25.0, tr_arr)
        rh_calc = np.where(nan_mask, 50.0, rh_arr)

        res = set_tmp(tdb=tdb_calc, tr=tr_calc, v=v, rh=rh_calc,
                      met=met, clo=clo, limit_inputs=False)

        if hasattr(res, 'set'):
            set_vals = np.array(res.set)
        elif hasattr(res, 'set_tmp'):
            set_vals = np.array(res.set_tmp)
        elif isinstance(res, dict):
            set_vals = np.array(res.get('set', np.nan))
        elif isinstance(res, (list, np.ndarray)):
            set_vals = np.array(res)
        else:
            set_vals = np.full_like(tdb_calc, float(res))

        # 输入有 NaN 的位置 → SET 也设为 NaN，由调用方排除
        set_vals = set_vals.astype(float)
        set_vals[nan_mask] = np.nan
        return set_vals
    except Exception:
        return np.full_like(np.asarray(tdb, dtype=float), np.nan)


def warm_up_numba():
    """
    主进程预热 Numba 缓存：避免子进程并发首次编译时的内存抖动。
    应在启动多进程池之前调用一次。
    """
    try:
        set_tmp(tdb=25.0, tr=25.0, v=0.1, rh=50.0, met=1.2, clo=0.5)
    except Exception:
        pass
