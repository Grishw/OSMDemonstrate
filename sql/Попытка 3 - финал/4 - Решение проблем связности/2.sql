-- Шаг 2: Глубокий анализ уникальных случаев
CREATE TABLE IF NOT EXISTS connection_analysis AS
WITH detailed_way_info AS (
    SELECT 
        pv.vertex_id,
        wn.way_id,
        wn.sequence_id,
        -- Определяем позицию вершины в way
        CASE 
            WHEN wn.sequence_id = min_seq THEN 'start'
            WHEN wn.sequence_id = max_seq THEN 'end'
            ELSE 'middle'
        END as position_in_way,
        -- Информация о соседних узлах
        LAG(wn.node_id) OVER (PARTITION BY wn.way_id ORDER BY wn.sequence_id) as prev_node,
        LEAD(wn.node_id) OVER (PARTITION BY wn.way_id ORDER BY wn.sequence_id) as next_node,
        -- Общая информация о way
        min_seq,
        max_seq,
        total_nodes,
        -- Существует ли сегмент в routing_graph для этого way
        EXISTS(SELECT 1 FROM routing_graph rg WHERE rg.way_id = wn.way_id) as in_routing_graph
    FROM problem_vertices pv
    JOIN way_nodes wn ON pv.vertex_id = wn.node_id
    CROSS JOIN LATERAL (
        SELECT 
            MIN(wn2.sequence_id) as min_seq,
            MAX(wn2.sequence_id) as max_seq,
            COUNT(*) as total_nodes
        FROM way_nodes wn2 
        WHERE wn2.way_id = wn.way_id
    ) way_info
    WHERE wn.way_id = ANY(pv.connecting_ways)
),
-- Группируем по вершинам и анализируем паттерны
vertex_patterns AS (
    SELECT 
        vertex_id,
        -- Основная классификация
        COUNT(way_id) as total_connected_ways,
        COUNT(CASE WHEN position_in_way = 'start' THEN 1 END) as start_connections,
        COUNT(CASE WHEN position_in_way = 'end' THEN 1 END) as end_connections,
        COUNT(CASE WHEN position_in_way = 'middle' THEN 1 END) as middle_connections,
        
        -- Анализ сложности соединений
        COUNT(CASE WHEN prev_node IS NULL THEN 1 END) as dead_start_points,
        COUNT(CASE WHEN next_node IS NULL THEN 1 END) as dead_end_points,
        
        -- Паттерны соединений между ways
        json_AGG(
            json_build_object(
                'way_id', way_id,
                'position', position_in_way,
                'sequence_id', sequence_id,
                'prev_node', prev_node,
                'next_node', next_node,
                'total_nodes', total_nodes,
                'in_routing_graph', in_routing_graph
            )
        ) as detailed_connections,
        
        -- Группируем ways по их положению относительно вершины
        ARRAY_AGG(DISTINCT 
            CASE 
                WHEN position_in_way = 'start' THEN 'start:' || way_id
                WHEN position_in_way = 'end' THEN 'end:' || way_id  
                ELSE 'middle:' || way_id
            END
        ) as connection_pattern,
        
        -- Определяем тип соединения
        CASE 
            -- Тип 1: Только середины (классический случай разрыва)
            WHEN COUNT(CASE WHEN position_in_way = 'middle' THEN 1 END) = COUNT(way_id) 
                 THEN 'ONLY_MIDDLE_CONNECTIONS'
                 
            -- Тип 2: Смесь середины и концов
            WHEN COUNT(CASE WHEN position_in_way = 'middle' THEN 1 END) > 0 
                 AND (COUNT(CASE WHEN position_in_way = 'start' THEN 1 END) > 0 
                      OR COUNT(CASE WHEN position_in_way = 'end' THEN 1 END) > 0)
                 THEN 'MIXED_MIDDLE_ENDS'
                 
            -- Тип 3: Все ways начинаются/заканчиваются в этой вершине (но не отражено в графе)
            WHEN COUNT(CASE WHEN position_in_way IN ('start', 'end') THEN 1 END) = COUNT(way_id)
                 THEN 'ALL_ENDS_NO_MIDDLE'
                 
            ELSE 'COMPLEX_PATTERN'
        END as connection_type,
        
        -- Определяем необходимые действия
        CASE 
            WHEN COUNT(CASE WHEN position_in_way = 'middle' THEN 1 END) = COUNT(way_id) 
                 THEN 'SPLIT_ALL_MIDDLE_WAYS'
                 
            WHEN COUNT(CASE WHEN position_in_way = 'middle' THEN 1 END) > 0 
                 AND (COUNT(CASE WHEN position_in_way = 'start' THEN 1 END) > 0 
                      OR COUNT(CASE WHEN position_in_way = 'end' THEN 1 END) > 0)
                 THEN 'SPLIT_MIDDLE_WAYS_AND_CONNECT_ENDS'
                 
            WHEN COUNT(CASE WHEN position_in_way IN ('start', 'end') THEN 1 END) = COUNT(way_id)
                 THEN 'CREATE_MISSING_CONNECTIONS'
                 
            ELSE 'MANUAL_REVIEW_NEEDED'
        END as required_action

    FROM detailed_way_info
    WHERE in_routing_graph = true  -- Только ways, которые есть в routing_graph
    GROUP BY vertex_id
)
SELECT 
    vp.*,
    pv.current_connections,
    pv.should_have_connections,
    pv.should_have_connections - pv.current_connections as missing_connections,
    pv.the_geom
FROM vertex_patterns vp
JOIN problem_vertices pv ON vp.vertex_id = pv.vertex_id;

-- Статистика по типам соединений
SELECT 
    connection_type,
    required_action,
    COUNT(*) as vertex_count,
    ROUND(AVG(total_connected_ways), 2) as avg_ways_per_vertex,
    ROUND(AVG(missing_connections), 2) as avg_missing_connections,
    SUM(missing_connections) as total_missing_connections
FROM connection_analysis
GROUP BY connection_type, required_action
ORDER BY vertex_count DESC;

-- Детальный анализ для каждого типа
SELECT 
    'ONLY_MIDDLE_CONNECTIONS' as analysis_type,
    COUNT(*) as cases,
    'Нужно разделить ВСЕ ways на сегменты в точке соединения' as solution
FROM connection_analysis 
WHERE connection_type = 'ONLY_MIDDLE_CONNECTIONS'

UNION ALL

SELECT 
    'MIXED_MIDDLE_ENDS',
    COUNT(*) as cases,
    'Разделить middle-ways и создать соединения с end-ways'
FROM connection_analysis 
WHERE connection_type = 'MIXED_MIDDLE_ENDS'

UNION ALL

SELECT 
    'ALL_ENDS_NO_MIDDLE', 
    COUNT(*) as cases,
    'Просто создать недостающие соединения между ways'
FROM connection_analysis 
WHERE connection_type = 'ALL_ENDS_NO_MIDDLE'

UNION ALL

SELECT 
    'COMPLEX_PATTERN',
    COUNT(*) as cases, 
    'Требует ручного анализа - сложные пересечения'
FROM connection_analysis 
WHERE connection_type = 'COMPLEX_PATTERN';

select * from connection_analysis;