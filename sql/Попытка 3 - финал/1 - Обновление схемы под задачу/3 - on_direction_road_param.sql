-- Скрипт 3: Обработка одностороннего движения
UPDATE routing_graph 
SET 
    oneway_processed = CASE 
        WHEN w.tags->'oneway' IN ('yes', '1', 'true') THEN 1
        WHEN w.tags->'oneway' = '-1' THEN -1
        WHEN w.tags->'oneway' IN ('reversible', 'alternating') THEN 0
        WHEN w.tags->'junction' = 'roundabout' THEN 1
        WHEN w.tags->'highway' IN ('motorway', 'motorway_link') THEN 1
        WHEN w.tags->'oneway' IN ('no', 'false', '0') THEN 0
        ELSE 0
    END,
    original_oneway = w.tags->'oneway',
    junction = w.tags->'junction'
FROM ways w
WHERE routing_graph.way_id = w.id;

-- Добавляем текстовое описание
UPDATE routing_graph 
SET oneway_desc = CASE oneway_processed 
    WHEN 1 THEN 'ONEWAY_FORWARD'
    WHEN -1 THEN 'ONEWAY_BACKWARD' 
    WHEN 0 THEN 'TWOWAY'
    ELSE 'UNKNOWN'
END;
