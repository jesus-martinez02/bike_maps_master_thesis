
import psycopg2
from .network_processing import remove_dead_ends, simplify_network, network_creation
from .poidpy_trip_generation import poidpy_trip_generation
from .trip_distribution import sample_od_pairs
from sqlalchemy import create_engine



def create_grid_table(conn, city_name, grid_size,  grid_table_name, vertex_table):
        """
        Creates a table representing a grid.

        ### Parameters
        - conn: Psycopg2 connection
        - city_name: Name of the current city
        - grid_size: Length in m of the side of each cell inside the grid
        - grid_table_name: Name of the output grid table
        - vertex_table: Name of the input vertex table

        """
        with conn.cursor() as cur:
            cur.execute(f"""
                DROP TABLE IF EXISTS {grid_table_name};
                CREATE TABLE {grid_table_name} AS
                (
                WITH bounds AS (
                    SELECT ST_Transform(
                            ST_Envelope(ST_Collect(geom)),
                            3857
                        ) AS geom
                    FROM {vertex_table}
                ),
                grid1 AS
                (SELECT
                ST_Transform((ST_SquareGrid({grid_size}, geom)).geom, 4326) AS geom
                FROM bounds)
                SELECT DISTINCT g.geom as geom
                FROM grid1 g
                JOIN {vertex_table} v
                ON ST_Intersects(
                    g.geom,
                    v.geom)
                );

                ALTER TABLE {grid_table_name}
                ADD COLUMN id bigserial PRIMARY KEY;

                UPDATE {grid_table_name}
                SET id = id - 1;
            """)

            cur.execute(f"""
                ALTER TABLE {grid_table_name}
                ADD COLUMN city_center TEXT DEFAULT 'No';
            """)
            cur.execute(f"""
            UPDATE {grid_table_name} t
            SET city_center = 'Yes'
            FROM(
            SELECT g.id as id
            FROM {grid_table_name} g
            CROSS JOIN (SELECT * FROM city_center_area WHERE fetched_city = '{city_name}') p
            WHERE ST_Intersects(p.geom, g.geom)
            ) c
            WHERE t.id = c.id;
            """)




def calculate_edge_percentiles(conn, starting_seed, edge_table, selected_ods_table, num_ods, out_table,include_different_sensitivity = True):
    """
    Calculates number of occurences and percentiles for each edge in the network according to shortest path from A*.

    ### Parameters
    - conn: Psycopg2 connection
    - starting_seed: Deprecated, it is ignored in this version
    - edge_table: Name of the input edge table
    - selected_ods_table: Name of the table containing the origin and destination vertices to be considered.
    - num_ods: Number of O-Ds to be considered
    - out_table: Output edge table with calculated columns for number of occurences and percentiles.
    - include_different_sensitivity: Whether different sensitivity towards bicycle infrastructure should be included or not

    """
    with conn.cursor() as cur:
        random_seed = starting_seed
        cur.execute(f"""
            DROP TABLE IF EXISTS {out_table};
            CREATE TABLE {out_table} AS
            (
            SELECT *, 0 as count_occ
            FROM {edge_table}
            );
        """)

        cur.execute(f"""SELECT MAX(id) FROM {selected_ods_table}
        """)
        
        MAX_OD = cur.fetchone()[0]


        increment = 1000

        if include_different_sensitivity is False:
            increment = 10000
            

        it = 0
        for i in range (0,num_ods,increment):
            min_od = i
            max_od = i + increment


            if min_od > MAX_OD:
                break

            if include_different_sensitivity:
                cur.execute(f"""
                    UPDATE {edge_table}
                    SET cost = (1 + ((weight_cost - 1)) * (SELECT value FROM infra_parameter WHERE id = {it}) )* ST_Length(geom::geography)
                """)

                cur.execute(f"""UPDATE {edge_table}
                SET reverse_cost = CASE
                WHEN calc_oneway = 'yes'
                THEN -1
                ELSE weight_cost * ST_Length(geom::geography)
                END;
                """)


            cur.execute(f"""
                UPDATE {out_table} h
                SET count_occ = h.count_occ + q.count_occ
                FROM(SELECT e2.*, e1.count_occ AS count_occ FROM
                (
                (SELECT edge as id, count(*) as count_occ
                FROM pgr_aStar('SELECT id, source, target, cost, reverse_cost, x1, x2, y1, y2 FROM {edge_table}',
                    'SELECT origin_vertex as source, destination_vertex as target FROM {selected_ods_table}
                    WHERE id >= {min_od}
                    AND id < {max_od}
                    AND id < {MAX_OD}')
                GROUP BY edge) e1
                INNER JOIN {edge_table} e2
                ON e1.id = e2.id)   
                ) q
                WHERE h.id = q.id;
            """)

            it += 1

            print(f"Calculated up to od {max_od}")

        random_seed += 0.001




        cur.execute(f"""
            DROP INDEX IF EXISTS {out_table}_geom_idx;        
            CREATE INDEX IF NOT EXISTS {out_table}_geom_idx
            ON {out_table}
            USING GIST (geom);
        """)

        cur.execute(f"""
            
            ALTER TABLE {out_table}
            ADD COLUMN percentile float;

            WITH ranked AS (
                SELECT
                    id,
                    percent_rank() OVER (ORDER BY count_occ) AS perc
                FROM {out_table}
            )
            UPDATE {out_table} t
            SET percentile = r.perc
            FROM ranked r
            WHERE t.id = r.id;
        """)


    return out_table

