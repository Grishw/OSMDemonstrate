-- Скрипт 4: Парсинг максимальной скорости
UPDATE routing_graph 
SET maxspeed_kmh = CASE 
    WHEN w.tags->'maxspeed' ~ '^[0-9]+$' THEN (w.tags->'maxspeed')::integer
    WHEN w.tags->'maxspeed' ~ '^[0-9]+\s*km/h$' THEN 
        regexp_replace(w.tags->'maxspeed', '[^0-9]', '', 'g')::integer
    ELSE NULL
END
FROM ways w
WHERE routing_graph.way_id = w.id;

-- Установка скоростей по умолчанию
UPDATE routing_graph 
SET maxspeed_kmh = COALESCE(maxspeed_kmh,
    CASE
        WHEN highway IN ('motorway', 'motorway_link') THEN 110
        WHEN highway IN ('trunk', 'trunk_link') THEN 90
        WHEN highway IN ('primary', 'primary_link') THEN 70
        WHEN highway IN ('secondary', 'secondary_link') THEN 60
        WHEN highway IN ('tertiary', 'tertiary_link') THEN 50
        ELSE 40
    END
);