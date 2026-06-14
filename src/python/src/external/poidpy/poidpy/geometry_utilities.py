"""
Utilities
"""

# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers and Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

# Internal modules
from .settings import *
from .osm_classification import tag_priority_default

# Other packages
import pandas as pd
import geopandas as gpd
import numpy as np


def create_polygon(path_to_shapefile, buffer=100, projected_epsg=proj_crs):
    gdf = gpd.read_file(path_to_shapefile)
    gdf_epsg = gdf.crs.to_epsg()
    if gdf.crs != projected_epsg:
        gdf = gdf.to_crs(projected_epsg)
    gdf['buffer_area'] = gdf.geometry
    if buffer > 0:
        gdf.loc[:, 'buffer_area'] = gdf.buffer_area.buffer(distance=buffer)
    gdf.loc[:, 'geometry'] = gdf.buffer_area
    gdf = gdf.to_crs(gdf_epsg)
    poly = gdf.geometry.unary_union
    return poly


def polygon_area_gdf(gdf, proj_crs=proj_crs):
    if 'polygon_area' in gdf.columns:
        gdf.drop('polygon_area', axis=1, inplace=True)

    proj_gdf = gdf.to_crs(proj_crs)
    print(f"Projected crs: {proj_crs} used to calculate polygon area.")
    pol_area = proj_gdf.area
    gdf.loc[:, 'polygon_area'] = pol_area
    return gdf


def polygon_to_centroid(gdf, proj_crs=None):
    current_crs = gdf.crs.to_epsg()
    if proj_crs is None:
        proj_crs = etrs89_eu
    gdf = gdf.to_crs(proj_crs)
    centroids = gdf.geometry.centroid
    gdf = gpd.GeoDataFrame(gdf, geometry=centroids)
    gdf = gdf.to_crs(current_crs)
    return gdf


def _assign_priority(gdf, priority_list=None, column_name=None):
    """
    Prioritize POI by the tag values present for every object. The priority is hard coded in osm_classification.py and
    states which tag attributes contain the most accurate information to classify a geometry.

    Parameters
    ----------
    gdf
    priority_list
    column_name

    Returns
    -------

    """
    gdf = gdf.copy()
    if priority_list is None:
        priority_list = tag_priority_default
    if column_name is None:
        column_name = priority_column
    print(len(gdf))
    gdf.loc[:, column_name] = None
    for i, j in enumerate(priority_list):
        index_none = set(gdf[gdf[column_name].isna()].index)
        index_value = set(gdf[gdf[j].notna()].index)
        gdf.loc[list(index_none.intersection(index_value)), column_name] = j
    return gdf


def split_by_geometry(gdf: object, area_pol: object = True) -> object:
    """
    Split full geodataframe by geometry type, distinguish Point and (Multi)Polygon
    LineStrings are not of any relevance, number of is very low
    Keep specified columns for each geodataframe
    :param gdf: geodataframe with OSM data, mixed types
    :param area_pol:
    """
    gdf_pnt, gdf_pol = gdf.loc[gdf.type == 'Point'].copy(), gdf.loc[gdf.type.isin(['Polygon', 'MultiPolygon'])].copy()
    if area_pol:
        gdf_pol = gdf_pol.copy()
        gdf_pol = polygon_area_gdf(gdf_pol)
        gdf_pnt.loc[:, 'polygon_area'] = 0
    return gdf_pnt, gdf_pol


def points_in_poly(gdf_pnt, gdf_poly):
    tmp = gpd.sjoin(gdf_pnt, gdf_poly, how='inner', op='within', lsuffix='pnt', rsuffix='poly')
    tmp_count = tmp.groupby('osmid_poly').count()
    tmp_count.rename(columns={'osmid_pnt': point_count}, inplace=True)
    tmp = pd.merge(tmp, tmp_count[point_count], left_on='osmid_poly', right_index=True, how='left')
    return tmp


