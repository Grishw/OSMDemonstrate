import numpy as np

def build_crp(g, nx_cells, ny_cells):
    print("[CRP] Building overlay ...")
    lats = np.array(g.vs["lat"])
    lons = np.array(g.vs["lon"])
    minlat, maxlat = np.min(lats), np.max(lats)
    minlon, maxlon = np.min(lons), np.max(lons)

    def cell_of(lat, lon):
        ix = int(((lon - minlon) / (maxlon - minlon + 1e-12)) * nx_cells)
        iy = int(((lat - minlat) / (maxlat - minlat + 1e-12)) * ny_cells)
        return (max(0, min(nx_cells-1, ix)), max(0, min(ny_cells-1, iy)))

    g.vs["cell"] = [cell_of(lat, lon) for lat, lon in zip(lats, lons)]
    boundary = set()
    for e in g.es:
        u, v = e.tuple
        if g.vs[u]["cell"] != g.vs[v]["cell"]:
            boundary.add(u); boundary.add(v)
    overlay = g.subgraph(list(boundary))
    print(f"[CRP] Overlay size: {overlay.vcount()} nodes")
    return {"boundary_nodes": list(boundary), "overlay": overlay}
