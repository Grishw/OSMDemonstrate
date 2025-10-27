from flask import Flask, jsonify, render_template, request
from db import SessionLocal
from sqlalchemy.sql.expression import text
from shapely.geometry import LineString
from shapely.ops import linemerge

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route('/api/ways', methods=['GET'])
def get_ways():
    session = SessionLocal()
    try:
        bbox_param = request.args.get("bbox")
        tag_param = request.args.get("tag")  # например: highway, waterway, railway
        zoom = int(request.args.get("zoom", 12))  # Получаем масштаб карты, дефолт - 12
        lim = 2000

        base_query = """
            SELECT 
                id,
                ST_AsGeoJSON(linestring)::json AS geometry,
                tags
            FROM ways
        """

        conditions = []
        params = {}

        if tag_param:
            conditions.append("tags @> hstore(:tag)")
            params["tag"] = f"{tag_param}"

        if zoom <= 13:
            conditions.append("(tags->'highway') IN ('motorway', 'trunk', 'primary', 'secondary')")
            lim = 4000
        elif zoom <= 10:
            conditions.append("(tags->'highway') IN ('motorway', 'trunk', 'primary')")
            lim = 5000 # увеличиваем лимит для более точной выборки
        if zoom <= 9:
            conditions.append("(tags->'highway') IN ('trunk')")
            lim = 10000 # увеличиваем лимит для более точной выборки
        
        if bbox_param:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox_param.split(","))
                conditions.append("""
                    ST_Intersects(
                        linestring,
                        ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
                    )
                """)
                params.update({
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat
                })
            except:
                pass 

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += f" LIMIT {lim}"  
        result = session.execute(text(base_query), params)

        features = []
        for row in result.mappings():
            features.append({
                "type": "Feature",
                "geometry": row["geometry"],
                "properties": {
                    "id": row["id"],
                    "tags": row["tags"]
                }
            })

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
    finally:
        session.close()

@app.route("/api/route", methods=["POST"])
def get_route():
    data = request.get_json()
    start = data.get("start")
    end = data.get("end")
    print(start, "   ", end)

    if not start or not end:
        return jsonify({"status": "error", "message": "start and end points are required"}), 400

    start_lat, start_lon= start
    end_lat, end_lon = end
    print("s ", start_lon, ",",start_lat)
    print("e ",end_lon, ",",end_lat)

    with SessionLocal() as conn:
         # 1 Находим ближайшие вершины
        get_point_sqltext = text("""
        WITH node_str AS (
            SELECT id
            FROM nodes
            ORDER BY geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
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
        """)
        start_vertex = conn.execute(get_point_sqltext, {"lat": start_lat, "lon": start_lon}).scalar()

        end_vertex = conn.execute(get_point_sqltext, {"lat": end_lat, "lon": end_lon}).scalar()

        if not start_vertex or not end_vertex:
            return jsonify({
                "status": "error",
                "message": "could not find nearest vertices"
            }), 400
        print(start_vertex,"  ", end_vertex)


        # Используем pgr_dijkstra для поиска маршрута
        route_rows = conn.execute(text("""
        SELECT seq, node, edge, rout.cost, ST_AsGeoJSON(ways.linestring)::json AS geometry 
        FROM pgr_dijkstra(
            'SELECT id, source, target, cost, reverse_cost
            FROM ways', -- запрос к графу дорог
            :start_v, -- начало пути
            :end_v, -- конец пути
            directed := false
        ) AS rout
        LEFT JOIN ways
        ON rout.edge = ways.id
        ORDER BY seq
        """), {"start_v": start_vertex, "end_v": end_vertex}).fetchall()

        #print(route_rows)
        if not route_rows:
            return jsonify({"status": "error", "message": "No route found"}), 404

        # Формируем геометрию маршрута из ребер
        
        features = [
            {
                "type": "Feature",
                "geometry": row.geometry,
                "properties": {
                    "seq": row.seq,
                    "node": row.node,
                    "edge": row.edge,
                    "cost": row.cost
                }
            }
            for row in route_rows if row.geometry
        ]

        feature_collection = {
            "type": "FeatureCollection",
            "features": features
        }

        return jsonify({
            "status": "ok",
            "start_vertex": start_vertex,
            "end_vertex": end_vertex,
            "route": feature_collection
        })


if __name__ == "__main__":
    app.run(debug=True)
