import math
import pandas as pd
from .models import Params


def distance_from_center(data):
    data['lat'] = data['coordinates'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
    data['lng'] = data['coordinates'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
    center_lat = 55.753600
    center_lng = 37.621184
    earth_radius_km = 6371

    def haversine(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return earth_radius_km * c

    data['distance_from_center'] = data.apply(
        lambda row: haversine(row['lat'], row['lng'], center_lat, center_lng), axis=1
    )
    return data


def preparams(data: Params):
    tables = {
        'addresses': [],
        'developers': [],
        'offers': [],
        'offers_details': [],
        'realty_details': [],
        'realty_inside': [],
        'realty_outside': [],
    }

    for table_name in tables.keys():
        if hasattr(data, table_name):
            tables[table_name].append(getattr(data, table_name).dict())

    dfs = {table: pd.DataFrame(tables[table]) for table in tables}

    data = dfs["addresses"].merge(dfs["offers"], on='cian_id', how='inner')\
        .merge(dfs["offers_details"], on='cian_id', how='inner')

    tables_to_left_join = [dfs["developers"], dfs["realty_details"],
                           dfs["realty_inside"], dfs["realty_outside"]]
    for table in tables_to_left_join:
        data = data.merge(table, on='cian_id', how='left')

    data = distance_from_center(data)
    return data.iloc[0].to_dict()

