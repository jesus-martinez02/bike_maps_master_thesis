-- This script prepares the datasources used for evaluation in Hamburg
DROP TABLE IF EXISTS hamburg_db_rad_2025;

CREATE TABLE hamburg_db_rad_2025 AS
(
WITH city_center AS (SELECT geometry as geom FROM city_center_table WHERE fetched_city = 'Hamburg')
SELECT h.* FROM
hamburg_db_rad_2025_raw h
INNER JOIN city_center cc
ON ST_Distance(h.geom::geography,cc.geom::geography) < 6000
)

ALTER TABLE hamburg_db_rad_2025
ADD COLUMN line_length FLOAT;

UPDATE hamburg_db_rad_2025
SET line_length = ST_Length(ST_Transform(geom,3857));

ALTER TABLE hamburg_db_rad_2025
ADD COLUMN cum_length FLOAT;

WITH calculated_length AS (
    SELECT id, SUM(line_length) OVER (ORDER BY count DESC, id ASC) as running_total
    FROM hamburg_db_rad_2025
)
UPDATE hamburg_db_rad_2025 h
SET cum_length = calculated_length.running_total / 1000
FROM calculated_length
WHERE h.id = calculated_length.id ;

drop TABLE IF EXISTS red_DB_hamburg;

CREATE TABLE red_db_hamburg AS (
    SELECT * FROM hamburg_db_rad_2025 WHERE cum_length <= 2000
)


ALTER TABLE hamburg_db_rad_2025
ADD COLUMN geom_proj geometry(Linestring,3857);

UPDATE hamburg_db_rad_2025
SET geom_proj = ST_Transform(geom,3857);

CREATE INDEX IF NOT EXISTS hamburg_db_rad_2025_geom_proj_idx
ON hamburg_db_rad_2025
USING GIST (geom_proj);




--- Processs new Stradradeln table

DROP TABLE IF EXISTS hamburg_sr_rad_2019;

CREATE TABLE hamburg_sr_rad_2019 AS
(
WITH city_center AS (SELECT geometry as geom FROM city_center_table WHERE fetched_city = 'Hamburg')
SELECT h.* FROM
hamburg_sr_rad_2019_raw h
INNER JOIN city_center cc
ON ST_Distance(h.geom::geography,cc.geom::geography) < 6000
)


ALTER TABLE hamburg_sr_rad_2019
ADD COLUMN line_length FLOAT;

UPDATE hamburg_sr_rad_2019
SET line_length = ST_Length(ST_Transform(geom,3857));

ALTER TABLE hamburg_sr_rad_2019
ADD COLUMN cum_length FLOAT;

WITH calculated_length AS (
    SELECT id, SUM(line_length) OVER (ORDER BY count DESC, id ASC) as running_total
    FROM hamburg_sr_rad_2019
)
UPDATE hamburg_sr_rad_2019 h
SET cum_length = calculated_length.running_total / 1000
FROM calculated_length
WHERE h.id = calculated_length.id ;

DROP TABLE red_sr_2019;

CREATE TABLE red_sr_2019 AS (
    SELECT * FROM hamburg_sr_rad_2019 WHERE cum_length <= 2000
)


ALTER TABLE hamburg_sr_rad_2019
ADD COLUMN geom_proj geometry(Linestring,3857);

UPDATE hamburg_sr_rad_2019
SET geom_proj = ST_Transform(geom,3857);

DROP INDEX hamburg_sr_rad_2019_geom_proj_idx;
CREATE INDEX IF NOT EXISTS hamburg_sr_rad_2019_geom_proj_idx
ON hamburg_sr_rad_2019
USING GIST (geom_proj);


--- Counting Points


CREATE EXTENSION postgis_sfcgal;
\df public.CG_ApproximateMedialAxis


DROP TABLE temp_hamburg_line_perp_step1;
CREATE TABLE temp_hamburg_line_perp_step1 AS (
WITH base AS (
    SELECT
        id,
        ST_LineMerge(geom_proj) AS geom
    FROM hamburg_db_rad_2025
),
offsets AS (
    SELECT
        id,
        geom,
        ST_OffsetCurve(geom, 60)  AS geom_left,
        ST_OffsetCurve(geom, -60) AS geom_right,
        ST_Length(geom) AS len
    FROM base
    WHERE ST_Length(geom) > 100   
),
samples AS (
    SELECT
        o.id,
        dist,
        ST_LineInterpolatePoint(o.geom_left,  dist / o.len) AS pt_left,
        ST_LineInterpolatePoint(o.geom_right, 1-dist / o.len) AS pt_right
    FROM offsets o,
    LATERAL generate_series(
        50,
        floor(o.len - 50)::INTEGER,
        100
    ) AS dist
)
SELECT
    ROW_NUMBER() OVER () AS id,
    dist,
    (ST_MakeLine(pt_left, pt_right)) AS geom
FROM samples
WHERE pt_left IS NOT NULL
  AND pt_right IS NOT NULL
);


