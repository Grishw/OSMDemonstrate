import numpy as np
import igraph as ig
from .ch_numpy import build_ch_numpy

import numpy as np

def convert_graph_to_numpy(g):
    """
    Преобразует igraph.Graph → numpy-матрицу рёбер (u, v, w).
    Гарантирует типы int64 для индексов и float64 для весов.
    """
    try:
        edges = np.array(g.get_edgelist(), dtype=np.int64)
        weights = np.array(g.es["weight"], dtype=np.float64)
        n_nodes = g.vcount()
        edges_np = np.column_stack((edges, weights))
        return edges_np, n_nodes, None
    except Exception as e:
        print(f"[CH] Conversion error: {e}")
        raise TypeError("Unsupported graph format for CH conversion")


def build_ch_wrapper(g, cache_dir=None, max_iters=2):
    """Построение CH с конвертацией графа в NumPy формат."""
    edges_np, n_nodes, mapping = convert_graph_to_numpy(g)
    ch_data = build_ch_numpy(edges_np, n_nodes, max_iters=max_iters)

    # Сохраняем для отладки
    if cache_dir:
        import os, pickle
        with open(os.path.join(cache_dir, "ch_numpy.pkl"), "wb") as f:
            pickle.dump(ch_data, f)

    return ch_data
