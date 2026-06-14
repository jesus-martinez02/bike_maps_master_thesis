import psycopg2
import os
from dotenv import load_dotenv
from modules import category_processing, network_preparation, network_processing, network_reduction, final_table_creation, poidpy_trip_generation, trip_distribution
import time
from multiprocessing import Pool, cpu_count
from sqlalchemy import create_engine

import pandas as pd
import geopandas as gpd

load_dotenv()

DB_CONFIG = {
    'host': 'localhost',
    'dbname': os.getenv("POSTGRES_DB"),
    'user': os.getenv("POSTGRES_USER"),
    'password': os.getenv("POSTGRES_PASSWORD"),
    'port': 5432
}

city_list = ["Berlin"]
NUM_ODS = 100 *1000


for index,city in enumerate(city_list):
    
    conn = psycopg2.connect(**DB_CONFIG)

    category_processing.create_cycling_categories(conn)
    network_preparation.pgrouting_start(conn)

    network_preparation.prepare_network(conn, city, out_edge_table = "temp_raw_edges")
    network_preparation.intersect_network(conn,in_edge_table = "temp_raw_edges", out_edge_table = "temp_edges")
    network_processing.network_creation(conn, edge_table = "temp_edges", vertex_table="temp_vertices")
    network_processing.keep_main_component(conn, in_edge_table = "temp_edges", vertex_table = "temp_vertices", component_table = "temp_comp_table", out_edge_table = "temp_filtered_edges")
    network_processing.remove_dead_ends(conn,edge_table = "temp_filtered_edges", vertex_table = "temp_vertices", num_it = 5)
    network_processing.simplify_network(conn,in_edge_table = "temp_filtered_edges", out_edge_table = "temp_filtered_edges", vertex_table="temp_vertices")



    network_reduction.create_grid_table(conn, city_name = city, 
                                        grid_size = 2000, grid_table_name = "temp_grid", vertex_table = "temp_vertices")

    
    conn.commit()
    conn.close()
    
    # # # start_time = time.time()

    # engine = create_engine(f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    #                 f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    # zones_gdf = poidpy_trip_generation.poidpy_trip_generation(engine, grid_table = "temp_grid", pois_table_name = "pois_" + city.lower())
    
    # zones_gdf.to_csv(city + "_zones.csv", index=False)

    
    engine = create_engine(f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
                    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    
    df = pd.read_csv('/home/jmartinez/Documents/bike_project/Berlin_zones.csv')

    from shapely import wkt
    df['geometry'] = df['geometry'].apply(wkt.loads)

    zones_gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
    
    ## Baseline

    trip_distribution.sample_od_pairs(engine, zones_gdf, grid_table = "temp_grid", vertex_table = "temp_vertices", 
    number_ods= NUM_ODS,pois_table_name = "pois_" + city.lower(), selected_ods_table = "temp_selected_ods1",
     use_zones = False, use_distances = False, random_destination = True)


    conn = psycopg2.connect(**DB_CONFIG)

    network_reduction.calculate_edge_percentiles(conn, starting_seed = 0.4, edge_table = "temp_filtered_edges", selected_ods_table = "temp_selected_ods1",num_ods = NUM_ODS,
                                                 include_different_sensitivity = False,out_table = "results_berlin_base_betweenness")


    conn.commit()
    conn.close()


    ## Adding POIs
    trip_distribution.sample_od_pairs(engine, zones_gdf, grid_table = "temp_grid", vertex_table = "temp_vertices", 
    number_ods= NUM_ODS,pois_table_name = "pois_" + city.lower(), selected_ods_table = "temp_selected_ods1",
     use_zones = True, use_distances = False, random_destination = True)


    conn = psycopg2.connect(**DB_CONFIG)


    network_reduction.calculate_edge_percentiles(conn, starting_seed = 0.4, edge_table = "temp_filtered_edges", selected_ods_table = "temp_selected_ods1",num_ods = NUM_ODS,
                                                 include_different_sensitivity = False,out_table = "results_berlin_base_pois")


    conn.commit()
    conn.close()
 
    ## Adding non-random destination, both way ODs

    trip_distribution.sample_od_pairs(engine, zones_gdf, grid_table = "temp_grid", vertex_table = "temp_vertices", 
    number_ods= NUM_ODS,pois_table_name = "pois_" + city.lower(), selected_ods_table = "temp_selected_ods1",
     use_zones = True, use_distances = False, random_destination = False)


    conn = psycopg2.connect(**DB_CONFIG)


    network_reduction.calculate_edge_percentiles(conn, starting_seed = 0.4, edge_table = "temp_filtered_edges", selected_ods_table = "temp_selected_ods1",num_ods = NUM_ODS * 2,
                                                 include_different_sensitivity = False,out_table = "results_berlin_base_non_random_des")


    conn.commit()
    conn.close()
         
    ## Including decay by distance
    trip_distribution.sample_od_pairs(engine, zones_gdf, grid_table = "temp_grid", vertex_table = "temp_vertices", 
    number_ods= NUM_ODS * 2,pois_table_name = "pois_" + city.lower(), selected_ods_table = "temp_selected_ods1",
     use_zones = True, use_distances = True, random_destination = False)


    conn = psycopg2.connect(**DB_CONFIG)


    network_reduction.calculate_edge_percentiles(conn, starting_seed = 0.4, edge_table = "temp_filtered_edges", selected_ods_table = "temp_selected_ods1",num_ods = NUM_ODS * 2,
                                                 include_different_sensitivity = False,out_table = "results_berlin_base_dist")


    conn.commit()
    conn.close()


    ## Including different parameter for sensitivity
    trip_distribution.sample_od_pairs(engine, zones_gdf, grid_table = "temp_grid", vertex_table = "temp_vertices", 
    number_ods= NUM_ODS * 2,pois_table_name = "pois_" + city.lower(), selected_ods_table = "temp_selected_ods1",
     use_zones = True, use_distances = True, random_destination = False)


    conn = psycopg2.connect(**DB_CONFIG)


    network_reduction.calculate_edge_percentiles(conn, starting_seed = 0.4, edge_table = "temp_filtered_edges", selected_ods_table = "temp_selected_ods1",num_ods = NUM_ODS * 2,
                                                 include_different_sensitivity = True,out_table = "results_berlin_final")


    conn.commit()
    conn.close()


    # print("--- %s seconds ---" % (time.time() - start_time))

# conn.commit()
# conn.close()
