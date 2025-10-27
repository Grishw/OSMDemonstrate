WITH
  start_pt AS (
	SELECT id
	FROM ways_vertices_pgr
	ORDER BY the_geom <-> ST_SetSRID(ST_Point(:lon1, :lat1), 4326)
	LIMIT 1
  ),
  end_pt AS (
	SELECT id
	FROM ways_vertices_pgr
	ORDER BY the_geom <-> ST_SetSRID(ST_Point(:lon2, :lat2), 4326)
	LIMIT 1
  ),
  route AS (
	SELECT r.seq, r.node, r.edge, w.linestring AS geom
	FROM pgr_dijkstra(
	  $$SELECT id, source, target, cost FROM ways WHERE tags ? 'highway'$$,
	  (SELECT id FROM start_pt),
	  (SELECT id FROM end_pt)
	) AS r
	JOIN ways w ON r.edge = w.id
  )
SELECT ST_AsGeoJSON(ST_LineMerge(ST_Collect(geom)))::json AS geometry
FROM route;