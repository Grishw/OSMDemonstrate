from pyproj import Geod
geod = Geod(ellps="WGS84")

def haversine_meters(lat1, lon1, lat2, lon2):
    """Расстояние по эллипсоиду WGS84"""
    az12, az21, dist = geod.inv(lon1, lat1, lon2, lat2)
    return dist
