WITH components AS (
    SELECT node, component
    FROM pgr_connectedComponents(
        'SELECT id, source, target, cost, reverse_cost FROM ways'
    )
)
SELECT DISTINCT component, COUNT(*) AS num_nodes
FROM components
GROUP BY component
ORDER BY num_nodes DESC;
