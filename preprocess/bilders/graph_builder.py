import numpy as np
import igraph as ig
from preprocess.utils.geo_utils import haversine_meters

def merge_regions(region_data):
    print("[merge] Combining region graphs ...")
    all_nodes, all_edges = {}, []
    for nodes, edges in region_data:
        for nid, lat, lon in nodes:
            all_nodes[int(nid)] = (float(lat), float(lon))
        all_edges.extend(edges)

    node_ids = list(all_nodes.keys())
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    g = ig.Graph(directed=True)
    g.add_vertices(len(node_ids))
    g.vs["id"] = node_ids
    g.vs["lat"] = [all_nodes[n][0] for n in node_ids]
    g.vs["lon"] = [all_nodes[n][1] for n in node_ids]

    edges_ig, weights = [], []
    for u, v, oneway in all_edges:
        if u in id_to_idx and v in id_to_idx:
            lat1, lon1 = all_nodes[u]; lat2, lon2 = all_nodes[v]
            dist = haversine_meters(lat1, lon1, lat2, lon2)
            edges_ig.append((id_to_idx[u], id_to_idx[v]))
            weights.append(dist)
            if oneway in ["no", "false", "0"]:
                edges_ig.append((id_to_idx[v], id_to_idx[u]))
                weights.append(dist)
    g.add_edges(edges_ig)
    g.es["weight"] = weights
    print(f"[merge] Done: {g.vcount()} nodes, {g.ecount()} edges")
    return g

def merge_regions_fast(region_data):
    """
    Ускоренное объединение региональных графов в один igraph.Graph.
    Полностью векторизовано, без циклов Python.
    """
    print("[merge-fast] Combining region graphs ...")

    # === 1️⃣ Собираем все узлы ===
    all_nodes = {}
    for nodes, _ in region_data:
        # nodes: np.array([[id, lat, lon], ...])
        for nid, lat, lon in nodes:
            all_nodes[int(nid)] = (float(lat), float(lon))

    node_ids = np.fromiter(all_nodes.keys(), dtype=np.int64)
    n_nodes = len(node_ids)
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    lats = np.fromiter((all_nodes[n][0] for n in node_ids), dtype=np.float64, count=n_nodes)
    lons = np.fromiter((all_nodes[n][1] for n in node_ids), dtype=np.float64, count=n_nodes)

    # === 2️⃣ Собираем все рёбра ===
    edges_raw = np.concatenate([np.array(edges, dtype=object) for _, edges in region_data])
    u_ids, v_ids, oneways = edges_raw[:, 0].astype(np.int64), edges_raw[:, 1].astype(np.int64), edges_raw[:, 2]

    # фильтруем недействительные рёбра
    valid_mask = np.isin(u_ids, node_ids) & np.isin(v_ids, node_ids)
    u_ids, v_ids, oneways = u_ids[valid_mask], v_ids[valid_mask], oneways[valid_mask]

    # === 3️⃣ Преобразуем ID → индексы
    u_idx = np.vectorize(id_to_idx.get, otypes=[np.int64])(u_ids)
    v_idx = np.vectorize(id_to_idx.get, otypes=[np.int64])(v_ids)

    # === 4️⃣ Векторное вычисление расстояний (через pyproj.Geod.inv)
    lon1, lat1 = lons[u_idx], lats[u_idx]
    lon2, lat2 = lons[v_idx], lats[v_idx]
    distances = haversine_meters(lon1, lat1, lon2, lat2)

    # === 5️⃣ Обработка двусторонних дорог
    rev_mask = np.isin(oneways, ["no", "false", "0"])
    edges_ig = np.column_stack((u_idx, v_idx))
    edges_rev = np.column_stack((v_idx[rev_mask], u_idx[rev_mask]))

    all_edges = np.vstack((edges_ig, edges_rev))
    all_weights = np.concatenate((distances, distances[rev_mask]))

    # === 6️⃣ Создание итогового графа
    g = ig.Graph(directed=True)
    g.add_vertices(n_nodes)
    g.vs["id"] = node_ids.tolist()
    g.vs["lat"] = lats.tolist()
    g.vs["lon"] = lons.tolist()

    g.add_edges(all_edges.tolist())
    g.es["weight"] = all_weights.tolist()

    print(f"[merge] Done: {n_nodes:,} nodes, {len(all_edges):,} edges")
    return g
