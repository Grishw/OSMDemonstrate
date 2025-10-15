
-- source = ближайшая вершина к началу линии
UPDATE ways
SET source = v.id
FROM ways_vertices_pgr v
WHERE ST_Equals(ST_StartPoint(ways.linestring), v.geom);

