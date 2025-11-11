from flask import Blueprint, request, jsonify
from db import SessionLocal
from sqlalchemy.sql.expression import text

ways_bp = Blueprint('ways', __name__)

@ways_bp.route('/api/ways', methods=['GET'])
def get_ways():
    session = SessionLocal()
    try:
        bbox_param = request.args.get("bbox")
        zoom = int(request.args.get("zoom", 12))
        
        base_query = """
            SELECT 
                id,
                ST_AsGeoJSON(geom)::json AS geometry
            FROM routing_graph_fixed_1
        """

        conditions = []
        params = {}

        if bbox_param:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox_param.split(","))
                conditions.append("""
                    ST_Intersects(
                        geom,
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

        base_query += " LIMIT 5000"
        result = session.execute(text(base_query), params)

        features = []
        for row in result.mappings():
            features.append({
                "type": "Feature",
                "geometry": row["geometry"],
                "properties": {
                    "id": row["id"],
                }
            })

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
    finally:
        session.close()