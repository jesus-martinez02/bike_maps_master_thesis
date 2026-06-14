import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import weibull_min

from sqlalchemy import text

def find_grid_vertex_map(db_engine, grid_table, vertex_table):
    """
    Calculates map between grid cells and contained vertices
    """
    query_vertices_grid = f"""SELECT g.id AS grid_id,
            v.id AS vertex_id,
            v.geom as geom
            FROM {grid_table} g
            JOIN {vertex_table} v
                        ON ST_Intersects(
                            g.geom,
                            v.geom)"""
    vertices_gdf = gpd.GeoDataFrame.from_postgis(query_vertices_grid, db_engine).rename(columns={"geom": "geometry"})

    grid_vertex_map = (
        vertices_gdf
        .groupby("grid_id")["vertex_id"]
        .apply(list)
        .to_dict()
    )

    return grid_vertex_map

def find_closest_vertices_to_poi(db_engine,pois_table_name,vertex_table):
    """
    Returns closes vertex to a POI
    """
    

    index_sql = f""" CREATE INDEX IF NOT EXISTS {pois_table_name}_geom_idx
                ON {pois_table_name}
                USING GIST (geometry);
                """
    alter_sql = f"""ALTER TABLE {pois_table_name} ADD COLUMN IF NOT EXISTS closest_vertex BIGINT;"""
    update_sql = f"""
    UPDATE {pois_table_name} p
    SET closest_vertex = (
        SELECT v.id
        FROM {vertex_table} v
        ORDER BY p.geometry <-> v.geom
        LIMIT 1
    );

    """

    with db_engine.connect() as conn:
        conn.execute(text(index_sql))
        conn.execute(text(alter_sql))
        conn.execute(text(update_sql))
        conn.commit()



def compute_zone_distances(zones_gdf):
    """
    Computes zonal distance
    """
    centroids = zones_gdf.geometry.centroid  

    geometries = centroids.apply(lambda x: (x.x, x.y)).tolist()
    distances = pdist(geometries)
    dist_matrix = squareform(distances)

    np.fill_diagonal(dist_matrix,zones_gdf["interzone_distance"])
    dist_df = pd.DataFrame(dist_matrix, index=zones_gdf.index, columns=zones_gdf.index)
    
    return dist_df


def Double_Cal(production_mat, attraction_mat,dist_mat,eps=0.1):
    """
    Algorithm to find balancing factors in a Doubly Constrained Gravity Model. Based on Chapter on Trip Distribution in book by Ortuzar.

    ### Parameters:
    - production_mat: Zonal matrix containing estimated production
    - attraction_mat: Zonal matrix containing estimated attraction
    - dist_mat: Matrix with distance between zones
    - eps: Parameter for convergence of the algorithm

    ### Returns:

    - T_ij matrix containing number of trips between origin zone i and destination zone j

    """
    # Avoid division by 0
    production_mat += 0.1
    attraction_mat += 0.1

    # Scale production to match attraction
    prod_sum = production_mat.sum()
    attr_sum = attraction_mat.sum()
    production_mat = (attr_sum / prod_sum) * production_mat

    cost = np.array(np.exp(-0.1 * dist_mat))

    A_i = np.ones((production_mat.shape[0], 1))  
    B_j = np.ones((1, attraction_mat.shape[1]))  

    iteration = 0
    while True:
        denominator_A = np.sum(B_j * attraction_mat * cost, axis=1, keepdims=True)
        A_i = 1.0 / (denominator_A + 1e-10)  
        denominator_B = np.sum(A_i * production_mat * cost, axis=0, keepdims=True)
        B_j = 1.0 / (denominator_B + 1e-10)
        
        T_i_j = A_i * production_mat * B_j * attraction_mat * cost  
        
        row_sums = np.sum(T_i_j, axis=1)  
        col_sums = np.sum(T_i_j, axis=0)  
        
        diff_or = np.max(np.abs(row_sums.flatten() - production_mat.flatten()))
        diff_des = np.max(np.abs(col_sums.flatten() - attraction_mat.flatten()))
        
        iteration += 1
        # print(f"Iter {iteration}: diff_or={diff_or:.2e}, diff_des={diff_des:.2e}")
        
        if (diff_or < eps) and (diff_des < eps):
            print("Doubly Constrained Gravity Model converged after " + str(iteration) + " iterations")
            break
        
        if iteration > 1000:
            print("Max iterations reached")
            break

    return T_i_j


