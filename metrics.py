import numpy as np

def q_ongrid(grid, strata_col, value_col):
    # usage: q_ongrid(sgrid.data, strata_col='BAIRRO', value_col='value')
    qi = 0
    for strata in grid[strata_col].unique():
        x = grid.loc[grid[strata_col]==strata]
        if x.shape[0]==0:
            qi += 0
        else:
            qi += x.shape[0]*np.var(x[value_col])
    return 1 - (qi/(grid.shape[0]*np.var(grid[value_col])))
