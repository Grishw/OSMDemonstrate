WITH start_node AS (
    SELECT id AS start_id
    FROM nodes
    ORDER BY geom <-> ST_SetSRID(ST_Point(37.527159 , 55.688414), 4326)
    LIMIT 1
),
end_node AS (
    SELECT id AS end_id
    FROM nodes
    ORDER BY geom <-> ST_SetSRID(ST_Point(37.535284 , 55.692778), 4326)
    LIMIT 1
)
SELECT seq, node, edge, rout.cost, ways.linestring
FROM pgr_dijkstra(
    'SELECT id, source, target, cost
     FROM ways', -- запрос к графу дорог
    (SELECT start_id FROM start_node), -- начало пути
    (SELECT end_id FROM end_node), -- конец пути
    directed := false
) AS rout
LEFT JOIN ways
ON rout.edge = ways.id

