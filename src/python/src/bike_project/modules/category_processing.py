
def create_cycling_categories(conn):
    """
    Assigns bicycle infrastructure and one-way categories depending on OSM tags.
    """
    with conn.cursor() as cur:
        cur.execute("""
        ALTER TABLE raw_table
        ADD COLUMN IF NOT EXISTS category TEXT;
        """)


        cur.execute("""
        UPDATE raw_table
        SET category = CASE
            WHEN surface = 'unpaved'  OR surface = 'compacted' OR surface = 'fine_gravel' OR surface = 'gravel'
                OR surface = 'shells' OR surface = 'rock' OR surface = 'pebblestone' OR surface = 'ground'
                OR surface = 'dirt' OR surface = 'earth' OR surface = 'grass' OR surface = 'mud' OR surface = 'sand'
                OR surface = 'woodchips' THEN 'Unpaved'
            WHEN ((cycleway = 'track' OR highway = 'cycleway') AND (oneway = 'no' OR oneway is NULL)) OR "cycleway:both" = 'track' THEN 'Track' 
            WHEN ((highway = 'cycleway' OR highway='path' OR highway='footway' OR highway='residential' OR highway='service' 
                OR highway = 'unclassified' OR highway = 'track') 
            AND (bicycle = 'yes' OR bicycle ='designated') AND (segregated = 'yes')) THEN 'Track'
            WHEN (highway = 'living_street' AND (bicycle != 'no' OR bicycle is NULL))
                    OR  cyclestreet = 'yes' 
                    OR bicycle_road = 'yes' 
                    THEN 'Cycling_Street' 
            WHEN ((highway = 'cycleway' OR highway='path' OR highway='footway' OR highway='residential' OR highway='service' 
                    OR highway = 'unclassified' OR highway = 'track') AND 
                (bicycle = 'yes' OR bicycle ='designated') AND (foot = 'yes' OR foot = 'designated') AND ((segregated = 'no') OR
                segregated IS  NULL))
                OR (highway IN ('footway', 'pedestrian') AND bicycle IN ('yes','permissive','designated')) THEN 'Track_shared'
            WHEN "cycleway:right" = 'track' THEN 'Right_Track'
            WHEN "cycleway:left" = 'track'  THEN 'Left_Track'
            WHEN "cycleway" = 'lane' OR 'cycleway:both' = 'lane' THEN 'Lane'
            WHEN "cycleway" = 'crossing' OR "cycleway:right" = 'crossing' OR "cycleway:left" = 'crossing' THEN 'Crossing'
            WHEN "cycleway:left" = 'lane' THEN 'Left_Lane'
            WHEN "cycleway:right" = 'lane' THEN 'Right_Lane'
            WHEN "cycleway" = 'shared_lane' OR "cycleway" = 'share_busway' OR "cycleway" = 'shared' THEN 'Shared_Lane'
            WHEN "cycleway:right" = 'shared_lane' OR "cycleway:right" = 'share_busway' OR "cycleway:right" = 'shared' THEN 'Right_Shared_Lane'
            WHEN "cycleway:left" = 'shared_lane' OR "cycleway:left" = 'share_busway' OR "cycleway:left" = 'shared' THEN 'Left_Shared_Lane'
            WHEN (highway IN ('primary','secondary','tertiary','residential') OR (highway = 'unclassified' AND surface = 'asphalt')
                    OR (highway = 'service' AND (access != 'private' OR access IS NULL)))
                    AND (bicycle != 'no'  OR bicycle IS NULL)
                    AND (cycleway != 'separated'  OR cycleway IS NULL)
                    AND ("cycleway:both" != 'separated' OR "cycleway:both" IS NULL) THEN 'Street'
            WHEN highway = 'cycleway' AND oneway = 'yes' THEN 'Track'
            ELSE 'ignore'
        END;
        """)

        cur.execute("""
        ALTER TABLE raw_table
        ADD COLUMN IF NOT EXISTS calc_oneway TEXT;
        """)


        cur.execute("""
        UPDATE raw_table
        SET calc_oneway = CASE
        WHEN "oneway:bicycle" = 'no' THEN 'no'
        WHEN oneway = 'yes' and category IN ('Left_Lane','Lane','Shared_Lane','Crossing', 'Left_Shared_Lane') THEN 'no'
        WHEN oneway = 'yes' THEN 'yes'
        ELSE 'no'            
        END;
        """)
        ## TODO: ADD 


        cur.execute("""
                    DROP TABLE IF EXISTS filtered_table;
                    """)

        cur.execute("""CREATE TABLE filtered_table AS 
                    (SELECT * FROM raw_table
                    WHERE category != 'ignore');
        """)

        cur.execute("""
            DROP INDEX IF EXISTS filtered_table_geom_idx;
                    """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS filtered_table_geom_idx
            ON filtered_table
            USING GIST (geometry);
        """)


    print("Columns updated successfully.")

