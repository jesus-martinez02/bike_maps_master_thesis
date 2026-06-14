def create_final_table(conn, final_table_name, overwrite = False):
    """
    Creates final table
    """
    with conn.cursor() as cur:
        if overwrite:
            cur.execute(f"""
            DROP TABLE {final_table_name};
            """)

        cur.execute(f"""
            CREATE TABLE {final_table_name};
            """)

def add_city(conn, city_name, final_table_name, city_table_name):
    """
    Adds city to final table
    """
    with conn.cursor() as cur:

        cur.execute(f"""DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'public' 
                AND TABLE_NAME = '{final_table_name}'
            ) THEN
                CREATE TABLE {final_table_name} AS (
                    SELECT * FROM {city_table_name}
                );
            ELSE
                DELETE FROM {final_table_name}
                WHERE fetched_city = '{city_name}';

                INSERT INTO {final_table_name}
                    SELECT * FROM {city_table_name}
                ;

                


            END IF;        
        END
        $$;
        """)

        cur.execute(f"""
        DROP INDEX IF EXISTS {final_table_name}_geom_idx;        
        CREATE INDEX IF NOT EXISTS  {final_table_name}_geom_idx
        ON  {final_table_name}
        USING GIST (geom);        
        """)

        

                #DROP TABLE {city_table_name};
