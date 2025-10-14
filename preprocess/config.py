import os

BASE_DIR = "data"
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

OSM_FILES = [
    "data/volga.osm.pbf"
]
# ,"data/central.osm.pbf",

# параметры CRP
CRP_GRID_X = 10
CRP_GRID_Y = 10

USE_NUMPY_CH = False  # переключатель

