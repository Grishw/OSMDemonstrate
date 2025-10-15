-- target = ближайшая вершина к концу линии
UPDATE ways
SET target = v.id
FROM ways_vertices_pgr v
WHERE ST_Equals(ST_EndPoint(ways.linestring), v.geom);

