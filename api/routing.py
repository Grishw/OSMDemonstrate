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
    """Создает временные соединения от точек до дорожной сети с длиной"""
    query = """
    CREATE TEMPORARY TABLE temp_route_points ON COMMIT DROP AS
    SELECT 
        :start_id as start_id,
        (SELECT geom FROM nodes WHERE id = :start_id) as start_geom,
        :end_id as end_id,
        (SELECT geom FROM nodes WHERE id = :end_id) as end_geom;

    INSERT INTO routing_graph_fixed_1  (id, source, target, cost, reverse_cost, length_m, geom)
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
    """Строит маршрут между вершинами с дополнительной информацией"""
    query = """
    WITH route AS (
        SELECT *
        FROM pgr_dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM routing_graph_fixed_1 ',
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
        rg.length_m,
        ST_AsGeoJSON(rg.geom)::json as geometry
    FROM route r
    LEFT JOIN routing_graph_fixed_1  rg ON r.edge = rg.id
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
    print("---start дейкстра---")
    session = SessionLocal()
    try:
        data = request.get_json()
        start_coords = data.get('start')
        end_coords = data.get('end')
        
        if not start_coords or not end_coords:
            return jsonify({"status": "error", "message": "Не указаны начальная или конечная точка"})
        
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        
        # Замеряем время выполнения на сервере
        import time
        start_time = time.time()
        
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
            total_distance = 0
            
            # Точки начала и конца дорожной сети
            start_geom = get_vertex_geometry(session, start_id)
            if start_geom:
                features.append({
                    "type": "Feature",
                    "geometry": start_geom,
                    "properties": {"type": "start_point", "algorithm": "Dijkstra"}
                })
            
            end_geom = get_vertex_geometry(session, end_id)
            if end_geom:
                features.append({
                    "type": "Feature", 
                    "geometry": end_geom,
                    "properties": {"type": "end_point", "algorithm": "Dijkstra"}
                })
            
            # Сегменты маршрута и расчет общей длины
            for segment in route_segments:
                if segment.geometry:
                    # Получаем длину сегмента из базы данных
                    segment_length = 0
                    if hasattr(segment, 'length_m') and segment.length_m:
                        segment_length = float(segment.length_m)
                    elif hasattr(segment, 'cost') and segment.cost:
                        # Если длины нет, используем cost как приблизительную длину
                        segment_length = float(segment.cost) * 1000  # примерное преобразование
                    
                    total_distance += segment_length
                    
                    features.append({
                        "type": "Feature",
                        "geometry": segment.geometry,
                        "properties": {
                            "seq": segment.seq,
                            "name": segment.name,
                            "highway": segment.highway,
                            "cost": float(segment.cost),
                            "total_cost": float(segment.agg_cost),
                            "length_m": segment_length,
                            "algorithm": "Dijkstra"
                        }
                    })
            
            server_execution_time = time.time() - start_time
            
            session.rollback()
            
            return jsonify({
                "status": "ok",
                "route": {
                    "type": "FeatureCollection",
                    "features": features
                },
                "summary": {
                    "total_segments": len(route_segments),
                    "total_cost": float(route_segments[-1].agg_cost) if route_segments else 0,
                    "total_distance": total_distance,
                    "execution_time": server_execution_time,
                    "algorithm": "Dijkstra"
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

def create_temporary_connections_astar(session, start_id, end_id):
    """Создает временные соединения от точек до дорожной сети с координатами для A*"""
    query = """
    CREATE TEMPORARY TABLE temp_route_points ON COMMIT DROP AS
    SELECT 
        :start_id as start_id,
        (SELECT geom FROM nodes WHERE id = :start_id) as start_geom,
        :end_id as end_id,
        (SELECT geom FROM nodes WHERE id = :end_id) as end_geom;

    INSERT INTO routing_graph_fixed_1 (id, source, target, cost, reverse_cost, length_m, geom, x1, y1, x2, y2)
    SELECT 
        nextval('routing_graph_id_seq'),
        trp.start_id,
        (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1),
        0, 0,
        ST_Distance(trp.start_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1)::geography),
        ST_MakeLine(trp.start_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1)),
        ST_X(trp.start_geom),
        ST_Y(trp.start_geom),
        ST_X((SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1)),
        ST_Y((SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.start_geom LIMIT 1))
    FROM temp_route_points trp

    UNION ALL

    SELECT 
        nextval('routing_graph_id_seq'),
        trp.end_id,
        (SELECT id FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1),
        0, 0,
        ST_Distance(trp.end_geom::geography, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1)::geography),
        ST_MakeLine(trp.end_geom, (SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1)),
        ST_X(trp.end_geom),
        ST_Y(trp.end_geom),
        ST_X((SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1)),
        ST_Y((SELECT the_geom FROM routing_graph_vertices_pgr WHERE cnt > 0 ORDER BY the_geom <-> trp.end_geom LIMIT 1))
    FROM temp_route_points trp;
    """
    
    session.execute(text(query), {
        'start_id': start_id, 
        'end_id': end_id
    })

def calculate_route_astar(session, start_id, end_id):
    """Строит маршрут между вершинами с использованием A*"""
    query = """
    WITH route AS (
        SELECT *
        FROM pgr_astar(
            'SELECT id, source, target, cost, reverse_cost, x1, y1, x2, y2 FROM routing_graph_fixed_1',
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
    LEFT JOIN routing_graph_fixed_1 rg ON r.edge = rg.id
    WHERE r.edge > 0
    ORDER BY r.seq
    """
    
    return session.execute(text(query), {
        'start_id': start_id,
        'end_id': end_id
    })

@routing_bp.route("/api/route/astar", methods=["POST"])
def calculate_route_astar_endpoint():
    print("---start astar---")
    session = SessionLocal()
    try:
        data = request.get_json()
        start_coords = data.get('start')
        end_coords = data.get('end')
        
        if not start_coords or not end_coords:
            return jsonify({"status": "error", "message": "Не указаны начальная или конечная точка"})
        
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        
        # Замеряем время выполнения на сервере
        import time
        start_time = time.time()
        
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
            create_temporary_connections_astar(session, start_id, end_id)
            
            # 3. Строим маршрут с использованием A*
            route_result = calculate_route_astar(session, start_id, end_id)
            route_segments = list(route_result.mappings())
            
            if not route_segments:
                session.rollback()
                return jsonify({"status": "error", "message": "Маршрут не найден"})
            
            # 4. Формируем ответ
            features = []
            total_distance = 0
            
            # Точки начала и конца дорожной сети
            start_geom = get_vertex_geometry(session, start_id)
            if start_geom:
                features.append({
                    "type": "Feature",
                    "geometry": start_geom,
                    "properties": {"type": "start_point", "algorithm": "A*"}
                })
            
            end_geom = get_vertex_geometry(session, end_id)
            if end_geom:
                features.append({
                    "type": "Feature", 
                    "geometry": end_geom,
                    "properties": {"type": "end_point", "algorithm": "A*"}
                })
            
            # Сегменты маршрута и расчет общей длины
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
                            "total_cost": float(segment.agg_cost),
                            "algorithm": "A*"
                        }
                    })
                    # Суммируем длину сегментов
                    if hasattr(segment, 'length_m') and segment.length_m:
                        total_distance += float(segment.length_m)
            
            server_execution_time = time.time() - start_time
            
            session.rollback()
            
            return jsonify({
                "status": "ok",
                "route": {
                    "type": "FeatureCollection",
                    "features": features
                },
                "summary": {
                    "total_segments": len(route_segments),
                    "total_cost": float(route_segments[-1].agg_cost) if route_segments else 0,
                    "total_distance": total_distance,
                    "execution_time": server_execution_time,
                    "algorithm": "A*"
                }
            })
            
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при построении маршрута A*: {str(e)}")
            return jsonify({"status": "error", "message": f"Ошибка сервера: {str(e)}"})
            
    except Exception as e:
        session.rollback()
        logging.error(f"Общая ошибка A*: {str(e)}")
        return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"})
    finally:
        session.close()
