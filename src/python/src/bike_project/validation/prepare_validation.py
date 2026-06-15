
import os
from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd

from sqlalchemy import create_engine,update, delete, text

def add_station_dataset(input_query,counting_stations_count_path,counting_stations_ref_path, counting_stations_ref_table, 
                            counting_stations_count_table, city_name):

    load_dotenv()
    

    db_url = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"localhost:5432/"
    f"{os.getenv('POSTGRES_DB')}"
)

    engine = create_engine(db_url)

    with engine.begin() as conn:
        city_stations_ref_df = gpd.GeoDataFrame.from_file(counting_stations_ref_path)
        city_stations_ref_df.to_postgis("temp_counting_stations_ref", engine, if_exists='replace')
        city_stations_count_df = pd.read_csv(counting_stations_count_path)
        city_stations_count_df.to_sql("temp_counting_stations_count", engine, if_exists='replace')

        conn.execute(text(f"""UPDATE temp_counting_stations_ref p
        SET geometry = ST_ClosestPoint(l.geom,p.geometry)
        FROM ({input_query}) l
        WHERE ST_DWithin(ST_Transform(p.geometry, 3857), ST_Transform(l.geom, 3857), 3);""")
        )

        conn.execute(text(f"""
        CREATE TABLE temp_counting_stations_merged
        AS(
        SELECT q1.id as id, q2.time as time, q2.count as count, q1.count_sim as count_sim, '{city_name}' as fetched_city
        FROM
        (SELECT p.id as id, SUM(l.count_occ) as count_sim
        FROM temp_counting_stations_ref p
        JOIN ({input_query}) l
        ON ST_Distance(p.geometry::geography, l.geom::geography) < 0.1
        WHERE p.id IS NOT NULL
        GROUP BY p.id) q1
        INNER JOIN temp_counting_stations_count q2
        ON q1.id = q2.id
        );
        """))

        conn.execute(text(f"""
        DROP TABLE temp_counting_stations_count;
        """))

        conn.execute(text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'public' 
                AND TABLE_NAME = '{counting_stations_ref_table}'
            ) THEN
                CREATE TABLE {counting_stations_ref_table} AS (
                    SELECT * FROM temp_counting_stations_ref
                );
                DROP TABLE temp_counting_stations_ref;
            ELSE
                DELETE FROM {counting_stations_ref_table}
                WHERE fetched_city = '{city_name}';

                INSERT INTO {counting_stations_ref_table}
                    SELECT * FROM temp_counting_stations_ref
                ;

                
                DROP TABLE temp_counting_stations_ref;


            END IF;        
        END
        $$;
        """))
        conn.execute(text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'public' 
                AND TABLE_NAME = '{counting_stations_count_table}'
            ) THEN
                CREATE TABLE {counting_stations_count_table} AS (
                    SELECT * FROM temp_counting_stations_merged
                );
                DROP TABLE temp_counting_stations_merged;
            ELSE
                DELETE FROM {counting_stations_count_table}
                WHERE fetched_city = '{city_name}';

                INSERT INTO {counting_stations_count_table}
                    SELECT * FROM temp_counting_stations_merged
                ;

                
                DROP TABLE temp_counting_stations_merged;


            END IF;        
        END
        $$;
        """))     
            



