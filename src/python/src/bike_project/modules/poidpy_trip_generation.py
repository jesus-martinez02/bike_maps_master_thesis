
from poidpy.pois import create_POIs_polygon
from poidpy.attraction_production import attraction_production_from_OD, attraction_production_from_file
from poidpy.io import read_pickle
from poidpy.poi_visualisation import *

import geopandas as gpd
import pandas as pd
import numpy as np

from sqlalchemy import text


def poidpy_trip_generation(db_engine, grid_table,pois_table_name):
    """
    Calculates Poidpy zonal attraction and production based on POIs
    """
    grid_fetch_query = f"SELECT * FROM {grid_table}"
    query_cc = f"SELECT * FROM {grid_table} WHERE city_center = 'Yes';"
    zones_gdf = gpd.GeoDataFrame.from_postgis(grid_fetch_query, db_engine, crs = "EPSG:4326").rename(columns={"geom": "geometry"})
    zones_gdf = zones_gdf.sort_values("id", ascending=True)
    zones_gdf = zones_gdf.reset_index(drop=True)
    print(zones_gdf)
    zones_gdf = zones_gdf.set_geometry("geometry", crs="EPSG:4326")
    city_center_gdf = gpd.GeoDataFrame.from_postgis(query_cc, db_engine).rename(columns={"geom": "geometry"})
    poly = zones_gdf["geometry"].union_all()
    POIs = create_POIs_polygon(poly, city_center=city_center_gdf, class_name="ignored", timeout=1000)
    zones_gdf = zones_gdf.set_geometry("geometry", crs="EPSG:4326")


    categorized_pois = POIs.pois_categorized
    exclude_cols = ['building:levels', 'addr:housenumber','priority']
    string_cols = categorized_pois.select_dtypes(include=['object', 'string']).drop(columns = exclude_cols)

    categorized_pois['non_null_string_count'] = ((string_cols.notna()) & (string_cols != '')).sum(axis=1)

    categorized_pois['exclude_poi'] = (categorized_pois["non_null_string_count"] == 1) & (categorized_pois["building"].isin(["commercial"]))
    categorized_pois_clean = categorized_pois[(~categorized_pois["landuse_outer"].str.contains('industrial')) & (categorized_pois['exclude_poi'] == False)]
    POIs.pois_categorized = categorized_pois_clean
    POIs.aggregate_over_zones(zones_gdf, zone_id_column='id')
    POIs.pois_categorized.to_postgis(pois_table_name,db_engine,if_exists = "replace")

    
    zones_gdf = make_reggression_from_pois(POIs, zones_gdf)
    print(zones_gdf)

    return zones_gdf

def make_reggression_from_pois(POIs, zones_gdf):
    """
    Makes Multiple Linear Regression based on POIs using coefficeints calibrated on Madrid BiciMad bike-sharing data
    """
    # Perform reggression
    variables = ['small_residential', 'large_residential']
    coeff = [0.005987, 0.008741]
    zones_gdf['prod_pred'] = 0.1 + (POIs.zones[variables] * coeff).sum(axis=1)
    variables = ['small_residential', 'large_residential']


    
    # variables = ['School', 'Services', 'Catering_industry',  'Industry', 'Others', 'total_residential']
    # coeff = [0.031445, 0.019582, 0.029253, 0.001579, 0.088157, 0.004037]
    # coeff = [c * 0.64 for c in [0.031445, 0.019582, 0.029253, 0.001579, 0.088157]] + [0.004037] # corrected for population density

    #######
    #######
    ### New coefficients, calibrated on Madrid

    variables = ['Leisure', 'Shops', 'Services', 'Catering_industry', 'Tourism', 'Leisure_area']
    coeff = [0.0526, 0.2844, 0.0273, 0.8890, 0.4160, 0.0156]

    zones_gdf['attr_pred'] = +  (POIs.zones[variables] * coeff).sum(axis=1)

    return zones_gdf


