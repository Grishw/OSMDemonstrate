import numpy as np
from concurrent.futures import ThreadPoolExecutor
from itertools import chain

def process_batch(batch_vertices, neighbors, edge_weights, rank):
    local_edges = []
    for v in batch_vertices:
        preds = [u for u in neighbors[v] if rank[u] < rank[v]]
        succs = [w for w in neighbors[v] if rank[w] > rank[v]]
        for u in preds:
            duv = edge_weights.get((u, v))
            if duv is None:
                continue
            for w in succs:
                dvw = edge_weights.get((v, w))
                if dvw is None or w in neighbors[u]:
                    continue
                local_edges.append((u, w, duv + dvw))
    return local_edges

def build_ch(g, max_workers=12, batch_size=1000):
    print(f"[CH] Building Contraction Hierarchy (threads, batch={batch_size})...")

    n = g.vcount()
    degree = np.array(g.degree())
    order = np.argsort(degree)
    rank = np.zeros(n, dtype=np.int32)
    rank[order] = np.arange(n)

    neighbors = [set(g.neighbors(v)) for v in range(n)]
    edge_weights = { (e.source, e.target): e["weight"] for e in g.es }

    batches = [order[i:i + batch_size] for i in range(0, n, batch_size)]

    # --- Параллельная обработка через потоки ---
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(
            lambda batch: process_batch(batch, neighbors, edge_weights, rank),
            batches
        )

    new_edges = list(chain.from_iterable(results))

    if new_edges:
        g.add_edges([(u, w) for u, w, _ in new_edges])
        g.es[-len(new_edges):]["weight"] = [wt for _, _, wt in new_edges]

    print(f"[CH] Added {len(new_edges)} shortcuts.")
    return {"rank": rank.tolist(), "shortcuts": len(new_edges)}
