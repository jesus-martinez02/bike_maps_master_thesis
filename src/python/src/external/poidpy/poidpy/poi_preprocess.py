"""
Preprocessing module to clean and enhance data layers of OSM.
"""
# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Jeroen Verstraete, Lotte Notelaers
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

# Import packages
from .geometry_utilities import _assign_priority, contains_polygon, overlaps_polygon, polygon_area_gdf, split_by_geometry, remove_contained_polygons, add_information_to_polygon_layers
from .osm_classification import default_ignore_tags, building_threshold_area

import pandas as pd
import geopandas as gpd
import numpy as np


def poi_preprocess(poi: gpd.GeoDataFrame):
    print("Preprocessing:")
    print("Assign attribute priority.")
    poi = _assign_priority(poi)
    print("Split by geometry (points and polygons).")
    points, polys = split_by_geometry(poi, area_pol=True)
    print("Removing inconsistencies:")
    polys, contour_polys, no_building_no_contour_polys = _remove_inconsistencies(polys)
    
    return points, polys, contour_polys, no_building_no_contour_polys


def construct_building_polygons(polys: object, points: object) -> object:
    # can also be put in separate function
    print("Constructing building polygons dataframe:")
    building_poly = _construct_building_polygons(polys, points)
    return building_poly


def _remove_inconsistencies(polys: gpd.GeoDataFrame):
    """
    Check consistency across different attributes, overlapping objects not allowed
    Done for main attributes = landuse, building; therefore these attributes should always be present in the
    attribute_cols parameter

    Parameters
    ----------
    polys

    Returns
    -------

    """
    essential = ['building', 'landuse', 'amenity', 'leisure', 'tourism']
    try:
        assert set(essential).issubset(set(polys.columns))
    except AssertionError:
        print("Essential columns: 'building' and 'landuse', not present in data set, check taglist when downloading "
              "data from OSM")

    # Pre-processing
    poi = polys.copy()

    # removes polygons with no values
    poi.drop(np.flatnonzero([poi['priority'] == 'other']), inplace=True)
    poi.dropna(axis=0, how='all', inplace=True)
    poi = polygon_area_gdf(poi)

    # LAND USE and other contour polygonen
    poi_no_building = poi[poi["building"].isna()]
    landuse_polygons = poi_no_building[(poi_no_building['landuse'].notna()) & (~poi_no_building['landuse'].isin(default_ignore_tags["landuse"]))]
    contour_amenity_polygons = poi_no_building[(poi_no_building['amenity'].isin(["college", "kindergarten", "university", "school",
                                                                                 "conference_centre", "hospital", "monastery", "prison",
                                                                                 "social_facility", "verkeerspark", "grave_yard", "market_place", "recycling"])) & (
                                                   ~poi_no_building['osmid'].isin(landuse_polygons['osmid'].to_list()))]
    # amenity contour polygons that are not yet taken into account in the landuse layer
    contour_polygons = pd.concat([landuse_polygons, contour_amenity_polygons], axis=0)

    contour_leisure_polygons = poi_no_building[
        (poi_no_building['leisure'].isin(["park", "stadium", "sports_centre", "nature_reserve", "garden"])) & (~poi_no_building['osmid'].isin(contour_polygons['osmid'].to_list()))]

    contour_polygons = pd.concat([contour_polygons, contour_leisure_polygons], axis=0)

    contour_tourism_polygons = poi_no_building[
        (poi_no_building["tourism"].isin(["camp_site", "caravan_site", "theme_park"])) & (~poi_no_building['osmid'].isin(contour_polygons['osmid'].to_list()))]
    contour_polygons = pd.concat([contour_polygons, contour_tourism_polygons], axis=0)

    poi_no_building.drop(contour_polygons.index, inplace=True)
    poi_no_building_no_contour = poi_no_building.copy(deep=True)
    print("Splitting contained landuse/contour polygons:")
    contour_polygons = contains_polygon(contour_polygons, mode='difference')  # No mixed land use/contour types of overlapping polygons
    print("Contained land-use/contour polygons are split.")
    print("Splitting overlapping landuse/contour polygons:")
    contour_polygons = overlaps_polygon(contour_polygons)
    print("Overlapping land-use/contour polygons are split.")
    poi_no_building = pd.concat([poi_no_building, contour_polygons], axis=0)

    # BUILDING
    # All polygons with a value for building-tag even if they have other values for other attributes
    building_polygons = poi.loc[poi['building'].notna()]
    building_polygons = building_polygons.loc[building_polygons.type.isin(['Polygon', 'MultiPolygon'])]
    poi.drop(building_polygons.index, inplace=True)
    print("Removing contained buildings:")
    building_polygons = contains_polygon(building_polygons, mode='remove')
    print("Contained building polygons are removed.")
    print("(Removing or) splitting overlapping building polygons:")
    building_polygons = overlaps_polygon(building_polygons)
    print("Overlapping building polygons are (removed or) split (based on overlap_ratio).")

    poi = pd.concat([poi_no_building, building_polygons], axis=0)
    return poi, contour_polygons, poi_no_building_no_contour


def _construct_building_polygons(polys, points):
    print("Selecting building polygons.")
    # building polygons are polygons with tag of building filled in
    building_polygons = polys.loc[polys['building'].notna()].copy()
    # remove buildings in leisure polygon

    print(f"Retaining building polygons with area larger than building_threshold_area of {building_threshold_area} m^2.")
    # remove small polygons
    s = (building_polygons['polygon_area'] < building_threshold_area)
    building_polygons.drop(s.index[s], inplace=True)

    print("Adding information to building polygons of surrounding landuse/contour polygons, and contained points and polygons.")
    # add information of other polygons and points
    building_polygons = add_information_to_polygon_layers(building_polygons, polys, points)
    return building_polygons
