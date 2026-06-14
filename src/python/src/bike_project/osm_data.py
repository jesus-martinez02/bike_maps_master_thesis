"""
Script for fetching bicycle network data from OSM. It is better if it is run with a single city each time, as to avoid reaching number of requests from Overpass API
"""


import requests
import json
import osm2geojson

import geopandas as gpd
from shapely.ops import transform
import pandas as pd

import time

import geopandas as gpd
import os


from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def osm_request(overpass_query):
    """
    Sends a request to the Overpass API.

    ### Parameters:
    - overpass_query: Query to be send to Overpass API

    ### Returns: 
    - Response from Overpass API

    """
    overpass_url = 'https://overpass-api.de/api/interpreter'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'text/plain',
        'User-Agent': 'Libebikemaps',
        'Referer': 'http://www.librebikemaps.com/'       
        }    
    
    response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers)
    num_attempts = 1

    print("Atempt: " + str(num_attempts) + " Status code: " + str(response.status_code))

    while response.status_code != 200 and num_attempts < 10:


        response = requests.get(overpass_url, params={'data': overpass_query})
        num_attempts += 1

        print("Atempt: " + str(num_attempts) + " Stauts code: " + str(response.status_code))

        time.sleep(60)


    
    if response.status_code != 200:
        raise Exception("FAILURE: Exceeded number of attempts to fetch the data")

    return response

def fetch_osm_city(city_radius,lat,lon):
    """
    Fetch possible bicycle infrastructure for one city.

    ### Parameters:
    - city_radius: Radius around which the OSM data will be fetched
    - lat: Latitude of the city center of the fetched city.
    - lon: Longitude of the city center of the fetched city.

    ### Returns: 
    - GeoPandasDataFrame with fetched infrastrcuture and OSM tags expanded.

    """
    overpass_query = fr"""[out:json][timeout:60];
    (
    way(around:{city_radius}, {str(lat)}, {str(lon)})["highway"];
    way(around:{city_radius}, {str(lat)}, {str(lon)})["bicycle"!="no"]["bicycle"];
    way(around:{city_radius}, {str(lat)}, {str(lon)})["cycleway:left"];
    way(around:{city_radius}, {str(lat)}, {str(lon)})["cycleway:right"];
    way(around:{city_radius}, {str(lat)}, {str(lon)})["cycleway:both"];
    way(around:{city_radius}, {str(lat)}, {str(lon)})["cycleway"];    
    );
    out geom;
    """

    response = osm_request(overpass_query)


    decoded_data = json.loads(response.text)

    geojson = osm2geojson.json2geojson(decoded_data)
    gdf = gpd.GeoDataFrame.from_features(geojson,crs="EPSG:4326")

    expaned_tags_df = pd.DataFrame(gdf["tags"].to_list()).rename(columns={"type": "type_tag"})

    tag_list =  ["highway","cycleway", "cycleway:left","cycleway:right","cycleway:both","bicycle","surface","foot","segregated","width",
                 "vehicle","oneway","motor_vehicle","name" , "access", "layer", "bridge"]
    if(any("route" == col for col in expaned_tags_df.columns)):
        tag_list.append("route")

    if(any("living_street" == col for col in expaned_tags_df.columns)):
        tag_list.append("living_street")

    if(any("bicycle_road" == col for col in expaned_tags_df.columns)):
        tag_list.append("bicycle_road")

    if(any("cyclestreet" == col for col in expaned_tags_df.columns)):
        tag_list.append("cyclestreet")

    if(any("oneway:bicycle" == col for col in expaned_tags_df.columns)):
        tag_list.append("oneway:bicycle")


    filtered_tags_df = expaned_tags_df[tag_list]
    expanded_gdf = gpd.GeoDataFrame(pd.concat([gdf.drop(["tags"], axis=1), filtered_tags_df],axis = 1))

    print(expanded_gdf.columns.to_list())
    return expanded_gdf


# def fetch_osm_multiple_cities(city_list, output_path=""):    
#     all_cities_gdf_list = []

#     for (city,country, admin_level) in city_list:
#         print("Fetching " + city)
#         city_gdf = fetch_osm_city(city,country, admin_level)
#         city_gdf["fetched_city"] = city
#         all_cities_gdf_list.append(city_gdf)

#     all_cities_gdf = gpd.GeoDataFrame(
#         pd.concat(all_cities_gdf_list, ignore_index=True), crs="EPSG:4326")

