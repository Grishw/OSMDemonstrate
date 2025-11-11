from flask import Flask, render_template
from api.ways import ways_bp
from api.routing import routing_bp

app = Flask(__name__)

# Регистрируем blueprint'ы
app.register_blueprint(ways_bp)
app.register_blueprint(routing_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)