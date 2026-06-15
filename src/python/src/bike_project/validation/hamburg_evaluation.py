
import psycopg2

def calculate_counts(conn,in_table_query):
    with conn.cursor() as cur:

        cur.execute(f"""
                    DROP TABLE IF EXISTS temp_my_hamburg;
                    CREATE TABLE temp_my_hamburg AS(
                        {in_table_query}
                    );
                    """)


        cur.execute(f"""
            ALTER TABLE temp_my_hamburg
            ADD COLUMN line_length FLOAT;

            UPDATE temp_my_hamburg
            SET line_length = ST_Length(ST_Transform(geom,3857));

            ALTER TABLE temp_my_hamburg
            ADD COLUMN cum_length FLOAT;


            WITH calculated_length AS (
                SELECT id, SUM(line_length) OVER (ORDER BY count_occ DESC, id ASC) as running_total
                FROM temp_my_hamburg
            )
            UPDATE temp_my_hamburg h
            SET cum_length = calculated_length.running_total / 1000
            FROM calculated_length
            WHERE h.id = calculated_length.id ;

            DROP TABLE IF EXISTS temp_red_my_hamburg;

            CREATE TABLE temp_red_my_hamburg AS (
                SELECT * FROM temp_my_hamburg WHERE cum_length <= 2000
            );


            ALTER TABLE hamburg_counting_points
            DROP COLUMN IF EXISTS count_sim;
                    
            ALTER TABLE hamburg_counting_points
            ADD COLUMN IF NOT EXISTS count_sim INTEGER;

            WITH counts_sim AS (
                SELECT g.id as id, SUM(l.count_occ) as count_sim
                FROM hamburg_counting_points g
                INNER JOIN
                temp_my_hamburg l
                ON ST_Intersects(g.geom, l.geom)
                GROUP BY g.id
            )
            UPDATE hamburg_counting_points h
            SET count_sim = counts_sim.count_sim
            FROM counts_sim
            WHERE h.id = counts_sim.id ;



            ALTER TABLE grid_validation_hamburg
            ADD COLUMN IF NOT EXISTS count_sim INTEGER;

            UPDATE grid_validation_hamburg h
            SET count_sim = c.count_sim
            FROM hamburg_counting_points c
            WHERE h.counter_id = c.id ;


        """)