DROP TABlE IF EXISTS hamburg_counting_points;

CREATE TABLE hamburg_counting_points AS (
SELECT id, dist, ST_Transform(geom, 4326) as geom  FROM 
    temp_hamburg_line_perp_step1
)


CREATE INDEX IF NOT EXISTS hamburg_counting_points_geom_idx
ON hamburg_counting_points
USING GIST (geom);


ALTER TABLE hamburg_counting_points
ADD COLUMN count_db INTEGER;


WITH counts_db AS (
    SELECT g.id as id, SUM(count) as count_db
    FROM hamburg_counting_points g
    INNER JOIN
    hamburg_db_rad_2025 l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_db = counts_db.count_db
FROM counts_db
WHERE h.id = counts_db.id ;

ALTER TABLE hamburg_counting_points
ADD COLUMN count_sr INTEGER;

WITH counts_sr AS (
    SELECT g.id as id, sum(l.count) as count_sr
    FROM hamburg_counting_points g
    INNER JOIN
    hamburg_sr_rad_2019 l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_sr = counts_sr.count_sr
FROM counts_sr
WHERE h.id = counts_sr.id ;

ALTER TABLE hamburg_counting_points
ADD COLUMN count_base INTEGER;

WITH counts_base AS (
    SELECT g.id as id, sum(l.count_occ) as count_base
    FROM hamburg_counting_points g
    INNER JOIN
    results_hamburg_base_betweenness l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_base = counts_base.count_base
FROM counts_base
WHERE h.id = counts_base.id ;

ALTER TABLE hamburg_counting_points
ADD COLUMN count_base_pois INTEGER;

WITH counts_base AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_pois
    FROM hamburg_counting_points g
    INNER JOIN
    results_hamburg_base_pois l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_base_pois = counts_base.count_base_pois
FROM counts_base
WHERE h.id = counts_base.id ;

ALTER TABLE hamburg_counting_points
ADD COLUMN count_base_nrd INTEGER;

WITH counts_base AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_nrd
    FROM hamburg_counting_points g
    INNER JOIN
    results_hamburg_base_non_random_des l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_base_nrd = counts_base.count_base_nrd
FROM counts_base
WHERE h.id = counts_base.id ;

ALTER TABLE hamburg_counting_points
ADD COLUMN count_base_dist INTEGER;

WITH counts_base AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_dist
    FROM hamburg_counting_points g
    INNER JOIN
    results_hamburg_base_dist l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_base_dist = counts_base.count_base_dist
FROM counts_base
WHERE h.id = counts_base.id ;


ALTER TABLE hamburg_counting_points
ADD COLUMN count_sim INTEGER;

WITH counts_sim AS (
    SELECT g.id as id, sum(l.count_occ) as count_sim
    FROM hamburg_counting_points g
    INNER JOIN
    results_hamburg_final l
    ON ST_Intersects(g.geom, l.geom)
    GROUP BY g.id
)
UPDATE hamburg_counting_points h
SET count_sim = counts_sim.count_sim
FROM counts_sim
WHERE h.id = counts_sim.id ;
DROP TABLE my_hamburg_table;


CREATE TABLE my_hamburg_table AS (
    WITH city_center AS (SELECT geometry as geom FROM city_center_table WHERE fetched_city = 'Hamburg')
    SELECT h.* FROM
    ((SELECT * FROM raw_table WHERE fetched_city = 'Hamburg') h
    INNER JOIN city_center cc
ON ST_Distance(h.geometry::geography,cc.geom::geography) < 6000)
)


DROP TABLE grid_validation_hamburg;

CREATE TABLE grid_validation_hamburg AS (
WITH bounds AS (
    SELECT ST_Transform(
            ST_Envelope(ST_Collect(geometry)),
            3857
        ) AS geom
    FROM my_hamburg_table
)
(SELECT
ST_Transform((ST_SquareGrid(1000, geom)).geom, 4326) AS geom
FROM bounds)
);

ALTER TABLE grid_validation_hamburg
ADD COLUMN id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY;

ALTER TABLE grid_validation_hamburg
ADD COLUMN counter_id INTEGER;

WITH counters_id AS (
    SELECT DISTINCT ON (g.id) g.id as id, l.id as counter_id
    FROM grid_validation_hamburg g
    INNER JOIN
    hamburg_counting_points l
    ON ST_Intersects(g.geom, l.geom)
    ORDER BY g.id, l.count_db DESC
)
UPDATE grid_validation_hamburg h
SET counter_id = counters_id.counter_id
FROM counters_id
WHERE h.id = counters_id.id ;


ALTER TABLE grid_validation_hamburg
ADD COLUMN count_db INTEGER;


UPDATE grid_validation_hamburg h
SET count_db = c.count_db
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;



ALTER TABLE grid_validation_hamburg
ADD COLUMN count_sr INTEGER;

UPDATE grid_validation_hamburg h
SET count_sr = c.count_sr
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;


ALTER TABLE grid_validation_hamburg
ADD COLUMN count_base INTEGER;

UPDATE grid_validation_hamburg h
SET count_base = c.count_base
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;

ALTER TABLE grid_validation_hamburg
ADD COLUMN count_base_pois INTEGER;

UPDATE grid_validation_hamburg h
SET count_base_pois = c.count_base_pois
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;

ALTER TABLE grid_validation_hamburg
ADD COLUMN count_base_nrd INTEGER;

UPDATE grid_validation_hamburg h
SET count_base_nrd = c.count_base_nrd
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;

ALTER TABLE grid_validation_hamburg
ADD COLUMN count_base_dist INTEGER;

UPDATE grid_validation_hamburg h
SET count_base_dist = c.count_base_dist
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;

ALTER TABLE grid_validation_hamburg
ADD COLUMN count_sim INTEGER;

UPDATE grid_validation_hamburg h
SET count_sim = c.count_sim
FROM hamburg_counting_points c
WHERE h.counter_id = c.id ;

-- Script end ---

SELECT * FROM
grid_validation_hamburg
ORDER BY count_base DESC;

SELECT * FROM raw_table WHERE fetched_city = 'Hamburg'

SELECT * FROM pois_hamburg
WHERE building = 'commercial'
and landuse_outer IS NULL
AND "addr:housenumber" IS NULL
AND priority = 'building'
ORDER BY osmid ASC;

CREATE TABLE temp_hubs_city_final_my_method_v_des_random AS(
SELECT * FROM temp_hubs_city_final_my_method);

DROP TABLE temp_hubs_city_final_my_method;

CREATE TABLE temp_hubs_city_final_my_method
AS (
SELECT * FROM final_table
WHERE fetched_city = 'Hamburg')

DELETE FROM raw_table WHERE fetched_city = 'Hamburg';


DROP TABLE pois_hamburg;

DROP TABLE test_pois_classified_hamburg

SELECT * FROM temp_selected_ods1;

SELECT * FROM raw_table
WHERE fetched_city = 'Hamburg';


SELECT weight_cost from temp_filtered_edges;

CREATE TABLE temp_hubs_city_final_diff_route
AS (
SELECT * FROM final_table
WHERE fetched_city = 'Hamburg')


---- Now part for counting stations
SELECT * FROM
counting_stations_lines_hamburg

SELECT * FROM
counting_stations_hamburg;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_stations INTEGER,
ADD COLUMN num_points INTEGER;

WITH results AS (
SELECT l.id as id, l.geometry as geom, SUM(count) as count_stations, count(*) as num_points FROM
(counting_stations_lines_hamburg l
INNER JOIN counting_stations_hamburg p
ON ST_Distance(l.geometry::geography,p.geometry::geography) < 5)
GROUP BY l.id,l.geometry
)
UPDATE counting_stations_lines_hamburg s
SET num_points = results.num_points,count_stations = results.count_stations
FROM results
WHERE s.id = results.id;


ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_db INTEGER;


WITH counts_db AS (
    SELECT g.id as id, SUM(count) as count_db
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    hamburg_db_rad_2025 l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_db = counts_db.count_db
FROM counts_db
WHERE h.id = counts_db.id ;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_sr INTEGER;

WITH counts_sr AS (
    SELECT g.id as id, sum(l.count) as count_sr
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    hamburg_sr_rad_2019 l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_sr = counts_sr.count_sr
FROM counts_sr
WHERE h.id = counts_sr.id ;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_base INTEGER;

WITH counts_base AS (
    SELECT g.id as id, sum(l.count_occ) as count_base
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    results_hamburg_base_betweenness l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_base = counts_base.count_base
FROM counts_base
WHERE h.id = counts_base.id ;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_sim INTEGER;

WITH counts_sim AS (
    SELECT g.id as id, sum(l.count_occ) as count_sim
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    results_hamburg_final l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_sim = counts_sim.count_sim
FROM counts_sim
WHERE h.id = counts_sim.id ;


ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_base_pois INTEGER;

WITH counts_sim AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_pois
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    results_hamburg_base_pois l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_base_pois = counts_sim.count_base_pois
FROM counts_sim
WHERE h.id = counts_sim.id ;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_base_dist INTEGER;

WITH counts_sim AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_dist
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    results_hamburg_base_dist l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_base_dist = counts_sim.count_base_dist
FROM counts_sim
WHERE h.id = counts_sim.id ;

ALTER TABLE counting_stations_lines_hamburg
ADD COLUMN count_base_non_random_des INTEGER;

WITH counts_sim AS (
    SELECT g.id as id, sum(l.count_occ) as count_base_non_random_des
    FROM counting_stations_lines_hamburg g
    INNER JOIN
    results_hamburg_base_non_random_des l
    ON ST_Intersects(g.geometry, l.geom)
    GROUP BY g.id
)
UPDATE counting_stations_lines_hamburg h
SET count_base_non_random_des = counts_sim.count_base_non_random_des
FROM counts_sim
WHERE h.id = counts_sim.id ;

