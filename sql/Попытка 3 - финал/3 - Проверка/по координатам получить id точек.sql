WITH start_point AS (
    SELECT id FROM routing_graph_vertices_pgr 
    ORDER BY the_geom <-> ST_SetSRID(ST_Point(37.6173, 55.7558), 4326) -- Москва, Кремль
    LIMIT 1
),
end_point AS (
    SELECT id FROM routing_graph_vertices_pgr 
    ORDER BY the_geom <-> ST_SetSRID(ST_Point(37.6456, 55.7654), 4326) -- Москва, другое место
    LIMIT 1
)
SELECT * from nodes, start_point, end_point
where nodes.id = start_point.id or nodes.id = end_point.id;