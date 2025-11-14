CREATE OR REPLACE FUNCTION find_route_pgr_dijkstra(
    start_lon DOUBLE PRECISION,
    start_lat DOUBLE PRECISION, 
    end_lon DOUBLE PRECISION,
    end_lat DOUBLE PRECISION
)
RETURNS TABLE(
    seq INTEGER,
    node BIGINT,
    edge BIGINT,
    cost DOUBLE PRECISION,
    agg_cost DOUBLE PRECISION,
    road_name TEXT,
    road_type TEXT,
    geom GEOMETRY
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Начинаем транзакцию
    BEGIN
        -- Создаем временную таблицу для точек
        CREATE TEMPORARY TABLE temp_route_points ON COMMIT DROP AS
        WITH start_point AS (
            SELECT id FROM routing_graph_vertices_pgr 
            ORDER BY the_geom <-> ST_SetSRID(ST_Point(start_lon, start_lat), 4326)
            LIMIT 1
        ),
        end_point AS (
            SELECT id FROM routing_graph_vertices_pgr 
            ORDER BY the_geom <-> ST_SetSRID(ST_Point(end_lon, end_lat), 4326)
            LIMIT 1
        )
        SELECT 
            (SELECT id FROM start_point) as start_id,
            (SELECT geom FROM nodes WHERE id = (SELECT id FROM start_point)) as start_geom,
            (SELECT id FROM end_point) as end_id,
            (SELECT geom FROM nodes WHERE id = (SELECT id FROM end_point)) as end_geom;

        -- Создаем временные связи
        INSERT INTO routing_graph_fixed (id, source, target, cost, reverse_cost, length_m, geom)
        SELECT 
            nextval('routing_graph_id_seq'),
            trp.start_id,
            (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1),
            0, 0,
            ST_Distance(trp.start_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1)::geography),
            ST_MakeLine(trp.start_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1))
        FROM temp_route_points trp

        UNION ALL

        SELECT 
            nextval('routing_graph_id_seq'),
            trp.end_id,
            (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1),
            0, 0,
            ST_Distance(trp.end_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1)::geography),
            ST_MakeLine(trp.end_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1))
        FROM temp_route_points trp;

        -- Возвращаем маршрут
        RETURN QUERY
        SELECT 
            path.seq, 
            path.node, 
            path.edge, 
            path.cost,
            path.agg_cost,
            COALESCE(rg.name, 'Temporary connection') as road_name,
            COALESCE(rg.highway, 'connection') as road_type,
            rg.geom
        FROM pgr_dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM routing_graph_fixed',
            (SELECT start_id FROM temp_route_points),
            (SELECT end_id FROM temp_route_points),
            directed := true
        ) AS path
        JOIN routing_graph_fixed rg ON path.edge = rg.id
        ORDER BY path.seq;

        -- Откатываем транзакцию (временные данные удалятся автоматически)
        ROLLBACK;

    EXCEPTION
        WHEN OTHERS THEN
            -- При ошибке также откатываем
            ROLLBACK;
            RAISE;
    END;
END;
$$;