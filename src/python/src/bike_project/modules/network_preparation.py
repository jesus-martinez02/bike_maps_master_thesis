
def pgrouting_start(conn):
    """
    Start pgrouting extension
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE EXTENSION IF NOT EXISTS pgrouting;
        """)

def prepare_network(conn, city_name, out_edge_table):
    """
    Prepares the network from OSM data by keeping ony LineString and creating an index.
    """
    with conn.cursor() as cur:
        cur.execute(f"""CREATE TABLE {out_edge_table} AS 
                (SELECT * FROM filtered_table
                WHERE fetched_city = '{city_name}'
                AND ST_GeometryType(geometry) = 'ST_LineString');
                """)

        cur.execute(f"""ALTER TABLE {out_edge_table} RENAME COLUMN geometry TO geom;
        """)
      
        cur.execute(f"""
            DROP INDEX IF EXISTS {out_edge_table}_geom_idx;
            CREATE INDEX IF NOT EXISTS {out_edge_table}_geom_idx
            ON {out_edge_table}
            USING GIST (geom);
        """)

def intersect_network(conn,in_edge_table,out_edge_table):
    """
    Intersects the network with itself, to produce proper vertices at the intersection points.
    """
    with conn.cursor() as cur:
        cur.execute(f"""
            DROP TABLE IF EXISTS {out_edge_table};
            CREATE TABLE {out_edge_table} AS 
            (
            WITH intersection_points AS
            (SELECT e1.id as id, ST_Collect(ST_Intersection(e1.geom,e2.geom)) as geom
            FROM 
            {in_edge_table} e1 
            JOIN {in_edge_table} e2
            ON ST_Intersects(e1.geom,e2.geom)
            WHERE  GeometryType(ST_Intersection(e1.geom,e2.geom)) = 'POINT'
            GROUP BY e1.id
            )
            SELECT (ST_Dump(ST_Split(e.geom,ip.geom))).geom as "new_geom", e.*
            FROM
            {in_edge_table} e
            JOIN intersection_points ip
            ON e.id = ip.id
            );
            """)

        cur.execute(f"""DROP TABLE {in_edge_table} 
        """)              

        cur.execute(f"""
            ALTER TABLE {out_edge_table} 
            DROP geom;
        """)

        cur.execute(f"""
            ALTER TABLE {out_edge_table} 
            RENAME COLUMN new_geom TO geom;               
        """)

        cur.execute(f"""
            ALTER TABLE {out_edge_table} 
            RENAME COLUMN id TO osm_id;
            ALTER TABLE {out_edge_table}  ADD id SERIAL;               
        """)

        cur.execute(f"""
        ALTER TABLE {out_edge_table}
        ALTER COLUMN geom
        TYPE geometry(LineString, 4326)
        USING ST_SetSRID(geom, 4326);
        """)

        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS {out_edge_table}_geom_idx
            ON {out_edge_table}
            USING GIST (geom);
        """)