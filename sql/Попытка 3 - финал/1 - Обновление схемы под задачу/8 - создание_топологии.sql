-- Скрипт 5: Создание топологии на основе OSM структур

-- 1. Создаем таблицу вершин из nodes
CREATE TABLE IF NOT EXISTS routing_graph_vertices_pgr (
    id BIGINT PRIMARY KEY,        -- ID узла из таблицы nodes (оригинальный OSM node_id)
    cnt INTEGER,                  -- Количество connected edges (ребер, соединенных с этой вершиной)
    chk INTEGER,                  -- Флаг проверки (для отладки топологии)
    ein INTEGER,                  -- Количество входящих ребер (edges incoming)
    eout INTEGER,                 -- Количество исходящих ребер (edges outgoing)  
    the_geom GEOMETRY(Point, 4326) -- Геометрия точки (координаты узла)
);
