import pandas as pd
import geopandas as gpd
import urllib
import json
from shapely.geometry import Point, Polygon, LineString, MultiPolygon


class API():

    def get_poi(self, map_features):
        """
        Returns points-of-interest data retrieved from OpenStreetMap.

        With a dictionary of map features (see https://wiki.openstreetmap.org/wiki/Map_Features),
        it returns a single GeoDataFrame with all the data.

        map_features : dict
            Map features as keys and elements in a list e.g. {'amenity':['hospital','police']}.
            For all elements of a single key, one can use '*' instead of the list of elements.
        """
        return get_poi_gdf(map_features)


def request_overpass(map_feature_key, map_feature_item, bbox):
    if isinstance(bbox, gpd.GeoDataFrame):
        bounds = bbox.bounds
        bbox={'north':bounds.max().values[3],'east':bounds.max().values[2],
            'south':bounds.min().values[1],'west':bounds.min().values[0]}
        bbox = f"({bbox['south']}, {bbox['west']}, {bbox['north']}, {bbox['east']})"
    assert isinstance(bbox, str), "Invalid bbox. Please follow this structure: '(S,W,N,E)'"
    query_string = ''
    for i in ['node','way','relation']:
        if map_feature_item=='*':
            query_string += f'{i}["{map_feature_key}"]{bbox};'
        else:
            query_string += f'{i}["{map_feature_key}"="{map_feature_item}"]{bbox};'
    query_string = f'[out:json][timeout:50];({query_string});out+geom;'.replace(' ','')
    result = urllib.request.urlopen(f'http://overpass-api.de/api/interpreter?data={query_string}').read()
    result = json.loads(result)
    if len(result['elements'])==0:
        raise Exception('Request made with no data returned, please check try with other parameters.')
    else:
        return result


def parse_relation(x_members):
    if isinstance(x_members, list):
        lines = []
        shell = []
        holes = []
        first_prev_line = 0
        for c, x in enumerate(x_members):
            line = [(p['lon'],p['lat']) for p in x['geometry']]
            if c==0 or line[-1]==first_prev_line:
                lines += line[::-1]
                first_prev_line = line[0]
            if line[0]==line[-1]:
                lines = []
                if x['role']=='outer':
                    shell.append(line)
                elif x['role']=='inner':
                    holes.append(line)
        if len(shell)>1:
            return MultiPolygon([[s,[]] for s in shell])
        elif len(shell)==1:
            return Polygon(shell[0], holes)
        else:
            return Polygon(lines)
    else:
        return x_members


def parse_coordinates(x):
    if x['type']=='node':
        g = Point([x['lon'],x['lat']])
    elif x['type']=='way':
        line = [(i['lon'],i['lat']) for i in x['geometry']]
        if line[0]==line[-1]:
            g = Polygon(line)
        else:
            g = LineString(line)
    else: # relation
        g = parse_relation(x['members'])
    return g


def overpass_result_to_geodf(result):
    elements_df = pd.DataFrame(result['elements'])
    elements_df['geometry'] = elements_df.apply(parse_coordinates, axis=1)
    elements_df = gpd.GeoDataFrame(elements_df, crs={'init': 'epsg:4326'})
    return elements_df[['type','id','tags','geometry']]


def get_poi_gdf(map_features, city_shape):
    poi_data = pd.DataFrame()
    for mf_key in map_features:
        if isinstance(map_features[mf_key], list):
            for mf_item in map_features[mf_key]:
                print(mf_key, mf_item)
                result = request_overpass(mf_key,mf_item, city_shape)
                result_gdf = overpass_result_to_geodf(result)
                result_gdf['mf_key'] = mf_key
                result_gdf['mf_item'] = mf_item
                poi_data = poi_data.append(result_gdf)
        elif isinstance(map_features[mf_key], str):
            print(mf_key, map_features[mf_key])
            result = request_overpass(mf_key,map_features[mf_key], city_shape)
            result_gdf = overpass_result_to_geodf(result)
            result_gdf['mf_key'] = mf_key
            result_gdf['mf_item'] = map_features[mf_key]
            poi_data = poi_data.append(result_gdf)
        else:
            raise Exception(f'Map feature {mf_key}:{map_features[mf_key]} not allowed.')
    return poi_data
