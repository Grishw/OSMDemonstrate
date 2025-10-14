import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse import csr_matrix, csc_matrix, vstack

def build_ch_numpy(edges, n_nodes, max_iters=3):
    """
    Быстрая реализация Contraction Hierarchy (CH) на основе NumPy + SciPy.
    
    edges: np.ndarray [[u, v, weight], ...]
    n_nodes: int
    max_iters: количество итераций схлопывания (можно увеличить для точности)

    Возвращает:
      {
        "A": csr_matrix - итоговая матрица графа,
        "rank": np.ndarray[int] - ранги вершин,
        "shortcuts": int - количество добавленных рёбер
      }
    """

    print(f"[CH] Building Contraction Hierarchy (NumPy, n={n_nodes}, m={len(edges)})")
    u = edges[:, 0].astype(np.int64)
    v = edges[:, 1].astype(np.int64)
    w = edges[:, 2].astype(np.float64)

    # Строим LIL-матрицу (быстрое добавление)
    A = lil_matrix((n_nodes, n_nodes), dtype=np.float64)
    for u, v, w in edges:
        A[u, v] = min(A[u, v] or np.inf, w)  # если есть, берём минимальный вес

    # Вычисляем степени
    deg = np.array((A > 0).sum(axis=1)).ravel()
    order = np.argsort(deg)     # упрощённый порядок схлопывания
    rank = np.zeros_like(order)
    rank[order] = np.arange(n_nodes)

    total_shortcuts = 0

    for it in range(max_iters):
        print(f"[CH] Iteration {it+1}/{max_iters}")
        added = 0

        for v in order:
            # Соседи v
            preds = A[:, v].nonzero()[0]
            succs = A[v, :].nonzero()[1]

            if len(preds) == 0 or len(succs) == 0:
                continue

            # Вычисляем все комбинации u→v→w через broadcasting
            duv = np.array(A[preds, v]).ravel()
            dvw = np.array(A[v, succs]).ravel()

            # Создаём все пары u→w и длины новых шорткатов
            new_u = np.repeat(preds, len(succs))
            new_w = np.tile(succs, len(preds))
            new_dist = np.repeat(duv, len(succs)) + np.tile(dvw, len(preds))

            # Добавляем, если ребра (u,w) нет или вес хуже
            for u, w, d in zip(new_u, new_w, new_dist):
                if u == w:
                    continue
                existing = A[u, w]
                if existing == 0 or d < existing:
                    A[u, w] = d
                    added += 1

        total_shortcuts += added
        print(f"[CH] +{added} shortcuts (total={total_shortcuts})")

        # Опционально: можно останавливать по порогу
        if added == 0:
            break

    # Преобразуем в CSR для компактности и быстрого использования
    A = A.tocsr()
    print(f"[CH] Done. Total shortcuts added: {total_shortcuts}")

    return {"A": A, "rank": rank, "shortcuts": total_shortcuts}
