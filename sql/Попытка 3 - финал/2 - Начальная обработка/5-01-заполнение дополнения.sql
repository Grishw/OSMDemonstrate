-- Для вершин, которых нет в vertex_usage_analysis (должно быть мало)
UPDATE routing_graph_vertices_pgr 
SET 
    way_count = 0,
    vertex_type = 4, -- неопределено
    is_junction = false
WHERE way_count IS NULL;


-- Проверим распределение типов вершин
SELECT 
    vertex_type,
    CASE vertex_type
        WHEN 0 THEN 'ТОЛЬКО НАЧАЛО пути'
        WHEN 1 THEN 'ТОЛЬКО КОНЕЦ пути' 
        WHEN 2 THEN 'ПРОМЕЖУТОЧНАЯ точка'
        WHEN 3 THEN 'НАЧАЛО И КОНЕЦ (короткий путь)'
        WHEN 4 THEN 'НЕОПРЕДЕЛЕНО'
    END as type_description,
    COUNT(*) as vertex_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM routing_graph_vertices_pgr), 2) as percentage,
    AVG(way_count) as avg_ways_per_vertex,
    COUNT(CASE WHEN is_junction THEN 1 END) as junction_count
FROM routing_graph_vertices_pgr 
GROUP BY vertex_type
ORDER BY vertex_type;

