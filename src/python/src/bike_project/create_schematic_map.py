"""
Script for creating schematic maps. Requires a city name and the relevant percentile to be considered
"""

import psycopg2
import os
from dotenv import load_dotenv
from modules import network_preparation, network_processing, final_table_creation

load_dotenv()
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)



city_name = 'Stockholms kommun'
perc = 0.95

with conn.cursor() as cur:
        cur.execute(f"""
    DROP TABLE IF EXISTS temp_graz_table;
    SELECT * INTO temp_graz_table FROM final_table WHERE fetched_city = '{city_name}';
    """)

    # This was used for Stockholm presentation map (but in the end not shown)
    #     cur.execute(f"""
    # DROP TABLE IF EXISTS temp_graz_table;
    # SELECT * INTO temp_graz_table FROM pres_stockholm;
    # """)

network_processing.network_creation(conn, edge_table = "temp_graz_table", vertex_table = "temp_vertex_table", create_edge_columns=False)

with conn.cursor() as cur:

    cur.execute(f"""
    DROP TABLE IF EXISTS temp_selected_hubs;

    CREATE TABLE temp_selected_hubs
    AS
    (
    SELECT v.id as id, v.geom as geom
    FROM(
    (SELECT * FROM pgr_degree($$SELECT id, source, target FROM temp_graz_table WHERE new_percentile >={perc}$$)
    WHERE degree >=3) sv
    INNER JOIN temp_vertex_table v
    ON SV.node = v.id
    )
    );

    DROP TABLE if exists test_schematic_map;

    CREATE TABLE test_schematic_map
    AS (
    SELECT DISTINCT edges.id as id, edges.geom as geom
    FROM(
    (SELECT edge as edge_id
    FROM pgr_dijkstra('SELECT id, source, target, cost, reverse_cost, x1, x2, y1, y2 FROM temp_graz_table WHERE new_percentile >= {perc}',
        ARRAY(SELECT id from temp_selected_hubs),ARRAY(SELECT id from temp_selected_hubs))) res
    INNER join temp_graz_table edges
    ON res.edge_id = edges.id
    )
    );

    DROP TABLE IF EXISTS temp_hubs_lines;
    CREATE TABLE temp_hubs_lines
    AS (
    WITH all_lines AS(
        SELECT (ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom as geom
        FROM test_schematic_map
    ), all_points AS (
        SELECT ST_Collect(geom) as geom
        FROM temp_selected_hubs
    )
    SELECT DISTINCT (ST_Dump(ST_Split(l.geom, p.geom))).geom as geom
    FROM all_lines l
    CROSS JOIN
    all_points p
    );

    ALTER TABLE temp_hubs_lines
    ADD COLUMN id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY;



    DROP table IF EXISTS temp_proj_grid;
    CREATE table temp_proj_grid AS(
        WITH bounds AS (
    SELECT ST_Transform(
                ST_Envelope(ST_Collect(geom)),
                3857
            ) AS geom 
        FROM temp_hubs_lines
    )
        SELECT
    ST_Transform((ST_SquareGrid(500, geom)).geom,4326) AS geom
        FROM bounds
    );

    DROP TABLE IF EXISTS temp_proj_lines;

    CREATE table temp_proj_lines AS(
        WITH segments AS (
            SELECT (ST_DumpSegments(ST_Boundary(geom))).geom AS geom
            FROM temp_proj_grid
        )
        SELECT DISTINCT ON (
            LEAST(
                ST_AsBinary(geom),
                ST_AsBinary(ST_Reverse(geom))
            )
        )
        geom, 'no' as diagonal 
        FROM segments

        UNION ALL

        SELECT ST_MakeLine(ST_PointN(r,1), ST_PointN(r,3)) as geom,  'yes' as diagonal  FROM (
            SELECT ST_ExteriorRing(geom) AS r FROM temp_proj_grid
        ) d1

        UNION ALL

        SELECT ST_MakeLine(ST_PointN(r,2), ST_PointN(r,4)) as geom,  'no' as diagonal  FROM (
            SELECT ST_ExteriorRing(geom) AS r FROM temp_proj_grid
        ) d2
    );



    DROP TABLE IF EXISTS temp_grid_points;
    CREATE TABLE temp_grid_points AS(
    SELECT (ST_DumpPoints(ST_Collect(geom))).geom as geom
        FROM temp_proj_lines
    );

    DROP TABLE IF EXISTS temp_start_end_points;

    CREATE TABLE temp_start_end_points AS(
        WITH p AS
        (
        SELECT ST_StartPoint(geom) as geom, 'start' as point_type, id
        FROM temp_hubs_lines
        UNION ALL 
        SELECT ST_EndPoint(geom) as geom, 'end' as point_type, id
        FROM temp_hubs_lines
        )
        SELECT p.geom as geom, p.point_type AS point_type, p.id AS id, MAX(streets.name) AS name
        FROM p LEFT JOIN (SELECT name,geom FROM final_table WHERE fetched_city = '{city_name}') streets
        ON ST_Intersects(p.geom,streets.geom)
        GROUP BY p.geom, p.point_type, p.id
    );

    CREATE INDEX idx_temp_grid_points_geom ON temp_grid_points USING GIST(geom);


    DROP TABLE IF EXISTS temp_vertex_simp;

    ALTER TABLE temp_proj_lines
    ADD COLUMN id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY;


    SELECT * INTO temp_vertex_simp
    FROM pgr_extractVertices($$SELECT id, geom FROM temp_proj_lines ORDER BY id$$);

    ALTER TABLE temp_proj_lines
                    ADD source BIGINT,
                    ADD target BIGINT,
                    ADD x1 FLOAT,
                    ADD y1 FLOAT,
                    ADD x2 FLOAT,
                    ADD y2 FLOAT,
                    ADD cost FLOAT,
                    ADD reverse_cost FLOAT;


    UPDATE temp_proj_lines
        SET cost = CASE 
            WHEN diagonal = 'yes' THEN 2
            ELSE 1.0
        END;


    UPDATE temp_proj_lines
        SET reverse_cost = CASE 
            WHEN diagonal = 'yes' THEN 2
            ELSE 1.0
        END;

    UPDATE temp_proj_lines AS e
    SET source = v.id, x1 = x, y1 = y
    FROM temp_vertex_simp AS v
    WHERE ST_StartPoint(e.geom) = v.geom;

    UPDATE temp_proj_lines AS e
    SET target = v.id, x2 = x, y2 = y
    FROM temp_vertex_simp AS v
    WHERE ST_EndPoint(e.geom) = v.geom;

    
    DROP INDEX IF exists temp_proj_lines_gix;
    CREATE INDEX IF NOT EXISTS temp_proj_lines_gix
    ON temp_proj_lines USING GIST (geom);



    DROP INDEX IF exists temp_vertex_simp_gix;
    CREATE INDEX IF NOT EXISTS temp_vertex_simp_gix
    ON temp_vertex_simp USING GIST (geom);

    DROP TABLE IF EXISTS temp_snapped_points;
    CREATE TABLE temp_snapped_points
    AS(
    SELECT b.id as id, b.geom as geom, a.point_type as point_type,
    a.id as edge_id, a.name as name
    FROM temp_start_end_points a
    JOIN LATERAL (
        SELECT b.id,b.geom
        FROM temp_vertex_simp b
        ORDER BY a.geom <-> b.geom
        LIMIT 1
    ) b ON true
    );


    ALTER TABLE temp_snapped_points
    ADD COLUMN fetched_city TEXT;

    UPDATE temp_snapped_points
    SET fetched_city = '{city_name}';

    DROP TABLE IF EXISTS temp_od_list;
    CREATE TABLE temp_od_list AS(
        SELECT ori.id as origin_vertex, des.id as destination_vertex FROM (
            (SELECT * FROM temp_snapped_points
            WHERE point_type = 'start') ori
            INNER JOIN (SELECT * FROM temp_snapped_points
            WHERE point_type = 'end') des
            ON ori.edge_id = des.edge_id
        )
        
    );

    DROP TABLE IF EXISTS temp_restrictions;

    CREATE TABLE temp_restrictions AS
    (
    SELECT ARRAY[l1.id, l2.id] as path, 1 as cost FROM temp_proj_lines l1
    JOIN temp_proj_lines l2
    ON ST_Intersects(l1.geom,l2.geom)
    WHERE l1.id != l2.id
    AND degrees(ST_Angle(l1.geom, l2.geom)) != 180)
    ; """)

    # cur.execute("""
    # DROP TABLE IF EXISTS temp_test_final_schematic_map;

    # CREATE TABLE temp_test_final_schematic_map AS
    # (
    # SELECT edges.id as id, edges.geom as geom
    # FROM(
    # (SELECT edge as edge_id
    # FROM pgr_trsp('SELECT id, source, target, cost, reverse_cost, x1, x2, y1, y2 FROM temp_proj_lines',
    # 'SELECT path, cost FROM temp_restrictions',
    #     'SELECT origin_vertex as source, destination_vertex as target FROM temp_od_list')) res
    # INNER join temp_proj_lines edges
    # ON res.edge_id = edges.id
    # )
    # );
    # """)


    cur.execute("""
    DROP TABLE IF EXISTS temp_test_final_schematic_map;
    CREATE TABLE temp_test_final_schematic_map AS
    (
    SELECT edges.id as id, edges.geom as geom
    FROM(
    (SELECT edge as edge_id
    FROM pgr_bdDijkstra('SELECT id, source, target, cost, reverse_cost, x1, x2, y1, y2 FROM temp_proj_lines',
        'SELECT origin_vertex as source, destination_vertex as target FROM temp_od_list',
                directed => false)) res
    INNER join temp_proj_lines edges
    ON res.edge_id = edges.id
    )
    );
    """)

    cur.execute(f"""
    ALTER TABLE temp_test_final_schematic_map
                    ADD fetched_city TEXT;

    UPDATE temp_test_final_schematic_map
        SET fetched_city = '{city_name}'
    """)


final_table_creation.add_city(conn, city_name, final_table_name = "final_schematic_points", city_table_name = "temp_snapped_points")
final_table_creation.add_city(conn, city_name, final_table_name = "final_schematic_maps", city_table_name = "temp_test_final_schematic_map")
conn.commit()
conn.close()


