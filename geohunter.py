# import json
import urllib
import fiona, shapely
import pandas as pd
import numpy as np
import geopandas as gpd
import os
import json
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import KFold, GridSearchCV


def make_grid(bbox, resolution=0.5):
    nlon = int(np.ceil((bbox['east']- bbox['west'])/(resolution/111.32)))
    nlat = int(np.ceil((bbox['north']- bbox['south'])/(resolution/110.57)))
    lon = np.linspace(float(bbox['west']), float(bbox['east']), nlon)
    lat = np.linspace(float(bbox['south']), float(bbox['north']), nlat)
    lonv, latv = np.meshgrid(lon,lat)
    grid = np.vstack([lonv.ravel(), latv.ravel()]).T
    grid = gpd.GeoDataFrame(grid, geometry=[shapely.geometry.Point(xy) for xy in grid],crs={'init': 'epsg:4326'})
    grid.rename(columns={0:'lon',1:'lat'}, inplace=True)
    return grid, lonv, latv

def gridsearch_kde_params(points, n_samples=None):
    if n_samples is None:
        n_samples = points.shape[0]
    pgrid = {'bandwidth': np.logspace(-1, -5, 10),
             'kernel':['gaussian','linear','exponential','tophat'],
             'metric':['haversine']}
    gscv = GridSearchCV(KernelDensity(), pgrid,
                        cv=5, n_jobs=-1, iid=False)
    gscv.fit(points[['lon','lat']].sample(int(n_samples),random_state=0));
    return gscv.best_params_

def overpass_get_points_by_key(folder, bbox, key, item): #keys: 'amenity', 'building', 'highway', 'tourism', 'historic'
    if "OSM_points_{}-{}".format(key, item) in os.listdir(folder):
        return gpd.read_file("{}/OSM_points_{}-{}".format(folder,key, item).replace('//','/'))
    else:
        print('Querying {} points from Overpass API...'.format(key+"-"+item))
        query_string = ''.join("node[\"{}\"=\"{}\"]{};way[\"{}\"=\"{}\"]{};relation[\"{}\"=\"{}\"]{};".format(key, item, bbox, key, item, bbox, key, item, bbox)).replace("=\"*\"",'')
        query_string = "[out:json][timeout:50];({});out+geom;".format(query_string)
        result = json.loads(urllib.request.urlopen('http://overpass-api.de/api/interpreter?data='+query_string).read())
        points = []
        for x in result['elements']:
            elem = {}
            if x['type']=='node':
                lon, lat = x['lon'],x['lat']
            else:
                lon, lat = x['bounds']['minlon'], x['bounds']['minlat']
            elem['geometry'] = shapely.geometry.Point([lon,lat])
            elem['id'] = x['id']
            elem['tag'] = key+'_'+x['tags'][key]
            points.append(elem)
        points = gpd.GeoDataFrame(points,crs={'init': 'epsg:4326'}).to_crs(fiona.crs.from_epsg(4326))
        points.set_index('id', inplace=True)
        if item=='*':
            points['tag'] = [key+'_*']*points.shape[0]
        # caching points df to output_folder
        points.to_file('{}/OSM_points_{}-{}'.format(folder,key,item).replace('//','/'))
        return points

def overpass_get_lines_by_key(folder, bbox, key, item, aspoints=False):
    if "OSM_lines_{}-{}".format(key, item) in os.listdir(folder):
        return gpd.read_file("{}/OSM_lines_{}-{}".format(folder,key, item).replace('//','/'))
    else:
        print('Querying {} lines from Overpass API...'.format(key+"-"+item))
        query_string = ''.join("way[\"{}\"=\"{}\"]{};".format(key, item, bbox))
        query_string = "[out:json][timeout:50];({});out+geom;".format(query_string)
        result = json.loads(urllib.request.urlopen('http://overpass-api.de/api/interpreter?data='+query_string).read())
        lines = []
        for x in result['elements']:
            elem = {}
            try: # it must have at least ['lon', 'lat', 'id', 'tags']
                elem['geometry'] = shapely.geometry.LineString([(i['lon'],i['lat']) for i in x['geometry']])
                elem['id'] = x['id']
                elem['tag'] = "{}_{}".format(key,x['tags'][key])
            except:
                continue
            lines.append(elem)
        lines = gpd.GeoDataFrame(lines)
        lines.set_index('id', inplace=True)
        if aspoints:
            l1, l2 = [], []
            for x in range(lines.shape[0]):
                tmp = [shapely.geometry.Point(i) for i in list(lines.iloc[x]['geometry'].coords)]
                l1 += tmp
                l2 += [lines.iloc[x]['tag']]*len(tmp)
            lines = gpd.GeoDataFrame({'geometry':l1, 'tag':l2})
        lines.to_file('{}/OSM_lines_{}-{}'.format(folder,key,item).replace('//','/'))
    return lines


class OSMHawk(object):

    def __init__(self, bbox, folder):
        if type(bbox)==dict:
            self.bbox = '({},{},{},{})'.format(bbox['south'], bbox['west'], bbox['north'], bbox['east'])
        else:
            self.bbox = bbox
        self.folder = folder
    def transform(self, points=None, lines=None):
        pdf = pd.DataFrame()
        if points is not None:
            for key in points:
                for item in points[key]:
                    pdf = pdf.append(overpass_get_points_by_key(self.folder, self.bbox, key, item))
        pdf['lat'] = pdf.geometry.y
        pdf['lon'] = pdf.geometry.x
        ldf = pd.DataFrame()
        if lines is not None:
            for key in lines:
                for item in lines[key]:
                    ldf = ldf.append(overpass_get_lines_by_key(self.folder, self.bbox, key, item, aspoints=True))
        ldf['lat'] = ldf.geometry.y
        ldf['lon'] = ldf.geometry.x
        return pdf, ldf


# # TESTS
# bbox = {'west':-35.29122515, 'south':-5.91582226, 'east':-35.153019, 'north':-5.702727}
# ol = OSMLeech(bbox, folder='/home/adelsondias/Repos/crime-hotspots/predspot/tests')
# points = {
#     'amenity':['hospital','school']
# }
# lines = {
#     'highway':['primary','secondary']
# }
# ol.transform(points, lines)