def contains_polygon(gdf, mode='difference'):
    """
    Contains for polygon layer
    Parameters
    ----------
    gdf
    mode : ['difference', 'join', 'remove']

    Returns
    -------

    """
    assert mode in ['difference', 'join', 'remove']

    df_contains = gpd.sjoin(gdf, gdf, how='left', predicate='contains', lsuffix='1', rsuffix='2')
    df_contains = df_contains.loc[df_contains['osmid_1'] != df_contains['osmid_2'], ['osmid_1', 'osmid_2']]
    contain_dic = {'index': [], 'contained': []}

    for id_val, val in enumerate(df_contains['osmid_1'].unique()):
        contain_dic['index'].append(val)
        contain_dic['contained'].append(df_contains.loc[df_contains['osmid_1'] == val, 'osmid_2'].to_list())

    contain_dic = pd.DataFrame(contain_dic)
    contain_dic[point_count] = list(map(len, contain_dic['contained']))
    contained_index = [i for sub in contain_dic.loc[contain_dic.contained.notna(), 'contained'].to_list() for i in sub]
    gdf_contained = gdf.loc[gdf.osmid.isin(contained_index)].copy()
    gdf_not_contained = gdf.loc[~gdf.osmid.isin(contained_index)].copy()
    if mode == 'difference':
        gdf_not_contained_cut = gpd.overlay(gdf_not_contained, gdf_contained, how='difference', keep_geom_type=True)
        gdf_not_contained_cut.index = gdf_not_contained[gdf_not_contained['osmid'].isin(gdf_not_contained_cut['osmid'].to_list())].index
        gdf.loc[gdf_not_contained[gdf_not_contained['osmid'].isin(gdf_not_contained_cut['osmid'].to_list())].index] = gdf_not_contained_cut
        gdf = gdf.drop(gdf_not_contained[~gdf_not_contained['osmid'].isin(gdf_not_contained_cut['osmid'].to_list())].index)
        # gdf = pd.concat([gdf_not_contained_cut, gdf_contained], axis=0)
        # gdf includes all contained polygon features (gdf_contained)
        # and the surrounding polygon features with the contained polygons cut out (gdf_not_contained_cut)

    elif mode == 'join':
        gdf_merged = pd.merge(gdf, contain_dic, how='inner', left_on='osmid', right_on='index')
        gdf_merged.drop('index', axis=1, inplace=True)
        gdf_merged.drop('points_in_poly', axis=1, inplace=True)
        gdf = gdf.assign(contained=0)
        indexes = np.empty(gdf_merged.shape[0])
        for index, poly in gdf_merged.iterrows():
            indexes[index] = gdf.loc[gdf['osmid'] == poly['osmid']].index.values
        gdf_merged.index = indexes
        gdf.loc[indexes] = gdf_merged
        gdf.drop(gdf_contained.index, inplace=True)

    elif mode == 'remove':
        gdf = gdf_not_contained
        # drops the contained polygons
    return gdf


def overlaps_polygon(gdf: object) -> object:
    """
    Overlap for polygon layer
    Parameters
    ----------
    gdf

    Returns
    -------

    """
    # Area column initialization
    tmp = gdf.copy()
    if 'polygon_area' not in tmp.columns:
        tmp = polygon_area_gdf(tmp)
    tmp_selected_cols = tmp.loc[:, ['geometry', 'osmid', 'polygon_area', 'landuse']]

    # Check for overlaps
    tmp_overlap = gpd.sjoin(tmp_selected_cols, tmp_selected_cols, how='inner', predicate='overlaps', lsuffix='1', rsuffix='2')
    if not tmp_overlap.empty:
        tmp_overlap = tmp_overlap.loc[tmp_overlap.polygon_area_1 < tmp_overlap.polygon_area_2].copy()  # only keep one
        for index, poly in tmp_overlap.iterrows():
            large_poly_index = np.flatnonzero([gdf.osmid == poly['osmid_2']])
            large_poly = gdf.iloc[large_poly_index]
            large_poly['geometry'] = large_poly['geometry'].difference(poly['geometry'])
            gdf.loc[large_poly.index] = large_poly

    return gdf


def remove_contained_polygons(gdf, gdf2):
    """
    Contains for polygon layer
    Parameters
    ----------
    gdf
    gdf2

    Returns
    -------

    """

    df_contains = gpd.sjoin(gdf, gdf2, how='left', predicate='contains', lsuffix='1', rsuffix='2')
    df_contains = df_contains.loc[df_contains['osmid_1'] != df_contains['osmid_2'], ['osmid_1', 'osmid_2']]
    contain_dic = {'index': [], 'contained': []}

    for id_val, val in enumerate(df_contains['osmid_1'].unique()):
        contain_dic['index'].append(val)
        contain_dic['contained'].append(df_contains.loc[df_contains['osmid_1'] == val, 'osmid_2'].to_list())

    contain_dic = pd.DataFrame(contain_dic)
    contain_dic[point_count] = list(map(len, contain_dic['contained']))
    contained_index = [i for sub in contain_dic.loc[contain_dic.contained.notna(), 'contained'].to_list() for i in sub]
    gdf_not_contained = gdf.loc[~gdf.osmid.isin(contained_index)].copy()

    return gdf_not_contained


