def network_creation(conn, edge_table, vertex_table, create_edge_columns=True):
    """
    Crates a network with pgRouting

    ### Parameters
    - conn: Psycopg2 connection
    - edge_table: Name of the input edge table
    - vertex_table: Name of the resulting vertex table
    - create_edge_columns: Whether to create pgRouting columns such as source, target, x1, y1,... if they are not already present

    ### Returns

    - Properly formed pgRouting edge and vertex tables 

    """
    with conn.cursor() as cur:
        cur.execute(f"""DROP TABLE IF EXISTS {vertex_table};
        """)

        cur.execute(f"""SELECT * INTO {vertex_table}
        FROM pgr_extractVertices('SELECT id, geom FROM {edge_table} ORDER BY id');
        """)

        cur.execute(f"""
        DROP INDEX IF exists {vertex_table}_gix;
        CREATE INDEX IF NOT EXISTS {vertex_table}_gix
        ON {vertex_table} USING GIST (geom);
        ANALYZE {vertex_table};
        """)

        if create_edge_columns:
            cur.execute(f"""ALTER TABLE {edge_table}
                        ADD source BIGINT,
                        ADD target BIGINT,
                        ADD x1 FLOAT,
                        ADD y1 FLOAT,
                        ADD x2 FLOAT,
                        ADD y2 FLOAT,
                        ADD cost FLOAT,
                        ADD reverse_cost FLOAT,
                        ADD weight_cost FLOAT,
                        ADD component_source BIGINT,
                        ADD component_target BIGINT;
            """)

        cur.execute(f"""UPDATE {edge_table}
                    SET weight_cost = CASE
                    WHEN category IN ('Track', 'Right_Track', 'Left_Track','Track_shared','Crossing') THEN 1.0
                    WHEN category IN ('Left_Lane', 'Right_Lane', 'Lane', 'Cycling_Street') THEN 1.05
                    WHEN category IN ('Shared_Lane', 'Right_Shared_Lane', 'Left_Shared_Lane') THEN 1.1
                    WHEN category IN ('Street') THEN 1.25
                    WHEN category IN ('Unpaved') THEN 2.0
                    END;
        """)


        cur.execute(f"""UPDATE {edge_table}
                    SET cost = weight_cost * ST_Length(geom::geography);
        """)

        cur.execute(f"""UPDATE {edge_table}
                    SET reverse_cost = CASE
                    WHEN calc_oneway = 'yes'
                    THEN -1
                    ELSE weight_cost * ST_Length(geom::geography)
                    END;
        """)



        # Set the soucre information 
        cur.execute(f"""UPDATE {edge_table} AS e
        SET source = v.id, x1 = x, y1 = y
        FROM {vertex_table} AS v
        WHERE ST_StartPoint(e.geom) = v.geom;
        """)


        # Set the target information */
        cur.execute(f"""UPDATE {edge_table} AS e
        SET target = v.id, x2 = x, y2 = y
        FROM {vertex_table} AS v
        WHERE ST_EndPoint(e.geom) = v.geom;
        """)

