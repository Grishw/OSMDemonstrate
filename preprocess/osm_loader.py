import os, pathlib, numpy as np

def region_name(path):
    return pathlib.Path(path).stem.replace(".osm", "")

def build_region_graph(path, cache_dir):
    import osmium
    class RoadHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes, self.edges = {}, []

        def node(self, n):
            if n.location.valid():
                self.nodes[n.id] = (n.location.lat, n.location.lon)

        def way(self, w):
            if "highway" in w.tags:
                oneway = w.tags.get("oneway", "no")
                node_refs = [n.ref for n in w.nodes]  
                for u, v in zip(node_refs[:-1], node_refs[1:]):
                    self.edges.append((u, v, oneway))

    region = region_name(path)
    npz_path = os.path.join(cache_dir, region, "graph.npz")
    os.makedirs(os.path.join(cache_dir, region), exist_ok=True)

    if os.path.exists(npz_path):
        print(f"[cache] Loading region {region}")
        data = np.load(npz_path, allow_pickle=True)
        return data["nodes"], data["edges"]

    print(f"[pyosmium] Reading {path} ...")
    handler = RoadHandler()
    handler.apply_file(path, locations=True)
    nodes = np.array([[nid, lat, lon] for nid, (lat, lon) in handler.nodes.items()], dtype=object)
    edges = np.array(handler.edges, dtype=object)
    np.savez_compressed(npz_path, nodes=nodes, edges=edges)
    print(f"[cache] Saved region {region}")
    return nodes, edges
