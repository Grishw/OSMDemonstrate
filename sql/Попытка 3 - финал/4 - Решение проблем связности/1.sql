-- Шаг 1: Создаем таблицу проблемных вершин
CREATE TABLE if not exists problem_vertices AS
SELECT 
    v.id as vertex_id,
    v.cnt as current_connections,
	v.ein as current_connections_in,
	v.eout as current_connections_out,
    v.way_count as should_have_connections,
    v.the_geom,
    -- Собираем информацию о ways, которые соединяются в этой вершине
    ARRAY(
        SELECT DISTINCT wn.way_id 
        FROM way_nodes wn 
        WHERE wn.node_id = v.id
    ) as connecting_ways
FROM routing_graph_vertices_pgr v
WHERE v.vertex_type = 2 
  AND v.way_count > 1
  AND v.cnt < v.way_count;  -- Только где есть разрыв

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS problem_vertices_index_vertex_id ON problem_vertices (vertex_id);

select * from problem_vertices;