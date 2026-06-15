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


def all_geometries_from_area(extent, tags=None, select_columns=True, timeout=None):
    tic = time.time()
    print('Start downloading geometries…')
    if tags is None:
        tags = tags_default
    ox.config(log_file=True)
    if timeout is not None:
        ox.config(timeout=timeout)
    data_geometries = ox.geometries_from_polygon(extent, tags) #deprecated and will be removed in the future
    # data_geometries = ox.features_from_polygon(extent, tags) #osmnx version 1.6.0
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
    return data_geometries


def get_all_tag_values(gdf, data_columns=None):
    if data_columns is None:
        data_columns = attribute_columns
    tags = []
    for k in data_columns:
        tags.extend(list(gdf[k].value_counts().keys()))
    len(tags)
    return set(tags)
