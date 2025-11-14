-- Первые узлы каждого way (source)
CREATE TEMPORARY TABLE temp_first_nodes AS
SELECT DISTINCT ON (way_id) way_id, node_id
FROM way_nodes
ORDER BY way_id, sequence_id ASC;

-- Последние узлы каждого way (target)  
CREATE TEMPORARY TABLE temp_last_nodes AS
SELECT DISTINCT ON (way_id) way_id, node_id
FROM way_nodes
ORDER BY way_id, sequence_id DESC;

-- Создаем индексы на временных таблицах для быстрого JOIN
CREATE INDEX ON temp_first_nodes (way_id);
CREATE INDEX ON temp_last_nodes (way_id);

-- Обновляем source и target одним запросом
UPDATE routing_graph rg
SET 
    source = fn.node_id,
    target = ln.node_id
FROM temp_first_nodes fn
JOIN temp_last_nodes ln ON fn.way_id = ln.way_id
WHERE rg.way_id = fn.way_id;

-- 4. Создаем индексы для производительности
CREATE INDEX IF NOT EXISTS idx_routing_graph_source ON routing_graph (source);
CREATE INDEX IF NOT EXISTS idx_routing_graph_target ON routing_graph (target);
CREATE INDEX IF NOT EXISTS idx_routing_graph_vertices_pgr_geom 
ON routing_graph_vertices_pgr USING GIST (the_geom);
