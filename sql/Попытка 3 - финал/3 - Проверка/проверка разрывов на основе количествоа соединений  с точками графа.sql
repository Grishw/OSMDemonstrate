-- Проверим количество вершин с соединениями
SELECT 
    COUNT(*) as total_vertices,
    COUNT(CASE WHEN cnt > 0 THEN 1 END) as vertices_with_connections,
	COUNT(CASE WHEN cnt = 0 and way_count = 1 THEN 1 END) as vertices_null_active,
    COUNT(CASE WHEN cnt = 0 and way_count > 1 THEN 1 END) as isolated_vertices
FROM routing_graph_vertices_pgr;