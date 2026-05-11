"""
一键运行：依次执行 step1 → step2 → step3。
画图请打开 notebooks/ 下的 .ipynb 文件交互式运行。
"""

import os
import sys
import multiprocessing

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    print("\n" + "=" * 70)
    print("  执行 Step 1: SET 计算 + 夜间过热统计")
    print("=" * 70)
    from src.pipeline.step1_compute_set import main as step1_main
    step1_main()

    print("\n" + "=" * 70)
    print("  执行 Step 2: 人均不舒适小时数")
    print("=" * 70)
    from src.pipeline.step2_per_capita_hours import main as step2_main
    step2_main()

    print("\n" + "=" * 70)
    print("  执行 Step 3: 透视表")
    print("=" * 70)
    from src.pipeline.step3_pivot_tables import main as step3_main
    step3_main()

    print("\n>> 全部流程完成！")
    print("   下一步：打开 notebooks/01_per_capita_grouped_bar.ipynb 画图")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
