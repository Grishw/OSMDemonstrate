
-- Начинаем транзакцию
BEGIN;
-- Задаем точки отдельно
CREATE TEMPORARY TABLE temp_points AS
WITH start_point AS (
    SELECT id FROM routing_graph_vertices_pgr 
    ORDER BY the_geom <-> ST_SetSRID(ST_Point(37.6173, 55.7558), 4326) -- Москва, Кремль
    LIMIT 1
),
end_point AS (
    SELECT id FROM routing_graph_vertices_pgr 
    ORDER BY the_geom <-> ST_SetSRID(ST_Point(37.6456, 55.7654), 4326) -- Москва, другое место
    LIMIT 1
)
SELECT 
    (SELECT id FROM start_point) as start_id,
    (SELECT geom FROM nodes WHERE id = (SELECT id FROM start_point)) as start_geom,
    (SELECT id FROM end_point) as end_id,
    (SELECT geom FROM nodes WHERE id = (SELECT id FROM end_point)) as end_geom;
	
-- Создаем временные связи
INSERT INTO routing_graph_fixed (id, source, target, cost, reverse_cost, length_m, geom)
SELECT 
	nextval('routing_graph_id_seq'),
    tp.start_id,
    (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.start_geom LIMIT 1),
	0,
	0,
    ST_Distance(tp.start_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.start_geom LIMIT 1)::geography),
    ST_MakeLine(tp.start_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.start_geom LIMIT 1))
FROM temp_points tp

UNION ALL

SELECT 
	nextval('routing_graph_id_seq'),
    tp.end_id,
    (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.end_geom LIMIT 1),
	0,
	0,
    ST_Distance(tp.end_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.end_geom LIMIT 1)::geography),
    ST_MakeLine(tp.end_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> tp.end_geom LIMIT 1))
FROM temp_points tp;


-- Пример 1: Кратчайший путь по расстоянию между двумя точками
SELECT 
    path.seq, 
    path.node, 
    path.edge, 
    path.cost,
    path.agg_cost,
    rg.name,
    rg.highway,
    rg.geom
FROM pgr_dijkstra(
    'SELECT id, source, target, cost, reverse_cost FROM routing_graph_fixed',
    (SELECT start_id FROM temp_points),
    (SELECT end_id FROM temp_points),
    directed := true
) AS path
JOIN routing_graph_fixed rg ON path.edge = rg.id
ORDER BY path.seq;

ROLLBACK;