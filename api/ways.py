from flask import Flask, jsonify, render_template
from db import SessionLocal
from models import Way
from sqlalchemy import text

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/ways")
def get_ways():
    session = SessionLocal()
    try:
        result = session.query(
            Way.id,
            text("ST_AsGeoJSON(linestring)::json")
        ).limit(1000)  # можно увеличить или добавить bbox
        features = []
        for row in result:
            features.append({
                "type": "Feature",
                "geometry": row[1],
                "properties": {"id": row[0]}
            })

        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })
    finally:
        session.close()

if __name__ == "__main__":
    app.run(debug=True)
