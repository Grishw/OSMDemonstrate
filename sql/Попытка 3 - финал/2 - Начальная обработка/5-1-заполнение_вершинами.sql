
-- 2. Наполняем вершинами из nodes (только те, что используются в ways)
INSERT INTO routing_graph_vertices_pgr (id, the_geom)
SELECT DISTINCT n.id, n.geom
FROM nodes n
WHERE EXISTS (
    SELECT 1 FROM way_nodes wn WHERE wn.node_id = n.id
);
