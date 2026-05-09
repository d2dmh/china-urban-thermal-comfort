# ==========================================
# 6城市 × 3情形 3D叠层批处理 (完全复刻3D逻辑 + 市中心红星)
# ==========================================
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import shapely.affinity
from shapely.geometry import Polygon, Point
import warnings

warnings.filterwarnings("ignore")

# ==================== 0. 基础配置与城市中心坐标 ====================
# ！！！ 核心修复：请在这里填入您实际的区县级行政边界 shapefile 路径 ！！！
COUNTY_SHP_PATH = r"E:\中国标准地图-审图号GS(2024)0650号-shp格式\面格式\中国_县_Albers.shp" # 👈 请务必核对并修改此路径

# 严格按照 WGS84 坐标定义各城市中心 (通常为市政府所在地)
CITY_CENTERS_WGS84 = {
    '北京市': (116.4074, 39.9042),
    '武汉市': (114.3055, 30.5928),
    '上海市': (121.4737, 31.2304),
    '广州市': (113.2644, 23.1291),
    '深圳市': (114.0596, 22.5429),
    '厦门市': (118.0894, 24.4798)
}

CITY_SPECIFIC_PARAMS = {
    "北京市": {"grid_sz": 1000, "min_grids": 150, "density": 0.15},
    "上海市": {"grid_sz": 1000, "min_grids": 150, "density": 0.15},
    "广州市": {"grid_sz": 1000, "min_grids": 100, "density": 0.10},
    "深圳市": {"grid_sz": 500,  "min_grids": 200, "density": 0.15}, 
    "厦门市": {"grid_sz": 500,  "min_grids": 200, "density": 0.15},
    "武汉市": {"grid_sz": 1000, "min_grids": 150, "density": 0.15},
}

# ==================== 1. 严格复刻 3D 变换函数 ====================
def transform_to_3d_strict(geom, z_offset=0):
    if geom is None or geom.is_empty: return geom
    tilt_z_deg = 60  
    rot_flat_deg = 0
    rx, rz = np.radians(tilt_z_deg), np.radians(rot_flat_deg)
    
    # 严格遵循用户提供的 a, b, d, e 矩阵计算方式
    a, b = np.cos(rz), -np.sin(rz)
    d, e = np.sin(rz) * np.cos(rx), np.cos(rz) * np.cos(rx)
    xoff, yoff = 0, -z_offset 
    
    return shapely.affinity.affine_transform(geom, [a, b, d, e, xoff, yoff])

def apply_3d_strict(gdf, z_offset=0):
    if gdf is None or gdf.empty: return gdf
    gdf_3d = gdf.copy()
    gdf_3d['geometry'] = gdf_3d.geometry.apply(lambda geom: transform_to_3d_strict(geom, z_offset))
    return gdf_3d

# ==================== 2. 批处理主循环 ====================
print("正在加载底图...")
counties_raw = gpd.read_file(COUNTY_SHP_PATH)
counties_raw['area_km2'] = counties_raw.geometry.area / 1e6
counties_all = counties_raw.to_crs('EPSG:3857')

