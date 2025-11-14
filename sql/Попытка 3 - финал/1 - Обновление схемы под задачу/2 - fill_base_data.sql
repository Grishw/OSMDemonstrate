-- Скрипт 2: Наполнение базовыми данными
INSERT INTO routing_graph (
    way_id, 
    length_m, 
    name, 
    highway, 
    geom
)
SELECT 
    w.id as way_id,
    ST_Length(ST_Transform(w.linestring, 3857)) as length_m,
    w.tags->'name' as name,
    w.tags->'highway' as highway,
    w.linestring as geom
FROM ways w
WHERE w.tags ? 'highway'
  AND w.tags->'highway' IN (
      'motorway', 'motorway_link', 'trunk', 'trunk_link', 
      'primary', 'primary_link', 'secondary', 'secondary_link', 
      'tertiary', 'tertiary_link', 'unclassified', 'residential', 
      'service', 'living_street', 'road'
  );