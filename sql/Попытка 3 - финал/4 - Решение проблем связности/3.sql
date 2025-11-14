-- Создаем копию таблицы для безопасного экспериментирования
CREATE TABLE routing_graph_fixed_1 AS TABLE routing_graph;

-- Создаем последовательность для новых way_id
CREATE SEQUENCE IF NOT EXISTS fixed_1_way_id_seq START WITH 1000000000;

-- Временная таблица с middle ways для разделения
CREATE TEMPORARY TABLE middle_ways_to_split AS
SELECT 
    ca.vertex_id as middle_node_id,
    conn->>'way_id' as original_way_id,
    (conn->>'sequence_id')::integer as middle_sequence_id,
    -- Начальная точка way
    (SELECT wn_start.node_id 
     FROM way_nodes wn_start 
     WHERE wn_start.way_id = (conn->>'way_id')::bigint 
     AND wn_start.sequence_id = 0) as way_start_node,
    -- Конечная точка way  
    (SELECT wn_end.node_id 
     FROM way_nodes wn_end 
     WHERE wn_end.way_id = (conn->>'way_id')::bigint 
     AND wn_end.sequence_id = (
         SELECT MAX(sequence_id) 
         FROM way_nodes 
         WHERE way_id = (conn->>'way_id')::bigint
     )) as way_end_node,
    -- Атрибуты оригинального way
    rg.name,
    rg.highway,
    rg.oneway_processed,
    rg.oneway_desc,
    rg.original_oneway,
    rg.junction,
    rg.maxspeed_kmh
FROM connection_analysis ca
CROSS JOIN LATERAL unnest(ca.detailed_connections) as conn
JOIN routing_graph rg ON rg.way_id = (conn->>'way_id')::bigint
WHERE ca.connection_type = 'MIXED_MIDDLE_ENDS'
  AND conn->>'position' = 'middle'
  AND conn->>'in_routing_graph' = 'true';


-- Первая часть: от начала way до middle точки
INSERT INTO routing_graph_fixed_1 (
    id, way_id, source, target, length_m, maxspeed_kmh, cost, reverse_cost, 
    name, highway, oneway_processed, oneway_desc, original_oneway, junction, geom
)
SELECT 
    nextval('routing_graph_id_seq') as id,
    nextval('fixed_1_way_id_seq') as way_id,
    mw.way_start_node as source,
    mw.middle_node_id as target,
    -- Расчет длины на основе точек от начала до middle
    ST_Length(ST_MakeLine(nodes.geom)::geography) as length_m,
    mw.maxspeed_kmh,
    -- Расчет стоимости
    (ST_Length(ST_MakeLine(nodes.geom)::geography) / 1000) / NULLIF(mw.maxspeed_kmh, 0) * 3600 as cost,
    (ST_Length(ST_MakeLine(nodes.geom)::geography) / 1000) / NULLIF(mw.maxspeed_kmh, 0) * 3600 as reverse_cost,
    mw.name,
    mw.highway,
    mw.oneway_processed,
    mw.oneway_desc,
    mw.original_oneway,
    mw.junction,
    ST_MakeLine(nodes.geom) as geom
FROM middle_ways_to_split mw
CROSS JOIN LATERAL (
    -- Собираем геометрию от начала way до middle точки
    SELECT ARRAY_AGG(n.geom ORDER BY wn.sequence_id) as geom
    FROM way_nodes wn
    JOIN nodes n ON wn.node_id = n.id
    WHERE wn.way_id = mw.original_way_id::bigint
      AND wn.sequence_id <= mw.middle_sequence_id
) nodes
WHERE array_length(nodes.geom, 1) > 1;  -- Проверяем, что есть достаточно точек для линии

-- Вторая часть: от middle точки до конца way
INSERT INTO routing_graph_fixed_1 (
    id, way_id, source, target, length_m, maxspeed_kmh, cost, reverse_cost, 
    name, highway, oneway_processed, oneway_desc, original_oneway, junction, geom
)
SELECT 
    nextval('routing_graph_id_seq') as id,
    nextval('fixed_1_way_id_seq') as way_id,
    mw.middle_node_id as source,
    mw.way_end_node as target,
    -- Расчет длины на основе точек от middle до конца
    ST_Length(ST_MakeLine(nodes.geom)::geography) as length_m,
    mw.maxspeed_kmh,
    -- Расчет стоимости
    (ST_Length(ST_MakeLine(nodes.geom)::geography) / 1000) / NULLIF(mw.maxspeed_kmh, 0) * 3600 as cost,
    (ST_Length(ST_MakeLine(nodes.geom)::geography) / 1000) / NULLIF(mw.maxspeed_kmh, 0) * 3600 as reverse_cost,
    mw.name,
    mw.highway,
    mw.oneway_processed,
    mw.oneway_desc,
    mw.original_oneway,
    mw.junction,
    ST_MakeLine(nodes.geom) as geom
FROM middle_ways_to_split mw
CROSS JOIN LATERAL (
    -- Собираем геометрию от middle точки до конца way
    SELECT ARRAY_AGG(n.geom ORDER BY wn.sequence_id) as geom
    FROM way_nodes wn
    JOIN nodes n ON wn.node_id = n.id
    WHERE wn.way_id = mw.original_way_id::bigint
      AND wn.sequence_id >= mw.middle_sequence_id
) nodes
WHERE array_length(nodes.geom, 1) > 1;  -- Проверяем, что есть достаточно точек для линии

-- Удаляем оригинальные ways, которые мы разделили
DELETE FROM routing_graph_fixed_1 
WHERE way_id IN (
    SELECT DISTINCT original_way_id::bigint 
    FROM middle_ways_to_split
);