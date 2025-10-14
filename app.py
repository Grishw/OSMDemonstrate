from flask import Flask, render_template, request, jsonify
import networkx as nx, numpy as np, pickle, os

CACHE_DIR = "data/cache"

app = Flask(__name__)
_graph=None; _ch_data=None; _crp_data=None

# ----------------- Load Cache -----------------
def load_cache():
    dat = np.load(os.path.join(CACHE_DIR, "volga/graph.npz"), allow_pickle=True)
    nodes, edges = dat["nodes"], dat["edges"]
    print(f"Loaded graph: {len(nodes)} nodes, {len(edges)} edges")

    G = nx.DiGraph()
    for n, lat, lon in nodes:
        G.add_node(int(n), lat=float(lat), lon=float(lon))
    for u, v, w in edges:
        weight = 0
        try:
            weight = float(w)
        except ValueError:
            weight = 1.0
            #print(f"[Warning] пропущено ребро {u}-{v} с некорректным весом: {w}")
        G.add_edge(int(u), int(v), weight=weight)

    with open(os.path.join(CACHE_DIR, "ch.pkl"), "rb") as f:
        ch = pickle.load(f)
    with open(os.path.join(CACHE_DIR, "crp.pkl"), "rb") as f:
        crp = pickle.load(f)

    # проверим, есть ли граф внутри CH/CRP, иначе добавим G
    if "G" not in ch: ch["G"] = G
    if "G" not in crp: crp["G"] = G

    return G, ch, crp

# ----------------- Queries -----------------
def snap_point(G, pt):
    lat, lon = pt
    best, bestd = None, float("inf")
    for n,d in G.nodes(data=True):
        if "lat" not in d or "lon" not in d: continue
        nd = (lat-d["lat"])**2 + (lon-d["lon"])**2
        if nd < bestd:
            bestd, best = nd, n
    return best

def ch_query(ch_data, source, target):
    rank_list = ch_data["rank"]
    Gch = ch_data["G"]
    rank = {n: r for n, r in enumerate(rank_list)}

    Gup = nx.DiGraph()
    for u, v, data in Gch.edges(data=True):
        if rank.get(u,0) <= rank.get(v,0):
            Gup.add_edge(u,v,weight=data["weight"])

    s_node = snap_point(Gch, source)
    t_node = snap_point(Gch, target)
    if s_node is None or t_node is None: return None

    try:
        path = nx.shortest_path(Gup, s_node, t_node, weight="weight")
        return [(Gch.nodes[n]["lat"], Gch.nodes[n]["lon"]) for n in path]
    except:
        return None

def crp_query(crp_data, source, target):
    G = crp_data["G"]
    s_node = snap_point(G, source)
    t_node = snap_point(G, target)
    if s_node is None or t_node is None: return None
    try:
        path = nx.shortest_path(G, s_node, t_node, weight="weight")
        return [(G.nodes[n]["lat"], G.nodes[n]["lon"]) for n in path]
    except:
        return None

# ----------------- Bounding Box -----------------
def get_region_bounds(graph):
    lats = [d["lat"] for _,d in graph.nodes(data=True) if "lat" in d]
    lons = [d["lon"] for _,d in graph.nodes(data=True) if "lon" in d]
    if not lats or not lons: return []

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    return [{
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [min_lon, max_lat],
                [max_lon, max_lat],
                [max_lon, min_lat],
                [min_lon, min_lat]
            ]]
        },
        "properties": {"color": "red"}
    }]

# ----------------- Flask Endpoints -----------------
@app.route("/")
def index(): return render_template("index.html")

@app.route("/regions")
def regions():
    global _graph,_ch_data,_crp_data
    if _graph is None:
        _graph,_ch_data,_crp_data = load_cache()
        print("Cache loaded.")
    features = get_region_bounds(_graph)
    return jsonify({"type":"FeatureCollection","features":features})

@app.route("/route",methods=["POST"])
def route():
    global _graph,_ch_data,_crp_data
    if _graph is None:
        _graph,_ch_data,_crp_data = load_cache()
        print("Cache loaded.")

    data = request.get_json()
    start, end, algo = data.get("start"), data.get("end"), data.get("algo","ch")
    if not start or not end: return jsonify({"error":"start/end required"}),400

    s = (float(start[0]), float(start[1]))
    t = (float(end[0]), float(end[1]))

    coords = None
    if algo=="ch":
        
        coords = ch_query(_ch_data, s, t)
    else:
        coords = crp_query(_crp_data, s, t)
    if not coords: return jsonify({"error":"route not found"}),404

    line = {"type":"Feature",
            "geometry":{"type":"LineString","coordinates":[[lon,lat] for lat,lon in coords]},
            "properties":{"algo":algo}}
    return jsonify(line)

@app.route("/shortcuts")
def shortcuts():
    """Возвращает все шорткаты CH и CRP для визуализации на карте."""
    global _graph, _ch_data, _crp_data
    if _graph is None:
        _graph, _ch_data, _crp_data = load_cache()

    features = []

    # --- CH Shortcuts ---
    Gch = _ch_data["G"]
    rank_list = _ch_data["rank"]
    rank = {n:r for n,r in enumerate(rank_list)}

    for u,v,data in Gch.edges(data=True):
        if rank.get(u,0) <= rank.get(v,0) and data.get("weight") is not None:
            features.append({
                "type":"Feature",
                "geometry":{"type":"LineString",
                            "coordinates":[
                                [Gch.nodes[u]["lon"], Gch.nodes[u]["lat"]],
                                [Gch.nodes[v]["lon"], Gch.nodes[v]["lat"]]
                            ]},
                "properties":{"algo":"ch"}
            })

    # --- CRP Shortcuts ---
    Gcrp = _crp_data["G"]
    for u,v,data in Gcrp.edges(data=True):
        if data.get("weight") is not None:
            features.append({
                "type":"Feature",
                "geometry":{"type":"LineString",
                            "coordinates":[
                                [Gcrp.nodes[u]["lon"], Gcrp.nodes[u]["lat"]],
                                [Gcrp.nodes[v]["lon"], Gcrp.nodes[v]["lat"]]
                            ]},
                "properties":{"algo":"crp"}
            })

    return jsonify({"type":"FeatureCollection","features":features})

if __name__=="__main__":
    app.run(debug=True, port=5000)
