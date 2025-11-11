from flask import Blueprint, request, jsonify
from db import SessionLocal
from sqlalchemy.sql.expression import text
import logging

routing_bp = Blueprint('routing', __name__)

def find_nearest_vertices(session, start_lon, start_lat, end_lon, end_lat):
    """Находит ближайшие вершины графа к указанным координатам"""
    query = """
    WITH start_point AS (
        SELECT id FROM routing_graph_vertices_pgr 
        ORDER BY the_geom <-> ST_SetSRID(ST_Point(:start_lon, :start_lat), 4326)
        LIMIT 1
    ),
    end_point AS (
        SELECT id FROM routing_graph_vertices_pgr 
        ORDER BY the_geom <-> ST_SetSRID(ST_Point(:end_lon, :end_lat), 4326)
        LIMIT 1
    )
    SELECT 
        (SELECT id FROM start_point) as start_id,
        (SELECT id FROM end_point) as end_id
    """
    
    result = session.execute(text(query), {
        'start_lon': start_lon, 'start_lat': start_lat,
        'end_lon': end_lon, 'end_lat': end_lat
    }).fetchone()
    
    return result

def create_temporary_connections(session, start_id, end_id):
    """Создает временные соединения от точек до дорожной сети"""
    query = """
    CREATE TEMPORARY TABLE temp_route_points ON COMMIT DROP AS
    SELECT 
        :start_id as start_id,
        (SELECT geom FROM nodes WHERE id = :start_id) as start_geom,
        :end_id as end_id,
        (SELECT geom FROM nodes WHERE id = :end_id) as end_geom;

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
    """
    
    session.execute(text(query), {
        'start_id': start_id, 
        'end_id': end_id
    })

def calculate_route(session, start_id, end_id):
    """Строит маршрут между вершинами"""
    query = """
    WITH route AS (
        SELECT *
        FROM pgr_dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM routing_graph_fixed',
            :start_id, :end_id, true
        )
    )
    SELECT 
        r.seq,
        r.node,
        r.edge,
        r.cost,
        r.agg_cost,
        rg.name,
        rg.highway,
        ST_AsGeoJSON(rg.geom)::json as geometry
    FROM route r
    LEFT JOIN routing_graph_fixed rg ON r.edge = rg.id
    WHERE r.edge > 0
    ORDER BY r.seq
    """
    
    return session.execute(text(query), {
        'start_id': start_id,
        'end_id': end_id
    })

def get_vertex_geometry(session, vertex_id):
    """Возвращает геометрию вершины"""
    query = "SELECT ST_AsGeoJSON(the_geom)::json as geometry FROM routing_graph_vertices_pgr WHERE id = :vertex_id"
    result = session.execute(text(query), {'vertex_id': vertex_id}).fetchone()
    return result.geometry if result else None

@routing_bp.route("/api/route", methods=["POST"])
def calculate_route_endpoint():
    session = SessionLocal()
    try:
        data = request.get_json()
        start_coords = data.get('start')
        end_coords = data.get('end')
        
        if not start_coords or not end_coords:
            return jsonify({"status": "error", "message": "Не указаны начальная или конечная точка"})
        
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        
        # Используем транзакцию
        session.begin()
        
        try:
            # 1. Находим ближайшие вершины
            vertices = find_nearest_vertices(session, start_lon, start_lat, end_lon, end_lat)
            
            if not vertices or not vertices.start_id or not vertices.end_id:
                session.rollback()
                return jsonify({"status": "error", "message": "Не удалось найти ближайшие вершины графа"})
            
            start_id = vertices.start_id
            end_id = vertices.end_id
            
            # 2. Создаем временные соединения
            create_temporary_connections(session, start_id, end_id)
            
            # 3. Строим маршрут
            route_result = calculate_route(session, start_id, end_id)
            route_segments = list(route_result.mappings())
            
            if not route_segments:
                session.rollback()
                return jsonify({"status": "error", "message": "Маршрут не найден"})
            
            # 4. Формируем ответ
            features = []
            
            # Точки начала и конца дорожной сети
            start_geom = get_vertex_geometry(session, start_id)
            if start_geom:
                features.append({
                    "type": "Feature",
                    "geometry": start_geom,
                    "properties": {"type": "start_point"}
                })
            
            end_geom = get_vertex_geometry(session, end_id)
            if end_geom:
                features.append({
                    "type": "Feature", 
                    "geometry": end_geom,
                    "properties": {"type": "end_point"}
                })
            
            # Сегменты маршрута
            for segment in route_segments:
                if segment.geometry:
                    features.append({
                        "type": "Feature",
                        "geometry": segment.geometry,
                        "properties": {
                            "seq": segment.seq,
                            "name": segment.name,
                            "highway": segment.highway,
                            "cost": float(segment.cost),
                            "total_cost": float(segment.agg_cost)
                        }
                    })
            
            session.rollback()
            
            return jsonify({
                "status": "ok",
                "route": {
                    "type": "FeatureCollection",
                    "features": features
                },
                "summary": {
                    "total_segments": len(route_segments),
                    "total_cost": float(route_segments[-1].agg_cost) if route_segments else 0
                }
            })
            
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при построении маршрута: {str(e)}")
            return jsonify({"status": "error", "message": f"Ошибка сервера: {str(e)}"})
            
    except Exception as e:
        session.rollback()
        logging.error(f"Общая ошибка: {str(e)}")
        return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"})
    finally:
        session.close()