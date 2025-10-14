# main.py
import time, os
import sys
sys.path.append("./preprocess")

from preprocess.config import OSM_FILES, CACHE_DIR, CRP_GRID_X, CRP_GRID_Y, USE_NUMPY_CH
from preprocess.osm_loader import build_region_graph
from preprocess.bilders.graph_builder import merge_regions, merge_regions_fast
from preprocess.bilders.crp_builder import build_crp
from preprocess.utils.cache_utils import save_pickle

# варианты CH
from preprocess.bilders.ch.ch_builder import build_ch
from preprocess.bilders.ch.ch_wrapper import build_ch_wrapper

if __name__ == "__main__":
    t0 = time.time()
    print("=== Start process ===")

    # загрузка регионов
    region_data = [build_region_graph(p, CACHE_DIR) for p in OSM_FILES]

    # слияние
    g = merge_regions_fast(region_data)
    del region_data

    # построение CH
    if USE_NUMPY_CH:
        ch_data = build_ch_wrapper(g, cache_dir=CACHE_DIR, max_iters=2)
    else:
        ch_data = build_ch(g)
    save_pickle(ch_data, os.path.join(CACHE_DIR, "ch.pkl"))
    print("[cache] Saved Contraction Hierarchy")
    del ch_data

    # построение CRP
    crp_data = build_crp(g, CRP_GRID_X, CRP_GRID_Y)
    save_pickle(crp_data, os.path.join(CACHE_DIR, "crp.pkl"))
    print("[cache] Saved CRP")
    del crp_data
    print(f"=== Done in {time.time()-t0:.1f}s ===")
