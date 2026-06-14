"""
Functions required to extract data from OpenStreetMap.
"""
# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers, Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

# Internal modules
from .osm_classification import tags_default, attribute_columns

# Other packages
import osmnx as ox
import numpy as np
import time

from shapely.geometry import box,Polygon,MultiPolygon,GeometryCollection
from shapely.ops import unary_union
import geopandas as gpd
import pandas as pd


def extract_polygons(geom):
    if isinstance(geom, Polygon):
        return geom
    elif isinstance(geom, MultiPolygon):
        return geom
    elif isinstance(geom, GeometryCollection):
        polys = []
        for g in geom.geoms:
            
            if isinstance(g, Polygon):
                polys.append(g)
            elif isinstance(g, MultiPolygon):
                polys.extend(g.geoms)
        
        if not polys:
            return None
        
        merged = unary_union(polys)
        return merged    
    

    raise Exception("Geomtry type not valid")

## Added function to subdivide polygon
def subdivide_polygon(polygon, n_tiles):
    minx, miny, maxx, maxy = polygon.bounds
    
    print(polygon.bounds)
    n_cols = int(np.ceil(np.sqrt(n_tiles)))
    n_rows = int(np.ceil(n_tiles / n_cols))
    
    x_splits = np.linspace(minx, maxx, n_cols + 1)
    y_splits = np.linspace(miny, maxy, n_rows + 1)
    
    tiles = []
    for i in range(n_cols):
        for j in range(n_rows):
            tile = box(x_splits[i], y_splits[j],
                       x_splits[i+1], y_splits[j+1])
            

            clipped = polygon.intersection(tile)
                        
            if not clipped.is_empty:
                tiles.append(extract_polygons(clipped))

    print(len(tiles))
    # return tiles[:n_tiles]
    return tiles

def all_geometries_from_area(extent, tags=None, select_columns=True, timeout=None):
    data_geometries_full = []
    tic = time.time()
    print('Start downloading geometries…')
    if tags is None:
        tags = tags_default
    ox.config(log_file=True)
    if timeout is not None:
        ox.config(timeout=timeout)

    num_tiles = 10
    tiles = subdivide_polygon(extent, num_tiles)

    print(extent)
    data_geometries_list = []
    for i, tile in enumerate(tiles):
        print(f"Fetching tile {i+1}/{len(tiles)}")
        print(tile)
        data_geometries_tile = ox.geometries_from_polygon(tile, tags)
        data_geometries_list.append(data_geometries_tile)
        print("Geometries fetched",len(data_geometries_tile))

    # data_geometries = ox.geometries_from_polygon(extent, tags) #deprecated and will be removed in the future
    #data_geometries = ox.features_from_polygon(extent, tags) #osmnx version 1.6.0
    data_geometries = gpd.GeoDataFrame(pd.concat(data_geometries_list))

    print(len(data_geometries))
    print('raw geometries downloaded from OSM')
    # raw geodataframe with all geometries
    if select_columns:
        if isinstance(select_columns, list):
            assert set(select_columns).issubset(set(data_geometries.columns))
            data_columns = select_columns
        else:
            base_columns = ['osmid', 'geometry']
            base_columns.extend(list(tags.keys()))
            data_columns = base_columns
            print(data_columns)
        if not set(data_columns).issubset(set(data_geometries.columns)):
            for k in data_columns:
                try:
                    data_geometries[k]
                except KeyError:
                    data_geometries.loc[:, k] = np.nan
        data_geometries = data_geometries[data_columns]
    data_geometries = data_geometries.reset_index(inplace=False)
    data_geometries.rename(columns={'index': '_id'}, inplace=True)
    toc = time.time()
    print(f'Downloading geometries done, took {toc - tic} sec')
    print("Length now: ", len(data_geometries))
    return data_geometries


def get_all_tag_values(gdf, data_columns=None):
    if data_columns is None:
        data_columns = attribute_columns
    tags = []
    for k in data_columns:
        tags.extend(list(gdf[k].value_counts().keys()))
    len(tags)
    return set(tags)