def sample_od_pairs(db_engine, zones_gdf, grid_table, vertex_table, number_ods, selected_ods_table, pois_table_name, include_od_prob = True, use_zones = True, use_distances = True, random_destination = False):
    """
    Function to sample OD vertex pairs, based on different customizable criteria.

    ### Parameters:
    - db_engine: SQLAlchemy engine
    - zones_gdf: GeoPandas DataFrame containing the zones and its estimated production and attraction
    - grid_table: Input grid table where each grid cell represents a zone
    - vertex_table: Input vertex tabke
    - number_ods: Number of ODs to be generated
    - selected_ods_table: Output table where generated OD vertex pairs will be stored.
    - pois_table_name: Output table where information regarding generated Podipy POIs will be stored
    - include_od_prob: Whether to include that OD zones are sampled according to a probability based on POIs. If false, then all zones would have same probability to be chosen.
    - use_zones: Whether to use a zonal division or not. If false, then it samples OD vertices totally at random, which would then later mean calculating betweenness centrality.
    - use_distances: Whether to use modal split based on Acceptance/Rejection of trips based on a Weibull distance distribution or not.
    - random_destination: Whether to consider that the destination vertex is chosen at random with euqal probabiliyy (True), or it is the closest vertex to the relevant POI
    """

    ### Order zones

    zones_gdf = zones_gdf.sort_values("id", ascending=True)
    zones_gdf = zones_gdf.reset_index(drop=True)
    print(zones_gdf)
    if use_zones:
        zones_gdf = zones_gdf.to_crs(3857)
        zones_gdf["interzone_distance"] = np.sqrt(zones_gdf['geometry'].area)/4

        dist_df = compute_zone_distances(zones_gdf)
        dist_mat = np.array(dist_df) / 1000
        production_mat = np.array(zones_gdf['prod_pred'].values, dtype=float).reshape(-1, 1) 
        attraction_mat = np.array(zones_gdf['attr_pred'].values, dtype=float).reshape(1, -1)
        T_i_j = Double_Cal(production_mat, attraction_mat,dist_mat)
        

        if include_od_prob is False:
            T_i_j = np.ones_like(T_i_j)

        P_i_j = T_i_j / np.sum(T_i_j)
        od_prob_data = [((i, j), val) for (i, j), val in np.ndenumerate(P_i_j)]

        od_prob_df = pd.DataFrame(od_prob_data, columns=["OD", "probability"])
        selected_ods = np.random.choice(od_prob_df["OD"],size = number_ods, p = od_prob_df["probability"])
        od_pairs_df = pd.DataFrame(list(selected_ods), columns=["origin_zone","destination_zone"])


        grid_vertex_map = find_grid_vertex_map(db_engine, grid_table, vertex_table)

        od_pairs_df["origin_vertex"] = [
            np.random.choice(grid_vertex_map.get(x, [-1])) for x in od_pairs_df["origin_zone"].values
        ]

        find_closest_vertices_to_poi(db_engine, pois_table_name, vertex_table)
        print("pased here 0")

        def sample_points(zone):
            subset = vertices_prob_df[vertices_prob_df['zone_id'] == zone]
            if not subset.empty:
                return np.random.choice(subset['closest_vertex'], p=subset['prob_poi'])
            else:
                # 
                return -1  
            #return np.random.choice(subset['closest_vertex'], p=subset['prob_poi'])


        variables = ['Leisure', 'Shops', 'Services', 'Catering_industry', 'Tourism', 'Leisure_area']
        coeff = [0.0526, 0.2844, 0.0273, 0.8890, 0.4160, 0.0156]

        classified_pois_gdf = gpd.GeoDataFrame.from_postgis(pois_table_name,db_engine, geom_col="geometry", crs=4326)
        print("pased here 1")
        classified_pois_gdf['attr_pred'] = + (classified_pois_gdf[variables] * coeff).sum(axis=1)
        possible_pois_gdf = classified_pois_gdf[(classified_pois_gdf['attr_pred'] > 0) & (~classified_pois_gdf['closest_vertex'].isnull())]
        pois_zones_merged_gdf = gpd.sjoin(possible_pois_gdf, zones_gdf[['id', 'geometry']].to_crs(4326).rename(columns={'id': 'zone_id'}), predicate='within', how='left')

        zone_totals = pois_zones_merged_gdf.groupby('zone_id')['attr_pred'].sum().reset_index()
        zone_totals = zone_totals.rename(columns={'attr_pred': 'total_attr'})
        print("pased here 2")

        pois_zones_merged_gdf = pois_zones_merged_gdf.merge(zone_totals, on='zone_id')

        print("passed here 3")
        pois_zones_merged_gdf['prob_poi'] = pois_zones_merged_gdf['attr_pred'] / pois_zones_merged_gdf['total_attr']
        vertices_prob_df = pois_zones_merged_gdf[["zone_id","closest_vertex","prob_poi"]]

        pois_zones_merged_gdf.to_postgis("test_pois_classified_hamburg", db_engine, if_exists="replace")

        od_pairs_df['destination_vertex'] = od_pairs_df['destination_zone'].apply(sample_points)

        print("pased here 4")
        


        if random_destination:
            od_pairs_df["destination_vertex"] = [
                np.random.choice(grid_vertex_map.get(x, [-1])) for x in od_pairs_df["destination_zone"].values
            ]

    else:
        od_pairs_df = pd.DataFrame(index=range(number_ods),columns=["origin_vertex","destination_vertex"])
        vertex_df = gpd.GeoDataFrame.from_postgis(f"SELECT id,geom FROM {vertex_table}",db_engine)
        od_pairs_df["origin_vertex"] = np.random.choice(vertex_df["id"].values,size=number_ods)
        od_pairs_df["destination_vertex"] = np.random.choice(vertex_df["id"].values,size=number_ods)


    
    # Sanity check in case there is an OD pair not existing
    valid_od_pairs_df = (od_pairs_df[(od_pairs_df["origin_vertex"] != -1) & (od_pairs_df["destination_vertex"] != -1)])


    if use_distances:
        valid_od_pairs_df["distance"] = valid_od_pairs_df.apply(
            lambda row: dist_df.loc[row["origin_zone"], row["destination_zone"]],
            axis=1
        )
        valid_od_pairs_df["uniform_value"] = np.random.uniform(size=len(valid_od_pairs_df))

        k = 1.5        
        lambda_ = 7    


        valid_od_pairs_df["weibull_cdf"] =  1- weibull_min.cdf(valid_od_pairs_df["distance"]/1000, c=k, scale=lambda_)

        valid_od_pairs_df = valid_od_pairs_df[ valid_od_pairs_df["weibull_cdf"] > valid_od_pairs_df["uniform_value"]].copy()


    valid_od_pairs_df_copy = valid_od_pairs_df.rename(columns={"origin_zone": "destination_zone","origin_vertex": "destination_vertex","destination_zone": "origin_zone","destination_vertex": "origin_vertex"})
    
    valid_od_pairs_df_final = pd.concat([valid_od_pairs_df, valid_od_pairs_df_copy], axis=0).reset_index(drop=True)

    valid_od_pairs_df_final["id"] = valid_od_pairs_df_final.index
    valid_od_pairs_df_final.to_sql(name=selected_ods_table, con = db_engine, schema="public", if_exists="replace")