def keep_main_component(conn, in_edge_table, vertex_table, component_table, out_edge_table):
    """
    Keeps the largest Strongly Connected Component from a given network
    ### Parameters
    - conn: Psycopg2 connection
    - in_edge_table: Name of the input edge table
    - vertex_table: Name of the input vertex table
    - component_table: Name of the table 
    - out_edge_table: Name of edge table to be created, containing only the largest Strongly connected component

    """

    with conn.cursor() as cur:
        cur.execute(f"""ALTER TABLE {vertex_table} ADD component BIGINT;
        """)

        cur.execute(f"""DROP TABLE IF EXISTS {component_table};
                        CREATE TABLE {component_table} AS 
                        SELECT * FROM pgr_strongComponents(
                        'SELECT id, source, target, cost, reverse_cost FROM {in_edge_table} WHERE source IS NOT NULL AND  target IS NOT NULL'
        );
        """)

        cur.execute(f"""UPDATE {vertex_table} 
        SET component = {component_table}.component 
        FROM {component_table} 
        WHERE {vertex_table}.id = {component_table}.node;
        """)


        cur.execute(f"""UPDATE {in_edge_table} e
        SET component_source = v.component
        FROM {vertex_table} v
        WHERE e.source = v.id;
        """)

        cur.execute(f"""UPDATE {in_edge_table} e
        SET component_target = v.component
        FROM {vertex_table}  v
        WHERE e.target = v.id;
        """)

        cur.execute(f"""
            DROP TABLE IF EXISTS {out_edge_table};
            CREATE TABLE {out_edge_table} AS (
                    SELECT * FROM {in_edge_table} e
                    INNER JOIN 
                    (SELECT component, count(*) FROM {component_table}
                    GROUP BY component
                    ORDER BY count(*) DESC
                    LIMIT 1) comp
                    ON e.component_source = comp.component
                    ); 
            DROP TABLE {component_table};
        """)



        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS {out_edge_table}_geom_idx
            ON {out_edge_table}
            USING GIST (geom);
        """)

        network_creation(conn, edge_table = out_edge_table, vertex_table = vertex_table,
                        create_edge_columns = False)
    

def remove_dead_ends(conn,edge_table, vertex_table, num_it):
    """
    Removes dead ends (edges adjacent only to degree 1 vertices) from a given edge netowrk table.

    ### Parameters
    - conn: Psycopg2 connection
    - edge_table: Name of the input edge table
    - vertex_table: Name of the input vertex table
    - num_it: Number of iterations to remove dead ends
    """
    with conn.cursor() as cur:
        it = 0
        while it < num_it:
            it += 1
            cur.execute(f"""
                WITH leaf_nodes AS (
                SELECT node
                FROM pgr_degree('SELECT id, source, target FROM {edge_table}')
                WHERE degree = 1
                )
                DELETE FROM {edge_table} e
                WHERE e.source IN (SELECT node FROM leaf_nodes)
                OR e.target IN (SELECT node FROM leaf_nodes);
                """)
            deleted = cur.rowcount

            
            cur.execute(f"""
            DROP TABLE IF EXISTS {vertex_table};
            SELECT * INTO {vertex_table}
            FROM pgr_extractVertices('SELECT id, geom FROM {edge_table} ORDER BY id');
            """)

            cur.execute(f"""
            DROP INDEX IF EXISTS {vertex_table}_gix;
            CREATE INDEX IF NOT EXISTS {vertex_table}_gix
            ON {vertex_table} USING GIST (geom);
            ANALYZE {vertex_table};
            """)

            # Set the soucre information 
            cur.execute(f"""UPDATE {edge_table} AS e
            SET source = v.id, x1 = x, y1 = y
            FROM {vertex_table} AS v
            WHERE ST_StartPoint(e.geom) = v.geom;
            """)

            # Set the target information */
            cur.execute(f"""UPDATE {edge_table} AS e
            SET target = v.id, x2 = x, y2 = y
            FROM {vertex_table} AS v
            WHERE ST_EndPoint(e.geom) = v.geom;
            """)

            print(f"Iteration {it}: deleted {deleted} {edge_table}")
            if deleted == 0:
                break


# TODO: Fix table name temp_edges_1234

def simplify_network(conn,in_edge_table, out_edge_table, vertex_table):
    """
    Simplifies network by joining geometries of edges adjacent to vertices of degree 2 together. 

    ### Parameters
    - conn: Psycopg2 connection
    - in_edge_table: Name of the input edge table
    - out_edge_table: Name of the output edge table
    - vertex_table: Name of the input vertex table
    """    
    with conn.cursor() as cur:
        cur.execute(f"""
        DROP TABLE IF EXISTS temp_edges_1234;
        CREATE TABLE temp_edges_1234
        AS
        (
        WITH component_groups AS (
            SELECT component, node AS edge_id
            FROM pgr_connectedComponents(
                'WITH endpoints AS (
                    SELECT source AS node, id AS edge_id, category
                    FROM {in_edge_table}
                    UNION ALL
                    SELECT target AS node, id AS edge_id, category
                    FROM {in_edge_table}
                    ),
                node_stats AS (
                    SELECT node,
                            count(edge_id) AS degree,
                            ARRAY_AGG(edge_id) AS incident_edges,
                            ARRAY_AGG(category) AS categories
                    FROM endpoints
                    GROUP BY node
                    )
                    SELECT ROW_NUMBER() OVER () AS id,
                        incident_edges[1] AS source,
                        incident_edges[2] AS target,
                        1.0 AS cost
                    FROM node_stats
                    WHERE degree = 2
                    AND categories[1] = categories[2]'
            )
        )
        SELECT COALESCE(cg.component, -e.id) AS new_id,
            MIN(e.category) AS category,
            ST_LineMerge(ST_Collect(e.geom)) as geom, 
            MIN(e.osm_id) as osm_id,
            MIN(e.name) as name,
            MIN(e.fetched_city) AS fetched_city,
            MAX(e.calc_oneway) AS calc_oneway
        FROM {in_edge_table} e
        LEFT JOIN component_groups cg ON e.id = cg.edge_id
        GROUP BY COALESCE(cg.component, -e.id)
        );
        ALTER TABLE temp_edges_1234
        ADD COLUMN id bigserial PRIMARY KEY;
        ALTER TABLE temp_edges_1234
        DROP COLUMN new_id;
        DROP TABLE IF EXISTS {out_edge_table};
        CREATE TABLE {out_edge_table} AS (
            SELECT * FROM temp_edges_1234);
        DROP TABLE temp_edges_1234;
        """)

        cur.execute(f"""
            DROP INDEX IF EXISTS {out_edge_table}_geom_idx;        
            CREATE INDEX IF NOT EXISTS {out_edge_table}_geom_idx
            ON {out_edge_table}
            USING GIST (geom);
        """)


        network_creation(conn, edge_table = out_edge_table, vertex_table = vertex_table,
                create_edge_columns = True)
