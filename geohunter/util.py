"""
geohunter.util

This module implements several operations for analyzing OpenStreetMap data.

Contributors : Adelson Araujo jr
"""

import math
import pandas as pd
import geopandas as gpd
import numpy as np
from numpy import linspace, ceil, meshgrid, vstack, zeros
from shapely.geometry import Point, Polygon
from scipy import stats
import matplotlib.pyplot as plt
import geojsoncontour


pd.options.mode.chained_assignment = None


def kde_interpolation(poi, area=None, resolution=1, grid=None, return_contour_geojson=False):
    """
    Applies kernel density estimation to a set points-of-interest
    measuring the density estimation on a grid of places (arbitrary points
    regularly spaced).

    Parameters
    ----------
    poi : GeoDataFrame.
    Corresponds to input data.

    area : GeoDataFrame or None, default is None.
    It's the geographic boundaries in which the result will be delimited.

    resolution : float, default is 1.
    Space between the arbitrary points of resulting grid.

    grid : GeoDataFrame or None, default is None.
    If a grid is not given, then it is provided according to the area parameter
    and resolution.

    Returns
    -------
    GeoDataFrame with a grid of points regularly spaced with the respective
    density values for the input points-of-interest given.
    """
    if grid is None and area is None:
        raise ValueError('grid or area must be given.')
    if grid is None and isinstance(area, gpd.GeoDataFrame):
        grid, lonv, latv = make_gridpoints(area, resolution, return_coords=True)
    assert isinstance(poi, gpd.GeoDataFrame)
    kernel = stats.gaussian_kde(np.vstack([poi.centroid.x, poi.centroid.y]),
                                bw_method=1/110)#'scott')
    grid_ = grid[:]
    grid_['density'] = kernel(grid[['lon', 'lat']].values.T)
    if return_contour_geojson:
        return contour_geojson(grid_['density'], lonv, latv,
                               cmin=grid_['density'].min(),
                               cmax=grid_['density'].max())
    else:
        return grid_


def contour_geojson(y, lonv, latv, cmin, cmax):
    Z = zeros(lonv.shape[0]*lonv.shape[1]) - 999
    Z[y.index] = y.values
    Z = Z.reshape(lonv.shape)
    fig, axes = plt.subplots()
    contourf = axes.contourf(lonv, latv, Z,
                            levels=linspace(cmin, cmax, 25),
                            cmap='Spectral_r')
    geojson = geojsoncontour.contourf_to_geojson(contourf=contourf, fill_opacity=0.5)
    plt.close(fig)
    return geojson


def make_gridpoints(bbox, resolution=1, return_coords=False):
    """
    It constructs a grid of points regularly spaced.

    Parameters
    ----------
    bbox : str, GeoDataFrame or dict.
    Corresponds to the boundary box in which the grid will be formed.
    If a str is provided, it should be in '(S,W,N,E)' format. With a
    GeoDataFrame, we will use the coordinates of the extremities. Also
    one can provide a dict with 'south', 'north', 'east', 'west'.

    resolution : float, default is 1.
    Space between the arbitrary points of resulting grid.

    return_coords : bool
    If it is wanted to return the coordinate sequences.
    """
    bbox_ = parse_bbox(bbox)
    b_s, b_w, b_n, b_e = map(float, bbox_[1:-1].split(','))
    nlon = int(ceil((b_e-b_w) / (resolution/111.32)))
    nlat = int(ceil((b_n-b_s) / (resolution/110.57)))
    lonv, latv = meshgrid(linspace(b_w, b_e, nlon), linspace(b_s, b_n, nlat))
    gridpoints = pd.DataFrame(vstack([lonv.ravel(), latv.ravel()]).T,
                              columns=['lon', 'lat'])
    gridpoints['geometry'] = gridpoints.apply(lambda x: Point([x['lon'], x['lat']]),
                                              axis=1)
    gridpoints = gpd.GeoDataFrame(gridpoints, crs={'init': 'epsg:4326'})
    if isinstance(bbox, gpd.GeoDataFrame):
        grid_ix = gpd.sjoin(gridpoints, bbox, op='intersects').index.unique()
        gridpoints = gridpoints.loc[grid_ix]
    if return_coords:
        return gridpoints, lonv, latv
    return gridpoints


def parse_bbox(bbox):
    """
    Organizes bbox to the standard format used in other places in the package
    and also in Overpass API.

    Parameters
    ----------
    bbox : str, GeoDataFrame or dict.
    Corresponds to the boundary box wanted to be formatted.

    Returns
    -------
    str containing '(S,W,N,E)' coordinates of the bounding box.
    """
    if isinstance(bbox, gpd.GeoDataFrame):
        bounds = bbox.bounds
        bbox = {'north':bounds.max().values[3], 'east':bounds.max().values[2],
                'south':bounds.min().values[1], 'west':bounds.min().values[0]}
        bbox = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
    elif isinstance(bbox, str):
        bbox_ = bbox[1:-1].split(',')
        bbox_ = [float(b) for b in bbox_]
        assert bbox_[0] < bbox_[2] and bbox_[1] < bbox_[3], \
            "Invalid bbox. Please follow this structure: '(S,W,N,E)'"
        bbox = bbox.replace(' ', '')
    elif isinstance(bbox, dict):
        assert bbox['south'] < bbox['north'] and bbox['west'] > bbox['east'], \
            "Invalid bbox. Please include 'south','north','west' and 'east' keys"
        bbox = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
    return bbox
