
WITH node_str AS (
	SELECT id
	FROM nodes
	ORDER BY geom <-> ST_SetSRID(ST_Point(37.527159 , 55.688414), 4326)
	LIMIT 1
),
str AS (
    SELECT way_id
    FROM way_nodes, node_str
    WHERE node_id = node_str.id
)
SELECT source
FROM ways AS w
JOIN str ON w.id = str.way_id;