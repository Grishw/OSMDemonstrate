-- Добавляем столбцы для классификации вершин
ALTER TABLE routing_graph_vertices_pgr 
ADD COLUMN IF NOT EXISTS vertex_type INTEGER, -- 0: начало пути, 1: конец пути, 2: промежуточная
ADD COLUMN IF NOT EXISTS is_junction BOOLEAN, -- является ли точкой соединения
ADD COLUMN IF NOT EXISTS way_count INTEGER;   -- количество путей, проходящих через вершину

-- Временная таблица для анализа использования вершин
CREATE TEMPORARY TABLE IF NOT EXISTS vertex_usage_analysis AS
SELECT 
    node_id,
    COUNT(DISTINCT way_id) as total_ways,
    -- Является ли началом какого-либо пути
    BOOL_OR(sequence_id = min_seq) as is_start_of_some_way,
    -- Является ли концом какого-либо пути  
    BOOL_OR(sequence_id = max_seq) as is_end_of_some_way,
    -- Является ли промежуточной точкой какого-либо пути
    BOOL_OR(sequence_id != min_seq AND sequence_id != max_seq) as is_middle_of_some_way
FROM (
    SELECT 
        wn.node_id,
        wn.way_id,
        wn.sequence_id,
        MIN(wn.sequence_id) OVER (PARTITION BY wn.way_id) as min_seq,
        MAX(wn.sequence_id) OVER (PARTITION BY wn.way_id) as max_seq
    FROM way_nodes wn
    WHERE EXISTS (
        SELECT 1 FROM routing_graph rg WHERE rg.way_id = wn.way_id
    )
) ranked
GROUP BY node_id;

-- Создаем индекс для быстрого JOIN
CREATE INDEX IF NOT EXISTS vertex_usage_analysis_node_id_index ON vertex_usage_analysis (node_id);

-- Обновляем routing_graph_vertices_pgr с новой информацией
UPDATE routing_graph_vertices_pgr v
SET 
    way_count = ua.total_ways,
    vertex_type = CASE
        WHEN ua.is_start_of_some_way AND NOT ua.is_end_of_some_way AND NOT ua.is_middle_of_some_way THEN 0 -- только начало
        WHEN ua.is_end_of_some_way AND NOT ua.is_start_of_some_way AND NOT ua.is_middle_of_some_way THEN 1 -- только конец
        WHEN ua.is_middle_of_some_way THEN 2 -- промежуточная
        WHEN ua.is_start_of_some_way AND ua.is_end_of_some_way THEN 3 -- и начало и конец (короткие пути)
        ELSE 4 -- неопределено
    END,
    is_junction = (ua.total_ways > 1) OR (v.cnt > 2) -- точка соединения если через нее проходит >1 way ИЛИ >2 соединений в графе
FROM vertex_usage_analysis ua
WHERE v.id = ua.node_id;



