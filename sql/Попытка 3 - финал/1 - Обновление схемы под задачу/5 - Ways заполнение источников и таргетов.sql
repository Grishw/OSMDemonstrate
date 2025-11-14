-- 2. Создаём топологию (генерирует ways_vertices_pgr и заполняет source/target)
DROP TABLE IF EXISTS temp_nodes CASCADE;
CREATE TEMPORARY TABLE temp_nodes AS
SELECT DISTINCT ON (way_id) way_id, node_id AS id
FROM way_nodes
ORDER BY way_id, sequence_id ASC;

DROP TABLE IF EXISTS temp_nodes2 CASCADE;
CREATE TEMPORARY TABLE temp_nodes2 AS
SELECT DISTINCT ON (way_id) way_id, node_id AS id
FROM way_nodes
ORDER BY way_id, sequence_id DESC;

UPDATE ways
SET
    source = nodes.id,
    target = nodes2.id,
    cost = ST_Length(linestring::geography),
    reverse_cost = CASE WHEN 'oneway' IN (tags->'highway') THEN NULL ELSE ST_Length(linestring::geography) END
FROM temp_nodes AS nodes
JOIN temp_nodes2 AS nodes2 USING(way_id)
WHERE ways.id = nodes.way_id AND ways.id = nodes2.way_id;