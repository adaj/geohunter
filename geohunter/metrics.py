import numpy as np
import pysal

def q_ongrid(data, grid, strata_col):
#   usage: q_ongrid(sgrid.data, strata_col='BAIRRO', value_col='value')
    qi = 0
    for strata in grid[strata_col].unique():
        x = grid.loc[grid[strata_col]==strata]
        if x.shape[0]==0:
            qi += 0
        else:
            qi += x.shape[0]*np.var(data.loc[x.index])
    return 1 - (qi/(data.shape[0]*np.var(data)))

def moran_i_ongrid(data, coords, d_threshold):
#    usage: moran_i_ongrid(data=grid.data['value'], 
#                coords=grid.data['geometry'].centroid.apply(lambda x:x.coords[0])
#                d_threshold=1/110)
    from pysal.explore.esda.moran import Moran
    w=pysal.lib.weights.distance.DistanceBand(list(coords.values),
                                              threshold=d_threshold,binary=True)
    
    mi = Moran(list(data.values),  w)
    mi.p_norm
    mi.I
    return mi.I, mi.p_norm

