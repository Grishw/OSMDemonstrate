from flask import Flask, jsonify, render_template, request
from db import SessionLocal
from sqlalchemy.sql.expression import text
from shapely.geometry import LineString
from shapely.ops import linemerge

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

# Маршрут для получения данных о компонентах
@app.route('/api/components', methods=['GET'])
def get_components():
    area = request.args.get('area')

    session = SessionLocal()

    # SQL-запрос для получения данных о компонентах
    query = """
        SELECT fix_id, comp_id, nodes
        FROM way_box_component
    """

    if area:
        query += " WHERE fix_id = :area"
        result = session.execute(text(query), {"area": area})
    else:
        result = session.execute(text(query))

    components = []
    for row in result:
        components.append({
            "fix_id": row[0],
            "comp_id": row[1],
            "nodes": row[2]
        })

    session.close()

    return jsonify(components)

# Маршрут для получения данных об областях
@app.route('/api/areas', methods=['GET'])
def get_areas():
    session = SessionLocal()

    # SQL-запрос для получения данных об областях
    query = text("""
        SELECT fix_id, x1, y1, x2, y2
        FROM road_to_fix
    """)

    result = session.execute(query)

    areas = []
    for row in result:
        areas.append({
            "id": row[0],
            "x1": row[1],
            "y1": row[2],
            "x2": row[3],
            "y2": row[4]
        })

    session.close()

    return jsonify(areas)

# Маршрут для создания новой связи
@app.route('/api/create_connection', methods=['POST'])
def create_connection():
    data = request.json
    node1 = data['node1']
    node2 = data['node2']

    session = SessionLocal()

    # SQL-запрос для создания новой связи
    query = """
        INSERT INTO ways (tags, nodes, linestring, source, target, cost, reverse_cost)
        VALUES (:tags, :nodes, :linestring, :source, :target, :cost, :reverse_cost)
        RETURNING id
    """

    # Создание геометрии линии
    linestring = f"ST_SetSRID(ST_MakeLine((SELECT geom FROM nodes WHERE node_id = {node1}), (SELECT geom FROM nodes WHERE node_id = {node2})), 4326)"

    result = session.execute(text(query), {
        "tags": '{"highway"=>"new_connection"}',
        "nodes": [node1, node2],
        "linestring": linestring,
        "source": node1,
        "target": node2,
        "cost": 1.0,
        "reverse_cost": 1.0
    })

    new_way_id = result.fetchone()[0]

    session.commit()
    session.close()

    return jsonify({"message": "Connection created successfully", "way_id": new_way_id}), 201

if __name__ == '__main__':
    app.run(debug=True)