import pandas as pd
import numpy as np
import fiona
import shapely
import geopandas as gpd
import os
import json
import urllib

def overpass_get_points_by_key(folder, bbox, key, item):
    #keys examples: 'amenity', 'building', 'highway', 'tourism', 'historic'
    if "OSM_points_{}-{}".format(key, item) in os.listdir(folder):
        return gpd.read_file("{}/OSM_points_{}-{}".format(folder,key, item).replace('//','/'))
    else:
        print('Querying {} points from Overpass API...'.format(key+"-"+item))
        query_string = ''.join("node[\"{}\"=\"{}\"]{};way[\"{}\"=\"{}\"]{};relation[\"{}\"=\"{}\"]{};".format(key, item, bbox, key, item, bbox, key, item, bbox)).replace("=\"*\"",'')
        query_string = "[out:json][timeout:50];({});out+geom;".format(query_string)
        for i in range(5):
            try:
                result = json.loads(urllib.request.urlopen('http://overpass-api.de/api/interpreter?data='+query_string).read())
            except:
                continue
            break
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
    #keys examples: 'amenity', 'building', 'highway', 'tourism', 'historic'
    if "OSM_lines_{}-{}".format(key, item) in os.listdir(folder):
        return gpd.read_file("{}/OSM_lines_{}-{}".format(folder,key, item).replace('//','/'))
    else:
        print('Querying {} lines from Overpass API...'.format(key+"-"+item))
        query_string = ''.join("way[\"{}\"=\"{}\"]{};".format(key, item, bbox))
        query_string = "[out:json][timeout:50];({});out+geom;".format(query_string)
        for i in range(5):
            try:
                result = json.loads(urllib.request.urlopen('http://overpass-api.de/api/interpreter?data='+query_string).read())
            except:
                continue
            break
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
