WITH comn AS (
    SELECT DISTINCT 
        component_id, 
        COUNT(node_id) AS num_nodes,
        array_agg(node_id) AS nodes_array
    FROM connected_components
    GROUP BY component_id
    HAVING COUNT(node_id) = 2
)
SELECT 
    comn.*, 
    w.*
FROM 
    comn
LEFT JOIN 
    ways w
ON 
	w.target = ANY(comn.nodes_array)
OR
	w.source = ANY(comn.nodes_array)
ORDER BY w.id;