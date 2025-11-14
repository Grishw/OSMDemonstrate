-- 5. Обновляем счетчики соединений через временные таблицы
-- Считаем общее количество соединений
CREATE TEMPORARY TABLE temp_vertex_counts AS
SELECT 
    v.id,
    COUNT(rg.id) as cnt,
    COUNT(CASE WHEN rg.target = v.id THEN 1 END) as ein,
    COUNT(CASE WHEN rg.source = v.id THEN 1 END) as eout
FROM routing_graph_vertices_pgr v
LEFT JOIN routing_graph rg ON rg.source = v.id OR rg.target = v.id
GROUP BY v.id;

CREATE INDEX ON temp_vertex_counts (id);

-- Обновляем счетчики
UPDATE routing_graph_vertices_pgr v
SET 
    cnt = tc.cnt,
    ein = tc.ein, 
    eout = tc.eout
FROM temp_vertex_counts tc
WHERE v.id = tc.id;
