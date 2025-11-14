-- Скрипт 8: Создание индексов
CREATE INDEX IF NOT EXISTS idx_routing_graph_way_id ON routing_graph (way_id);
CREATE INDEX IF NOT EXISTS idx_routing_graph_highway ON routing_graph (highway);
CREATE INDEX IF NOT EXISTS idx_routing_graph_oneway ON routing_graph (oneway_processed);
CREATE INDEX IF NOT EXISTS idx_routing_graph_geom ON routing_graph USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_routing_graph_vertices_pgr_geom 
ON routing_graph_vertices_pgr USING GIST (the_geom);