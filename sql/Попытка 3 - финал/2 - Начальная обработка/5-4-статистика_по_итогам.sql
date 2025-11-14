-- 6. Проверяем результат
SELECT 
    'Всего сегментов' as metric, 
    COUNT(*) as value 
FROM routing_graph
UNION ALL
SELECT 
    'Сегменты с заполненными source/target', 
    COUNT(*) 
FROM routing_graph 
WHERE source IS NOT NULL AND target IS NOT NULL
UNION ALL
SELECT
    'Всего вершин в графе',
    COUNT(*)
FROM routing_graph_vertices_pgr
UNION ALL
SELECT
    'Вершины с cnt > 2 (перекрестки)',
    COUNT(*)
FROM routing_graph_vertices_pgr 
WHERE cnt > 2;