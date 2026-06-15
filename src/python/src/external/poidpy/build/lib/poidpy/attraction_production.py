import numpy as np
import pandas as pd

# This file is part of the Demand Generation Tool, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers, Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be


def attraction_production_from_OD(od_matrix, zones_gdf, zones_id_col='ZONENUMMER', prod_col='production', attr_col='attraction'):
    """

    Parameters
    ----------
    zones_id_col: name of column that represents the indexes as given in od_matrix
    zones_gdf: geopandas dataframe of zoning
    od_matrix: pandas dataframe with index origin ids and column labels the destination ids
    prod_col: name of column in which the total production of each zone will be stored
    attr_col: name of column in which the total attraction of each zone will be stored

    Returns
    -------
    the production and attraction column will be added to given zones data frame

    """
    zones_gdf.loc[:, prod_col] = 0
    zones_gdf.loc[:, attr_col] = 0
    for i, j in zones_gdf.iterrows():
        # TODO find source of excepts and handle generic
        try:
            zones_gdf.loc[i, prod_col] = od_matrix.loc[od_matrix.index == j[zones_id_col], :].sum(axis=1).values[0]
        except:
            print(f'No trip value (production) found for ZoneID {j[zones_id_col]}. NaN value assigned.')
            zones_gdf.loc[i, prod_col] = np.NaN
        try:
            zones_gdf.loc[i, attr_col] = od_matrix[j[zones_id_col]].sum(axis=0)
        except:
            print(f'No trip value (attraction) found for ZoneID {j[zones_id_col]}. NaN value assigned.')
            zones_gdf.loc[i, attr_col] = np.NaN

    return zones_gdf

def attraction_production_from_file(file,  zones_gdf, zones_id_col='ZONENUMMER', prod_col='production', attr_col='attraction'):
    """

        Parameters
        ----------
        zones_id_col: name of column that represents the indexes as given in PA file
        zones_gdf: geopandas dataframe of zoning
        file: file path storing PA totals
        prod_col: name of column in which the total production of each zone is stored
        attr_col: name of column in which the total attraction of each zone is stored

        Returns
        -------
        the production and attraction column will be added to given zones data frame

        """

    PA = pd.read_csv(file)

    try:
        assert zones_id_col in zones_gdf and zones_id_col in PA
    except AssertionError:
        print(f"{zones_id_col} not in the zoning dataframe or not in the Production Attraction data.")

    PA[zones_id_col] = PA[zones_id_col].astype(zones_gdf[zones_id_col].dtype)
    zones_gdf = zones_gdf.merge(PA[[zones_id_col, prod_col, attr_col]], on=zones_id_col, how="left")

    if prod_col != "production" or attr_col != "attraction":
        zones_gdf = zones_gdf.rename(columns={prod_col: "production", attr_col: "attraction"})

    return zones_gdf