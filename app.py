from flask import Flask, jsonify, render_template, request
from db import SessionLocal
from models.models import Way
from sqlalchemy import text

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
            conditions.append("tags LIKE :tag")
            params["tag"] = f"\"{tag_param}\""

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
    print(start)

    
    if not start or not end:
        return jsonify({
            "status": "error",
            "message": "start and end required"
        }), 400

    start_lat, start_lon = start
    end_lat, end_lon = end

    with SessionLocal() as conn:
         # 1 Находим ближайшие вершины
        start_vertex = conn.execute(text("""
            SELECT id
            FROM ways_vertices_pgr
            ORDER BY geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
            LIMIT 1
        """), {"lat": start_lat, "lon": start_lon}).scalar()

        end_vertex = conn.execute(text("""
            SELECT id
            FROM ways_vertices_pgr
            ORDER BY geom <-> ST_SetSRID(ST_Point(:lon, :lat), 4326)
            LIMIT 1
        """), {"lat": end_lat, "lon": end_lon}).scalar()

        if not start_vertex or not end_vertex:
            return jsonify({
                "status": "error",
                "message": "could not find nearest vertices"
            }), 400

        # 2 Запрос маршрута через pgr_astar
        route_rows = conn.execute(text("""
            SELECT seq, node, edge, cost
            FROM pgr_astar(
                'SELECT id, source, target, cost, ST_X(ST_StartPoint(linestring)) AS x1,
                        ST_Y(ST_StartPoint(linestring)) AS y1,
                        ST_X(ST_EndPoint(linestring)) AS x2,
                        ST_Y(ST_EndPoint(linestring)) AS y2
                 FROM ways',
                :start_v, :end_v,
                directed := false
            )
            WHERE edge <> -1;
        """), {"start_v": start_vertex, "end_v": end_vertex}).fetchall()

            if not route_rows:
                return jsonify({"status": "error", "message": "No route found"}), 404

            # Формируем геометрию маршрута из ребер
            edges = []
            for row in route_rows:
                edge_row = conn.query(Ways.linestring).filter(Ways.id == row.edge).one_or_none()
                if edge_row is not None:
                    edges.append(to_shape(edge_row.linestring))

            from shapely.ops import linemerge
            merged_geometry = linemerge(edges)

            # Возвращаем JSON с результатами
            return jsonify({
                "status": "ok",
                "geometry": merged_geometry.wkt,
                "message": None
            })

if __name__ == "__main__":
    app.run(debug=True)
