"""geohunter.osm

This module wraps requests to OpenStreetMap's Overpass API with an interface for
the GeoPandas data structures. The OpenStreetMap has a data model based on nodes,
ways and relations. The geometric data structures available in geopandas are points,
lines and polygons (but also multipoints, multilines and multipolygons).

For a complete list of data categories available ("map features"), please
look the OpenStreetMap.
"""

from time import time, sleep
from pandas import DataFrame, json_normalize
from geopandas import GeoDataFrame, sjoin
from shapely.ops import polygonize, linemerge
from shapely.geometry import Point, Polygon, LineString
from shapely.geometry import MultiPolygon, MultiPoint
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import geohunter.util

MAP_FEATURES_KEYS = ['aerialway', 'aeroway', 'amenity', 'barrier', 'boundary',
                     'admin_level', 'building', 'craft', 'emergency',
                     'geological', 'highway', 'sidewalk', 'cycleway', 'busway',
                     'bicycle_road', 'service', 'historic', 'landuse',
                     'leisure', 'man_made', 'military', 'natural', 'office',
                     'place', 'power', 'public_transport', 'railway', 'route',
                     'shop', 'sport', 'telecom', 'tourism', 'waterway',
                     'water', 'name', 'healthcare']


def timelog(func):
    def wrapper(data_func, *args, **kwargs):
        t0 = time()
        result = func(data_func, *args, **kwargs)
        tf = time()
        print(f"Geohunter: [TIMELOG] {func.__name__} -- {kwargs} -- Completed in {round(tf - t0, 4)}s")
        return result
    return wrapper


