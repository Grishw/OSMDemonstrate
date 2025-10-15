-- 1. Добавляем недостающие поля в таблицу ways
ALTER TABLE ways
ADD COLUMN IF NOT EXISTS source BIGINT,
ADD COLUMN IF NOT EXISTS target BIGINT,
ADD COLUMN IF NOT EXISTS cost DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS reverse_cost DOUBLE PRECISION;

-- 2. Создаём топологию (генерирует ways_vertices_pgr и заполняет source/target)
DROP TABLE IF EXISTS ways_vertices_pgr;

CREATE TABLE ways_vertices_pgr (
    id BIGSERIAL PRIMARY KEY,
    in_edges BIGINT[],
    out_edges BIGINT[],
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    geom geometry(Point, 4326)
);

INSERT INTO ways_vertices_pgr (id, in_edges, out_edges, x, y, geom)
SELECT id, in_edges, out_edges, x, y, geom
FROM pgr_extractVertices(
    $$SELECT id, linestring AS geom FROM ways$$,
    false
);

-- source = ближайшая вершина к началу линии
UPDATE ways
SET source = v.id
FROM ways_vertices_pgr v
WHERE ST_Equals(ST_StartPoint(ways.linestring), v.geom);

-- target = ближайшая вершина к концу линии
UPDATE ways
SET target = v.id
FROM ways_vertices_pgr v
WHERE ST_Equals(ST_EndPoint(ways.linestring), v.geom);

-- 3. Заполняем cost длиной геометрии
UPDATE ways
SET cost = ST_Length(linestring::geography)
WHERE cost IS NULL;

-- 4. Делаем обратную стоимость (если дороги двусторонние)
UPDATE ways
SET reverse_cost = cost
WHERE reverse_cost IS NULL;

-- 5. Индекс для ускорения
CREATE INDEX IF NOT EXISTS idx_ways_source ON ways(source);
CREATE INDEX IF NOT EXISTS idx_ways_target ON ways(target);
CREATE INDEX IF NOT EXISTS idx_ways_cost ON ways(cost);
