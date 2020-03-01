import pandas as pd
import geopandas as gpd
import numpy as np
from numpy import linspace, ceil, meshgrid, vstack
from shapely.geometry import Point
from scipy import stats

import geohunter.osm

pd.options.mode.chained_assignment = None


def kde_interpolation(poi, area=None, resolution=1, grid=None):
    if grid is None and area is None:
        raise ValueError('grid or area must be given.')
    elif grid is None and isinstance(area, gpd.GeoDataFrame):
        grid = make_gridpoints(area, resolution)
    assert isinstance(poi, gpd.GeoDataFrame)
    kernel = stats.gaussian_kde(np.vstack([poi.centroid.x, poi.centroid.y]),
        bw_method='scott')
    grid_ = grid[:]
    grid_['density'] = kernel(grid[['lon','lat']].values.T)
    return grid_


def make_gridpoints(bbox, resolution=0.5, return_coords=False):
    bbox_ = parse_bbox(bbox)
    s, w, n, e = map(float, bbox_[1:-1].split(','))
    nlon = int(ceil((e-w)/(resolution/111.32)))
    nlat = int(ceil((n-s)/(resolution/110.57)))
    lonv, latv = meshgrid(linspace(w, e, nlon), linspace(s, n, nlat))
    gridpoints = pd.DataFrame(vstack([lonv.ravel(), latv.ravel()]).T,
        columns=['lon','lat'])
    gridpoints['geometry'] = gridpoints.apply(
        lambda x: Point([x['lon'],x['lat']]), axis=1)
    gridpoints = gpd.GeoDataFrame(gridpoints, crs={'init': 'epsg:4326'})
    if isinstance(bbox, gpd.GeoDataFrame):
        grid_ix = gpd.sjoin(gridpoints, bbox, op='intersects').index.unique()
        gridpoints = gridpoints.loc[grid_ix]
    if return_coords:
        return gridpoints, lonv, latv
    else:
        return gridpoints


def parse_bbox(bbox):
    """
    Organizes bbox to the standard format.
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
