import pandas as pd
import numpy as np
import shapely
import os
import geopandas as gpd
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import KFold, GridSearchCV

import geohunter.osm

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
    pgrid = {'bandwidth': np.logspace(-1, -5, 50),
             'kernel':['gaussian','linear','exponential','tophat'],
             'metric':['haversine']}
    gscv = GridSearchCV(KernelDensity(), pgrid,
                        cv=5, n_jobs=-1, iid=False)
    gscv.fit(points[['lon','lat']].sample(int(n_samples),random_state=0));
    return gscv.best_params_

def kde_mean_grid_column(grid, X, column):
    Xn = grid.data.join(X).groupby(column).mean()[X.columns]
    Xn.index.name='place'
    return grid.data.join(Xd, on=column)[X.columns]

def landmark_dens_grid_column(landmarks, grid, city_shape, column):
    plgrid = gpd.sjoin(landmarks.pdf, city_shape, op='within')
    llgrid = gpd.sjoin(landmarks.ldf, city_shape, op='within')

    Xn = pd.DataFrame()
    for item in plgrid['tag'].unique():
        dens = plgrid.loc[plgrid['tag']==item].groupby('BAIRRO').size()/(10000*city_shape.set_index(column).area)
        dens = dens.fillna(0)
        Xn[item] = dens
    for item in llgrid['tag'].unique():
        dens = llgrid.loc[llgrid['tag']==item].groupby('BAIRRO').size()/(10000*city_shape.set_index(column).area)
        dens = dens.fillna(0)
        Xn[item] = dens
    Xn = grid.join(Xn, on=column)[Xn.columns]
    Xn.index.name = 'place'
    return Xn


class Grid(object):

    def __init__(self, resolution):
        self.resolution = resolution

    def fit(self, city_shape):
        self.city_shape = city_shape
        self.data, self.lonv, self.latv = make_grid(bbox={'north':city_shape.bounds.max().values[3],
                                                            'east':city_shape.bounds.max().values[2],
                                                            'south':city_shape.bounds.min().values[1],
                                                            'west':city_shape.bounds.min().values[0]},
                                                    resolution=self.resolution)
        self.data = gpd.sjoin(self.data, self.city_shape, how='inner', op='within')
        self.data = self.data[~self.data.index.duplicated(keep='first')]
        return self


class KDE(object):

    def __init__(self, grid, params='auto'):
        self.grid = grid
        self.params = params

    def fit(self, points, tuning_samples=None):
        if self.params=='auto':
            self.params = gridsearch_kde_params(points, tuning_samples)
        return self

    def transform(self, points, label):
        kde = KernelDensity(**self.params).fit(points[['lon','lat']])
        X = pd.DataFrame(kde.score_samples(self.grid[['lon','lat']]),
                         index=self.grid.index, columns=[label])
        X.index.name = 'place'
        return X


class Landmarks(object):

    def __init__(self, city_shape, osm_folder):
        self.osm_folder = osm_folder
        self.hawk = geohunter.osm.OSMHawk(bbox={'north':city_shape.bounds.max().values[3],
                                            'east':city_shape.bounds.max().values[2],
                                            'south':city_shape.bounds.min().values[1],
                                            'west':city_shape.bounds.min().values[0]},
                                      folder=self.osm_folder)

    def fit(self, points, lines):
        self.pdf, self.ldf = self.hawk.transform(points, lines)
        return self


class KDEFeatures(object):

    def __init__(self, landmarks, kde_params):
        self.landmarks = landmarks
        self.kde_params = {}
        if kde_params=='auto':
            for ptype in self.landmarks.pdf['tag'].unique():
                self.kde_params[ptype] = 'auto'
            for ltype in self.landmarks.ldf['tag'].unique():
                self.kde_params[ltype] = 'auto'
        else:
            self.kde_params = kde_params

    def fit_transform(self, grid):
        label = "{}_{}_{}".format(grid.shape[0],
                 self.landmarks.pdf['tag'].unique().shape[0],
                 self.landmarks.ldf['tag'].unique().shape[0])
        if 'GF_{}.csv'.format(label) in os.listdir(self.landmarks.osm_folder):
            X = pd.read_csv(self.landmarks.osm_folder+'/GF_{}.csv'.format(label).replace('//','/')).set_index('place')
        else:
            X = pd.DataFrame(index=grid.index)
            for ptype in self.landmarks.pdf['tag'].unique():
                p = self.landmarks.pdf.loc[self.landmarks.pdf['tag']==ptype]
                kde = KDE(grid, params=self.kde_params[ptype]).fit(p)
                self.kde_params[ptype] = kde.params
                X = X.join(kde.transform(p, label='kde:'+ptype), on='place')
            for ltype in self.landmarks.ldf['tag'].unique():
                l = self.landmarks.ldf.loc[self.landmarks.ldf['tag']==ltype]
                kde = KDE(grid, params=self.kde_params[ltype]).fit(l, 500)
                self.kde_params[ltype] = kde.params
                X = X.join(kde.transform(l, label='kde:'+ltype), on='place')
            X.to_csv(self.landmarks.osm_folder+'/GF_{}.csv'.format(label))
        return X

def plot_kde(shape, grid, kde, ax, fig_path=False, geojson_path=False):
    import numpy as np
    import geojsoncontour
    Z = np.zeros(grid.lonv.shape[0]*grid.lonv.shape[1]) - 999
    Z[kde.reset_index()['place'].unique()] = kde.values.ravel()
    Z = Z.reshape(grid.lonv.shape)
    shape.plot(ax=ax, color='white', edgecolor='black')
    contourf = plt.contourf(grid.lonv, grid.latv, Z, levels=np.linspace(-2, 7, 15), alpha=0.6, cmap=plt.cm.Spectral_r)
    plt.axis('off')
    if fig_path:
        plt.savefig(fig_path)
    if geojson_path:
        geojsoncontour.contourf_to_geojson(contourf=contourf, geojson_filepath=geojson_path, fill_opacity=0.5)
    plt.show()
    return