def add_information_to_polygon_layers(main_polys, all_polys, points):

    # OUTER POLYGONS (polygons around main_polys = buildings)
    # df_contains = gpd.sjoin(all_polys, main_polys, how='right', predicate='contains', lsuffix='1', rsuffix='2')
    df_contained = gpd.sjoin(main_polys, all_polys, how='left', predicate='within', lsuffix='1', rsuffix='2')
    # see of main_polys (1) are within which all_polys (2)
    df_contained = df_contained.loc[df_contained['osmid_1'] != df_contained['osmid_2'], ['osmid_1', 'osmid_2']]
    contained_by_dic = {}

    land_use_bool = all_polys['landuse'].notna().values
    leisure_bool = all_polys['leisure'].notna().values
    amenity_bool = all_polys['amenity'].notna().values
    office_bool = all_polys['office'].notna().values
    sport_bool = all_polys['sport'].notna().values
    tourism_bool = all_polys['tourism'].notna().values
    shop_bool = all_polys['shop'].notna().values

    main_polys['landuse_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['shop_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['tourism_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['sport_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['office_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['amenity_outer'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['leisure_outer'] = np.empty((len(main_polys), 0)).tolist()

    for id_val, val in enumerate(df_contained['osmid_1'].unique()):
        #if np.isnan(val):
        #    continue
        contained_by_dic[val] = df_contained.loc[df_contained['osmid_1'] == val, 'osmid_2'].to_list()
        # main_poly (1) contained by all_polys (2)
        # main_poly should normally always be contained by 1 larger polygon because of the preprocessing and removing
        # of contained and overlapping polygons. Sometimes not the case if e.g. amenity contour polygon not taken into
        # account.
    print("Adding info from outer polygons to building polygons:")
    for main_id, contained_by_ids in contained_by_dic.items():
        main_index = main_polys.loc[main_polys['osmid'] == main_id].index.values
        for index, contained_by_id in enumerate(contained_by_ids):
            index = np.flatnonzero(all_polys['osmid'] == contained_by_id)[0]

            if land_use_bool[index]:
                main_polys.loc[main_index, 'landuse_outer'].values[0].append(all_polys.iloc[index]['landuse'])

            if amenity_bool[index]:
                main_polys.loc[main_index]['amenity_outer'].values[0].append(all_polys.iloc[index]['amenity'])

            if leisure_bool[index]:
                main_polys.loc[main_index]['leisure_outer'].values[0].append(all_polys.iloc[index]['leisure'])

            if office_bool[index]:
                main_polys.loc[main_index]['office_outer'].values[0].append(all_polys.iloc[index]['office'])

            if sport_bool[index]:
                main_polys.loc[main_index]['sport_outer'].values[0].append(all_polys.iloc[index]['sport'])

            if tourism_bool[index]:
                main_polys.loc[main_index]['tourism_outer'].values[0].append(all_polys.iloc[index]['tourism'])

            if shop_bool[index]:
                main_polys.loc[main_index]['shop_outer'].values[0].append(all_polys.iloc[index]['shop'])

    print("Finished adding info of outer polygons.")
    print("Adding info from inner polygons to building polygons:")
    # INNER polygons (sometimes also amenity polygon with no building value contains info about restaurant, library, cafe, pharmacy, ...
    df_contains = gpd.sjoin(main_polys, all_polys, how='left', predicate='contains', lsuffix='1', rsuffix='2')
    df_contains = df_contains.loc[df_contains['osmid_1'] != df_contains['osmid_2'], ['osmid_1', 'osmid_2']]
    # drop enteries of buildings containing their own
    contain_dic = {}

    amenity_bool = all_polys['amenity'].notna().values
    leisure_bool = all_polys['leisure'].notna().values
    office_bool = all_polys['office'].notna().values
    sport_bool = all_polys['sport'].notna().values
    tourism_bool = all_polys['tourism'].notna().values
    shop_bool = all_polys['shop'].notna().values

    main_polys['shop_inner_poly'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['tourism_inner_poly'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['sport_inner_poly'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['office_inner_poly'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['amenity_inner_poly'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['leisure_inner_poly'] = np.empty((len(main_polys), 0)).tolist()

    for id_val, val in enumerate(df_contains['osmid_1'].unique()):
        #if np.isnan(val):
        #    continue
        contain_dic[val] = df_contains.loc[df_contains['osmid_1'] == val, 'osmid_2'].to_list()
        # main_poly (1) contains all_polys (2)

    for large_id, contained_ids in contain_dic.items(): # large_id is of main_poly
        large_index = main_polys.loc[main_polys['osmid'] == large_id].index.values
        # large_index = all_polys.loc[all_polys['osmid'] == large_id].index.values # main polys also part of all_polys
        for index, contained_id in enumerate(contained_ids):
            index = np.flatnonzero(all_polys['osmid'] == contained_id)[0]

            if amenity_bool[index]:
                main_polys.loc[large_index]['amenity_inner_poly'].values[0].append(all_polys.iloc[index]['amenity'])

            if leisure_bool[index]:
                main_polys.loc[large_index]['leisure_inner_poly'].values[0].append(all_polys.iloc[index]['leisure'])

            if office_bool[index]:
                main_polys.loc[large_index]['office_inner_poly'].values[0].append(all_polys.iloc[index]['office'])

            if sport_bool[index]:
                main_polys.loc[large_index]['sport_inner_poly'].values[0].append(all_polys.iloc[index]['sport'])

            if tourism_bool[index]:
                main_polys.loc[large_index]['tourism_inner_poly'].values[0].append(all_polys.iloc[index]['tourism'])

            if shop_bool[index]:
                main_polys.loc[large_index]['shop_inner_poly'].values[0].append(all_polys.iloc[index]['shop'])
    print("Finished adding info of inner polygons.")

    # INNER POINTS
    df_contains2 = gpd.sjoin(main_polys, points, how='right', predicate='contains', lsuffix='1', rsuffix='2')
    # one building can contain multiple points
    contain_dic = {}

    building_bool = points['building'].notna().values
    amenity_bool = points['amenity'].notna().values
    leisure_bool = points['leisure'].notna().values
    office_bool = points['office'].notna().values
    sport_bool = points['sport'].notna().values
    tourism_bool = points['tourism'].notna().values
    shop_bool = points['shop'].notna().values

    main_polys['building_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['shop_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['tourism_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['sport_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['office_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['amenity_inner_point'] = np.empty((len(main_polys), 0)).tolist()
    main_polys['leisure_inner_point'] = np.empty((len(main_polys), 0)).tolist()

    for id_val, val in enumerate(df_contains2['osmid_1'].unique()):
        if np.isnan(val):
            continue
        contain_dic[val] = df_contains2.loc[df_contains2['osmid_1'] == val, 'osmid_2'].to_list()

    print("Adding info from points inside building polygons to building polygons:")
    for large_id, contained_ids in contain_dic.items():
        large_index = all_polys.loc[all_polys['osmid'] == large_id].index.values
        for index, contained_id in enumerate(contained_ids):
            index = np.flatnonzero(points['osmid'] == contained_id)[0]

            if building_bool[index]:
                main_polys.loc[large_index]['building_inner_point'].values[0].append(points.iloc[index]['building'])

            if amenity_bool[index]:
                main_polys.loc[large_index]['amenity_inner_point'].values[0].append(points.iloc[index]['amenity'])

            if leisure_bool[index]:
                main_polys.loc[large_index]['leisure_inner_point'].values[0].append(points.iloc[index]['leisure'])

            if office_bool[index]:
                main_polys.loc[large_index]['office_inner_point'].values[0].append(points.iloc[index]['office'])

            if sport_bool[index]:
                main_polys.loc[large_index]['sport_inner_point'].values[0].append(points.iloc[index]['sport'])

            if tourism_bool[index]:
                main_polys.loc[large_index]['tourism_inner_point'].values[0].append(points.iloc[index]['tourism'])

            if shop_bool[index]:
                main_polys.loc[large_index]['shop_inner_point'].values[0].append(points.iloc[index]['shop'])
    print("Finished adding info of points inside.")
    return main_polys