def reduce_network(conn, thresehold, in_edge_table, in_vertex_table, out_edge_table, out_vertex_table, remove_existing_tables = True):
    """
    Reduces a network by removing edges below a certain percentile thresehold

    CURRENTLY NOT IN USE
    """
    with conn.cursor() as cur:
        #gap_filling(conn,num_iterations=10, edge_table=in_edge_table, interval_length=)

        cur.execute(f"""
        DROP TABLE temp_edges;
        CREATE TABLE temp_edges AS
        (SELECT * FROM {in_edge_table}
        WHERE percentile >= {thresehold});
        """)



        if remove_existing_tables:
            cur.execute(f"""
            DROP TABLE {in_edge_table};
                DROP TABLE {in_vertex_table};
            """)

        network_creation(conn, "temp_edges", out_vertex_table, create_edge_columns = False)
        simplify_network(conn, "temp_edges", out_edge_table, out_vertex_table)
        remove_dead_ends(conn,out_edge_table, out_vertex_table , num_it=1)
        simplify_network(conn, out_edge_table, out_edge_table, out_vertex_table)
        remove_dead_ends(conn,out_edge_table, out_vertex_table , num_it=1)
        simplify_network(conn, out_edge_table, out_edge_table, out_vertex_table)

        

def gap_filling(conn, num_iterations, edge_table, interval_length = 100):
    """
    Applies gap filling algorithm by assigning higher percentiles to edges adjacent to edges that would become disconnected at the current percentile bin.

    ### Parameters:
    - conn: Psycopg2 connection
    - num_iterations: Number of iterations that are performed for fidning disconnected edges
    - edge_table: Input edge table
    - interval_length: Length of each percentile bin.

    """
    with conn.cursor() as cur:
        cur.execute(f"""
        ALTER TABLE {edge_table}
        DROP COLUMN IF EXISTS new_percentile;
 
        ALTER TABLE {edge_table}
        ADD COLUMN new_percentile float;
                
        UPDATE {edge_table}
        SET new_percentile = percentile;
        
        ALTER TABLE {edge_table}
        ALTER COLUMN geom TYPE geometry(LINESTRING, 4326)
        USING ST_SetSRID(geom,4326);   
    """)

        for thresehold in range(90,100,interval_length):
            for _ in range(num_iterations):
                cur.execute(f"""
                UPDATE {edge_table} AS e
                SET new_percentile = {thresehold/100}
                FROM
                (WITH disconnected_vertices AS
                (
                SELECT node as id
                FROM pgr_degree('SELECT id, source, target FROM {edge_table} WHERE new_percentile >= {thresehold/100}')
                WHERE degree = 1)
                SELECT DISTINCT ON (v.id) e.id as id FROM {edge_table} e
                JOIN disconnected_vertices v
                ON e.source = v.id
                OR e.target = v.id
                WHERE new_percentile < {thresehold/100}
                ORDER BY v.id, new_percentile DESC) AS new_e
                WHERE e.id = new_e.id;
                """)


                cur.execute(f"""
                    DROP INDEX IF EXISTS {edge_table}_geom_idx;        
                    CREATE INDEX IF NOT EXISTS {edge_table}_geom_idx
                    ON {edge_table}
                    USING GIST (geom);
                """)
