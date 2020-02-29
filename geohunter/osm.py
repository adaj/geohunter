import pandas as pd
import geopandas as gpd
from shapely.ops import polygonize, linemerge
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

MAP_FEATURES_KEYS = ['aerialway', 'aeroway', 'amenity', 'barrier', 'boundary',
    'admin_level', 'building', 'craft', 'emergency', 'geological', 'highway',
    'sidewalk', 'cycleway', 'busway', 'bicycle_road', 'service', 'historic',
    'landuse', 'leisure', 'man_made', 'military', 'natural', 'office', 'place',
    'power', 'public_transport', 'railway', 'route', 'shop', 'sport', 'telecom',
    'tourism', 'waterway', 'water', 'name']


class API:

    @classmethod
    def get(self, bbox, **map_features):
        """
        Returns points-of-interest data from OpenStreetMap.

        It returns the gpd.GeoDataFrame with a set of points-of-interest
        requested in **map_features. For a list of complete map features keys
        and elements available on the API, please consult documentation
        https://wiki.openstreetmap.org/wiki/Map_Features.

        Example : df = API.get_poi(bbox='(-5.91,-35.29,-5.70,-35.15)',
                    amenity=['hospital','police'], natural='*')

        Parameters
        ----------
        bbox : str or gpd.GeoDataFrame
        If str, follow the structure (south_lat,west_lon,north_lat,east_lon),
        but if you prefer to pass a gpd.GeoDataFrame, the bbox will be
        defined as the maximum and minimum values delimited by the geometry.

        **map_features : poi requested described in map features
        Example: amenity=['hospital', 'police']. See OpenStreetMap docs for
        the map features available.

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with all points-of-interest requested.
        """
        for mf in map_features:
            if mf not in MAP_FEATURES_KEYS:
                raise Exception(f"{mf} is not a valid map feature. Please " \
                    + "consult https://wiki.openstreetmap.org/wiki/Map_Features.")
        poi_data = pd.DataFrame()
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
            for mf_item in map_features[mf_key]:
                result = self.request_overpass(bbox=bbox,
                    map_feature_key=mf_key, map_feature_item=mf_item)
                result_gdf = overpass_result_to_geodf(result)
                result_gdf['mf_key'] = mf_key
                poi_data = poi_data.append(result_gdf)
        poi_data['mf_item'] = poi_data.apply(lambda x: x['tags'][x['mf_key']], axis=1)
        return poi_data

    @classmethod
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
        bbox : str or gpd.GeoDataFrame
        If str, follow the structure (south_lat,west_lon,north_lat,east_lon),
        but if you prefer to pass a gpd.GeoDataFrame, the bbox will be
        defined as the maximum and minimum values delimited by the geometry.

        map_feature_key: str

        map_feature_item: str

        Returns
        -------
        dict
            Data requested in output format of Overpass API.
        """
        bbox = parse_bbox(bbox)
        query_string = ''
        for i in ['node','way','relation']:
            if map_feature_item=='*':
                query_string += f'{i}["{map_feature_key}"]{bbox};'
            else:
                query_string += f'{i}["{map_feature_key}"="{map_feature_item}"]{bbox};'
        query_string = f'[out:json];({query_string});out+geom;'
        result = requests_retry_session().get(\
            f'http://overpass-api.de/api/interpreter?data={query_string}')
        if result.status_code != 200:
            raise Exception("Bad request.")
        result = result.json()
        if len(result['elements'])==0:
            print(query_string)
            raise Exception('Request made with no data returned,' \
                + 'please check try with other parameters.')
        else:
            return result


def requests_retry_session(retries=3, backoff_factor=0.5,
    status_forcelist=(500, 503, 502, 504), session=None):
    # retrieved from https://www.peterbe.com/plog/best-practice-with-retries-with-requests
        session = session or requests.Session()
        retry = Retry(total=retries, read=retries, connect=retries,
            backoff_factor=backoff_factor, status_forcelist=status_forcelist)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session


def overpass_result_to_geodf(result):
    """
    Transforms the result from Overpass request to GeoDataFrame.
    """
    elements_df = pd.DataFrame(result['elements'])
    elements_df['geometry'] = elements_df.apply(parse_geometry, axis=1)
    elements_df = gpd.GeoDataFrame(elements_df, crs={'init': 'epsg:4326'})
    return elements_df[['type','id','tags','geometry']]


def parse_bbox(bbox):
    """
    Organizes the bbox string required into the Overpass request.
    """
    if isinstance(bbox, gpd.GeoDataFrame):
        bounds = bbox.bounds
        bbox={'north':bounds.max().values[3],'east':bounds.max().values[2],
            'south':bounds.min().values[1],'west':bounds.min().values[0]}
        bbox = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
    elif isinstance(bbox, str):
        bbox_ = bbox[1:-1].split(',')
        bbox_ = [float(b) for b in bbox_]
        assert bbox_[0]<bbox_[2] and bbox_[1]<bbox_[3], \
            "Invalid bbox. Please follow this structure: '(S,W,N,E)'"
        bbox = bbox.replace(' ','')
    elif isinstance(bbox, dict):
        assert bbox['south']<bbox['north'] and bbox['west']>bbox['east'], \
            "Invalid bbox. Please include 'south','north','west' and 'east' keys"
        bbox = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
    return bbox


def parse_geometry(x):
    """
    Transforms coordinates into shapely objects.
    """
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


def parse_relation(x_members):
    """
    Transforms coordinates of 'relation' objects into shapely objects.
    """
    if not isinstance(x_members, list):
        return x_members
    shell, holes, lines, points = [], [], [], []
    for x in x_members:
        line = [(p['lon'],p['lat']) for p in x.get("geometry", [])]
        if not line: # empty geometry or it's a node
            if x.get('type', None)=='node':
                points.append((x['lon'],x['lat']))
        elif line[0]==line[-1]: # explicit polygons
            if x['role']=='outer':
                shell.append(line)
            elif x['role']=='inner':
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
        return MultiPolygon([[s,[]] for s in polygons])
    elif shell:
        if len(shell)>1:
            # Here we don't treat multipolygons with multiholes.
            # Who want this, please implement for us :D
            return MultiPolygon([[s,[]] for s in shell])
        else: # single shell
            return Polygon(shell[0], holes)
    elif lines:
        if len(lines)<3:
            # Two lines or less doesn't form a polygon. If
            # there are two lines, these are merged.
            return linemerge(lines)
        else:
            # Lines may not be sequentially organized,
            # so one cannot simply Polygon(lines). Luckily,
            # shapely saved us with shapely.ops.polygonize.
            polygon = list(polygonize(lines))
            if len(polygon)>1:
                return MultiPolygon([[s,[]] for s in polygon])
            else:
                return polygon[0]
    elif points:
        return