#     # all_cities_gdf.to_file(output_path, index=False, driver="GeoJSON", 
#     #                      engine='fiona', crs="EPSG:4326")

#     return all_cities_gdf


def fetch_city_center(city,country,admin_level):
    """
    Fetch OSM city center for a given city.

    ### Parameters:
    - city: Name of the city to be fetched.
    - country: Country of the city to be fetched.
    - admin_level: Administrative level tag for the city to be fetched.

    ### Returns: 
    - GeoPandasDataFrame with city center fetched.

    """

    overpass_query = fr"""[out:json][timeout:20];
    area[name="{city}"][boundary="administrative"][admin_level={admin_level}]->.small;
    area["ISO3166-1"="{country}"]->.big;
    (
    node["place" = "city"](area.small)(area.big);
    );
    out geom;
    """


    response = osm_request(overpass_query)


    decoded_data = json.loads(response.text)

    geojson = osm2geojson.json2geojson(decoded_data)
    gdf = gpd.GeoDataFrame.from_features(geojson,crs="EPSG:4326")
    filtered_gdf = gdf[["id","geometry"]]

    return filtered_gdf

def fetch_osm_multiple_cities(city_list, output_path=""):
    """
    Fetch OSM data for multiple cities.

    ### Parameters:
    - city_list: List of cities to be fetched

    ### Returns: 
    - GeoPandasDataFrame with fetched infrastrcuture for all required OSM cities.

    """    
    all_cities_gdf_list = []
    all_cities_gdf_cc_list = []

    for (city,country, admin_level,radius) in city_list:
        print("Fetching " + city)
        city_center_gdf = fetch_city_center(city,country, admin_level)
        city_center_gdf["fetched_city"] = city
        all_cities_gdf_cc_list.append(city_center_gdf)

        if len(city_center_gdf) > 1:
            raise Exception("More than 1 city center")
        
        cc_lat = city_center_gdf["geometry"][0].y

        cc_lon = city_center_gdf["geometry"][0].x

        city_gdf = fetch_osm_city(radius,cc_lat, cc_lon)
        city_gdf["fetched_city"] = city
        all_cities_gdf_list.append(city_gdf)
        time.sleep(60) ## Wait for OSM so number of requests does not reach the quota

    all_cities_gdf_cc = gpd.GeoDataFrame(
        pd.concat(all_cities_gdf_cc_list, ignore_index=True), crs="EPSG:4326")


    all_cities_gdf = gpd.GeoDataFrame(
        pd.concat(all_cities_gdf_list, ignore_index=True), crs="EPSG:4326")

    return all_cities_gdf_cc, all_cities_gdf


def load_geodata(gdf, table_name, engine):
    """
    Simple function to convert a GeoDataframe into a Postgis Table. Useful to have it as a function to control if_exists behaviour more easily.
    """
    gdf.to_postgis(
        table_name,
        engine,
        if_exists="append",
        index=False
    )


# CITY_LIST = [("Graz","AT",6,5000),("Madrid","ES",8,8000),("Stockholms kommun", "SE", 7,8000),("Hamburg","DE", 4,8000),("Berlin","DE", 4,8000), ("Padova","IT", 8,3000),("Córdoba","ES",8,3000)]

"""
It is better to fetch city by city to avoid hitting Overpass API limits
"""
CITY_LIST = [("Stockholms kommun", "SE", 7,8000)]

# CITY_LIST = [("Hamburg","DE", 4,8000)]

# CITY_LIST = []
#CITY_LIST = [("Madrid","ES")]
#print(os.getenv("POSTGRES_USER"))
#print(os.getenv("POSTGRES_DB"))


def main():
    load_dotenv()

    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@"
        f"localhost:5432/"
        f"{os.getenv('POSTGRES_DB')}"
    )

    engine = create_engine(db_url)



    [gdf_cc,gdf] = fetch_osm_multiple_cities(CITY_LIST)


    load_geodata(
        gdf=gdf_cc,
        table_name="city_center_table",
        engine=engine,
    )

    load_geodata(
        gdf=gdf,
        table_name="raw_table",
        engine=engine,
    )

    print(f"Loaded {len(gdf_cc)} rows")

    print(f"Loaded {len(gdf)} rows")


    

if __name__ == "__main__":
    main()