for city_name, params in CITY_SPECIFIC_PARAMS.items():
    if city_name not in cities_info: continue
    paths = cities_info[city_name]
    grid_sz, m_grids, m_dens = params["grid_sz"], params["min_grids"], params["density"]
    
    print(f"\n🚀 正在绘制 3D 视角: {city_name}")
    
    try:
        # --- A. 数据融合与网格化 ---
        buildings = gpd.read_file(paths['shp'])
        pop_df = load_table(paths['pop'], POP_COLS)
        heat_df = load_table(paths['heat'], HEAT_COLS)
        for df in [buildings, pop_df, heat_df]:
            df['BuildingID'] = df['BuildingID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        df_merged = pop_df.merge(heat_df, on='BuildingID', how='inner')
        df_merged['Vulnerability'] = (df_merged['age0_2'] + df_merged['age65abv_2']).fillna(0)
        gdf_merged = buildings.merge(df_merged, on='BuildingID', how='inner').to_crs('EPSG:3857')
        
        china_cities = gpd.read_file(CITY_BOUNDS_SHP)
        city_mask = china_cities[china_cities.astype(str).apply(lambda x: x.str.contains(city_name[:2])).any(axis=1)]
        city_limit = city_mask.iloc[[0]].to_crs('EPSG:3857') if not city_mask.empty else None
        
        grid_base = create_clipped_grid(city_limit if city_limit is not None else gdf_merged, grid_size=grid_sz)
        joined = gpd.sjoin(gdf_merged.copy().set_geometry(gdf_merged.centroid), grid_base, how='left', predicate='within')
        grid_stats = joined.groupby('index_right').agg({'Vulnerability': 'sum', '人均受灾小时数_2020': 'mean', 
                                                        '人均受灾小时数_2040-rcp8.5': 'mean', '人均受灾小时数_2060-rcp8.5': 'mean'}).reset_index()
        grid_city = grid_base.merge(grid_stats, left_index=True, right_on='index_right', how='right').dropna()

        # 锁定全情形阈值
        all_heat = pd.concat([grid_city['人均受灾小时数_2020'], grid_city['人均受灾小时数_2040-rcp8.5'], grid_city['人均受灾小时数_2060-rcp8.5']]).dropna()
        h_mid = (np.percentile(all_heat, HEAT_LOWER_PERCENTILE) + np.percentile(all_heat, HEAT_UPPER_PERCENTILE)) / 2
        v_mid = (np.percentile(grid_city['Vulnerability'], VUL_LOWER_PERCENTILE) + np.percentile(grid_city['Vulnerability'], VUL_UPPER_PERCENTILE)) / 2

        # --- B. 核心行政边界筛选 ---
        pts = gpd.GeoDataFrame(geometry=grid_city.centroid, crs=grid_city.crs)
        joined_counties = gpd.sjoin(pts, counties_all, how='inner', predicate='intersects')
        counts = joined_counties['index_right'].value_counts().rename('grid_count')
        curr_counties = counties_all.copy().merge(counts, left_index=True, right_index=True, how='left').fillna(0)
        curr_counties['density_ratio'] = (curr_counties['grid_count'] * ((grid_sz**2)/1e6)) / curr_counties['area_km2']
        core_counties = curr_counties[(curr_counties['grid_count'] >= m_grids) | (curr_counties['density_ratio'] >= m_dens)]
        
        core_hull = gpd.GeoDataFrame(geometry=[core_counties.unary_union], crs=grid_city.crs)
        core_hull['geometry'] = core_hull['geometry'].apply(lambda g: Polygon(g.exterior) if g.geom_type == 'Polygon' else g)
        grid_core = gpd.clip(grid_city, core_hull)

        # --- C. 计算并变换市中心五角星 ---
        lon, lat = CITY_CENTERS_WGS84[city_name]
        star_point_3857 = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs("EPSG:3857")[0]
        # 应用 3D 变换 (z_offset=0 确保它在顶层)
        star_3d = transform_to_3d_strict(star_point_3857, z_offset=0)

        # --- D. 绘图 (3D 叠层 + 五角星) ---
        fig, axes = plt.subplots(1, 4, figsize=(28, 10), gridspec_kw={'width_ratios': [1, 1, 1, 0.7]}, facecolor='none')
        fig.patch.set_alpha(0.0)
        
        scenarios = [('2020', '2020 现状'), ('2040-rcp8.5', '2040 RCP8.5'), ('2060-rcp8.5', '2060 RCP8.5')]
        minx, miny, maxx, maxy = core_hull.total_bounds
        dynamic_thickness = (maxy - miny) * 0.03

        for i, (yr, ttl) in enumerate(scenarios):
            ax = axes[i]
            ax.set_facecolor('none')
            ax.set_axis_off()

            # 1. 底座阴影 (15层)
            for z in np.linspace(dynamic_thickness, 0, 15):
                apply_3d_strict(core_hull, z_offset=z).plot(ax=ax, facecolor='#cccccc', edgecolor='none', zorder=1)

            # 2. 顶层底盘
            hull_top = apply_3d_strict(core_hull, z_offset=0)
            hull_top.plot(ax=ax, facecolor='#F7F7F7', edgecolor='none', zorder=2)

            # 3. 2x2 网格
            grid_core[f'clr_{yr}'] = grid_core.apply(lambda r: f"{get_class_2x2(r[f'人均受灾小时数_{yr}'], h_mid)}-{get_class_2x2(r['Vulnerability'], v_mid)}", axis=1)
            grid_3d = apply_3d_strict(grid_core, z_offset=0)
            for c_class, hex_c in bivariate_colors_2x2.items():
                subset = grid_3d[grid_3d[f'clr_{yr}'] == c_class]
                if not subset.empty:
                    subset.plot(ax=ax, color=hex_c, edgecolor='none', zorder=3)
            
            # 4. 行政边界线
            apply_3d_strict(core_counties, z_offset=0).boundary.plot(ax=ax, color='#888888', linewidth=0.6, zorder=4)
            hull_top.boundary.plot(ax=ax, color='#666666', linewidth=1.2, zorder=5)

            # 5. ⭐ 绘制红星 (zorder 设为最高)
            ax.scatter(star_3d.x, star_3d.y, marker='*', color='red', edgecolor='white', s=700, zorder=15, label="市中心")

            ax.set_title(f"【{city_name}】 {ttl}", fontsize=20, pad=20, fontweight='bold')
            viz_bounds = hull_top.total_bounds
            ax.set_xlim(viz_bounds[0] - 5000, viz_bounds[2] + 5000)
            ax.set_ylim(viz_bounds[1] - 10000, viz_bounds[3] + 5000)

        # 索引图
        ax_idx = axes[3]
        idx_pts = gpd.GeoDataFrame(geometry=counties_all.centroid, crs=counties_all.crs)
        idx_match = gpd.sjoin(idx_pts, city_limit[['geometry']], how='inner', predicate='within')
        all_city_counties = counties_all.loc[idx_match.index]
        all_city_counties.plot(ax=ax_idx, color='#EEEEEE', edgecolor='#B0B0B0', linewidth=0.5)
        core_counties.plot(ax=ax_idx, color='#E67E22', alpha=0.8)
        core_counties.boundary.plot(ax=ax_idx, color='#C0392B', linewidth=0.5)
        core_hull.boundary.plot(ax=ax_idx, color='#D35400', linewidth=1.0)
        ax_idx.set_title("区域索引 (平面)", fontsize=18)
        ax_idx.set_axis_off()

        plt.subplots_adjust(wspace=0.05)
        save_path = os.path.join(OUTPUT_DIR, f"{city_name}_3D_Star_600dpi.png")
        plt.savefig(save_path, dpi=600, bbox_inches='tight', transparent=True)
        plt.show()

    except Exception as e:
        print(f"❌ 处理 {city_name} 错误: {e}")

print("\n🎉 任务完成！五角星已精准嵌入 3D 地图。")