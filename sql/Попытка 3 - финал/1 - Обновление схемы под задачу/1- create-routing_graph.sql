-- Создаем основную таблицу для графа маршрутизации
DROP TABLE IF EXISTS routing_graph CASCADE;
CREATE TABLE routing_graph (
    id BIGSERIAL PRIMARY KEY,
    way_id BIGINT,
    source BIGINT,
    target BIGINT,
    length_m DOUBLE PRECISION,
    maxspeed_kmh INTEGER,
    cost DOUBLE PRECISION,
    reverse_cost DOUBLE PRECISION,
    name TEXT,
    highway TEXT,
    oneway_processed INTEGER, -- 1: прямо, -1: обратно, 0: двустороннее
    oneway_desc TEXT,
    original_oneway TEXT,
    junction TEXT,
    geom GEOMETRY(LineString, 4326)
);
