-- === Настрой свои вершины ===
WITH params AS (
    SELECT
        4178701423::bigint AS start_v,
        7098320066::bigint AS end_v
),
-- === Проверяем, в каких компонентах находятся вершины ===
components AS (
    SELECT node, component
    FROM pgr_connectedComponents(
        'SELECT id, source, target, cost, reverse_cost FROM routing_graph'
    )
),

-- === Компоненты для конкретных вершин ===
check_vertices AS (
    SELECT
        p.start_v,
        p.end_v,
        c1.component AS start_component,
        c2.component AS end_component
    FROM params p
    LEFT JOIN components c1 ON c1.node = p.start_v
    LEFT JOIN components c2 ON c2.node = p.end_v
)

SELECT
    start_v,
    end_v,
    start_component,
    end_component,
    CASE
        WHEN start_component IS NULL OR end_component IS NULL THEN
            '❌ Одна из вершин отсутствует в графе'
        WHEN start_component != end_component THEN
            '⚠️ Вершины находятся в разных несвязных компонентах'
        ELSE
            '✅ Вершины связаны (можно строить маршрут)'
    END AS status
FROM check_vertices;