class Eagle:
    """
    `Eagle` is the facade for requesting data given the map
    keys available with the `request_overpass()` method. This class also
    implements a `get()` method which return the data required in a single
    pandas DataFrame that has a geometric attribute that makes it a geopandas
    GeoDataFrame (please consult geopandas documentation for more details).
    """

    def __init__(self):
        self.session = requests_retry_session()

    def __enter__(self):
        return self

    @timelog
    def get(self, bbox, as_points=False,
            largest_geom=False, sjoin_op='intersects',
            **map_features):
        """Returns points-of-interest data from OpenStreetMap.
        as geopandas.GeoDataFrame with a set of points-of-interest
        requested. For a list of complete map features keys
        and elements available on the API, please consult documentation
        https://wiki.openstreetmap.org/wiki/Map_Features.

        Parameters
        ----------
        bbox : str or geopandas.GeoDataFrame
            If str, follow the structure (south_lat,west_lon,north_lat,east_lon),
            but if you prefer to pass a geopandas.GeoDataFrame, the bbox will be
            defined as the maximum and minimum values delimited by the geometry.

        **map_features : **kwargs
            requested described in map features.
            Example: amenity=['hospital', 'police'].

        Returns
        -------
        geopandas.GeoDataFrame
            GeoDataFrame with all points-of-interest requested.

        Example
        -------
        >>> df = Eagle().get(bbox='(-5.91,-35.29,-5.70,-35.15)',
                    amenity=['hospital' , 'police'], natural='*')
        """
        for map_feature in map_features:
            if map_feature not in MAP_FEATURES_KEYS:
                raise Exception(f"{map_feature} is not a valid map feature. Please " \
                    + "consult https://wiki.openstreetmap.org/wiki/Map_Features.")
        poi_data = DataFrame()
        for mf_key in map_features:
            if isinstance(map_features[mf_key], list):
                pass
            elif isinstance(map_features[mf_key], str):
                map_features[mf_key] = [map_features[mf_key]]
            elif isinstance(map_features[mf_key], int):
                map_features[mf_key] = [str(map_features[mf_key])]
            else:
                raise Exception(f'Map feature {mf_key}={map_features[mf_key]}. ' \
                    + 'Please consult https://wiki.openstreetmap.org/wiki/Map_Features.')
            if mf_key == 'admin_level' and sjoin_op == 'intersects':
                if not isinstance(bbox, GeoDataFrame):
                    raise ValueError("To get admin_level geometries, it's " \
                        + 'required to have bbox as a GeoDataframe.')
                else:
                    # forcing 'within' to get admin_level inside a geometry,
                    #  intersection could get undesired neighbor regions
                    sjoin_op = 'within'
            for mf_item in map_features[mf_key]:
                print(f'Requesting {mf_key}={mf_item}')
                result = self.request_overpass(bbox,
                                              map_feature_key=mf_key,
                                              map_feature_item=mf_item)
                print('Done. Wait for 15s to start the next request.')
                sleep(15)
                result_gdf = overpass_result_to_geodf(result, as_points)
                result_gdf['key'] = mf_key
                poi_data = poi_data.append(result_gdf)
        poi_data['item'] = poi_data.apply(lambda x: x['tags'][x['key']], axis=1)
        poi_data = poi_data.reset_index(drop=True)
        poi_data['name'] = json_normalize(poi_data['tags'])['name']
        poi_data = GeoDataFrame(poi_data)
        if isinstance(bbox, GeoDataFrame):
            poi_ix = sjoin(poi_data, bbox, op=sjoin_op).index.unique()
            poi_data = poi_data.loc[poi_ix]
        if largest_geom:
            return poi_data.iloc[[poi_data['geometry'].area.argmax()]]
        return poi_data

    def request_overpass(self, bbox, map_feature_key, map_feature_item):
        """
        Return the json resulted from *a single* request on Overpass API.

        It generates the Overpass QL query from the map features
        defined, including nodes, ways and relations, and request
        data from the API. Please consult OpenStreetMap documentation
        (https://wiki.openstreetmap.org/wiki/Map_Features) for a full
        list of map features available.

        Parameters
        ----------
        bbox : str or geopandas.GeoDataFrame
            If str, follow the structure (south_lat,west_lon,north_lat,east_lon),
            but if you prefer to pass a geopandas.GeoDataFrame, the bbox will be
            defined as the maximum and minimum values delimited by the geometry.

        map_feature_key: str
            Map key item from OpenStreetMap, such as "amenity", "highway" etc.

        map_feature_item: str

        Returns
        -------
        dict
            Data requested in output format of Overpass API.
        """
        bbox = geohunter.util.parse_bbox(bbox)
        query_string = ''
        for i in ['node', 'way', 'relation']:
            if map_feature_item == '*':
                query_string += f'{i}["{map_feature_key}"]{bbox};'
            else:
                query_string += f'{i}["{map_feature_key}"="{map_feature_item}"]{bbox};'
        query_string = f'[out:json];({query_string});out+geom;'
        result = self.session.get(
            f'http://overpass-api.de/api/interpreter?data={query_string}')
        if result.status_code != 200:
            if result.status_code == 429:
                raise Exception('Too many requests. Please wait a couple minutes to retry.')
            raise Exception(f"HTTP {result.status_code}, error.")
        result = result.json()
        if len(result['elements']) == 0:
            print(query_string)
            raise Exception('Request made with no data returned , ' \
                + 'please check try with other parameters.')
        return result

    def debug__find_geom_not_being_successfully_parsed(self, bbox, key, item):
        failed = self.request_overpass(bbox,
                      map_feature_key=key,
                      map_feature_item=item)
        elements_df = DataFrame(failed['elements'])
        for i in elements_df.iterrows():
            try:
                parse_geometry(i[1])
            except:
                print(f'{key}={item} id#{i[0]}')
                return i[1]

    def close(self):
        self.session.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def requests_retry_session(retries=3, backoff_factor=0.5, session=None,
                           status_forcelist=(500, 503, 502, 504)):
    session = session or Session()
    retry = Retry(total=retries, read=retries, connect=retries,
                  backoff_factor=backoff_factor, status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def overpass_result_to_geodf(result, as_points=False):
    """
    Transforms the result from Overpass request to GeoDataFrame.
    """
    elements_df = DataFrame(result['elements'])
    elements_df['geometry'] = elements_df.apply(parse_geometry, axis=1)
    elements_df = GeoDataFrame(elements_df, crs={'init': 'epsg:4326'})
    if as_points:
        elements_df['geometry'] = elements_df['geometry'].centroid
    return elements_df[['type', 'id', 'tags', 'geometry']]


def parse_geometry(x_elements_df):
    """
    Transforms coordinates into shapely objects.
    """
    if x_elements_df['type'] == 'node':
        geom = Point([x_elements_df['lon'], x_elements_df['lat']])
    elif x_elements_df['type'] == 'way':
        line = [(i['lon'], i['lat']) for i in x_elements_df['geometry']]
        if line[0] == line[-1]:
            geom = Polygon(line)
        else:
            geom = LineString(line)
    else: # relation
        geom = parse_relation(x_elements_df['members'])
    return geom


def parse_relation(x_members):
    """
    Transforms coordinates of 'relation' objects into shapely objects.
    """
    if not isinstance(x_members, list):
        return x_members
    shell, holes, lines, points = [], [], [], []
    # Iterating through all geometries inside an element of the
    # Overpass relation ouput, which often are composed by
    # many internal geometries. For example, some polygons are formed with
    # sets of lines, sometimes unordered.
    for x_m in x_members:
        line = [(p['lon'], p['lat']) for p in x_m.get("geometry", [])]
        if not line: # empty geometry or it's a node
            if x_m.get('type', None) == 'node':
                points.append((x_m['lon'], x_m['lat']))
        elif line[0] == line[-1]: # explicit polygons
            if x_m['role'] == 'outer':
                shell.append(line)
            elif x_m['role'] == 'inner':
                holes.append(line)
        else: # these may be lines or a polygon formed by lines
            lines.append(LineString(line))
    # We chose to return in order of priority (1) members that
    # have both shell and lines, then those that have only
    # shell, then members that are formed by lines, and if
    # there aren't shells or lines and the member is formed
    # by a node/point, then it's returned.
    if shell and lines:
        polygons = shell + list(polygonize(lines))
        final_geom = MultiPolygon([[s, []] for s in polygons])
    elif shell:
        if len(shell) > 1:
            # Here we don't treat multipolygons with multiholes.
            # Who want this, please implement for us :D
            final_geom = MultiPolygon([[s, []] for s in shell])
        else:
            final_geom = Polygon(shell[0], holes)
    elif lines:
        if len(lines) < 3:
            # Two lines or less doesn't form a polygon. If
            # there are two lines, these are merged.
            final_geom = linemerge(lines)
        else:
            # Lines may not be sequentially organized,
            # so one cannot simply Polygon(lines). Luckily,
            # shapely saved us with shapely.ops.polygonize.
            polygon = list(polygonize(lines))
            if len(polygon) > 1:
                final_geom = MultiPolygon([s for s in polygon])
            else:
                final_geom = polygon[0]
    elif points:
        if len(points) > 1:
            final_geom = MultiPoint(points)
        else:
            final_geom = Point(points[0])
    else:
        print(x_members)
        print('Relation not correctly parsed. Report this in error in the repository.')
        return Point([0,0])
    return final_geom
