import unittest
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

from geohunter.osm import *
from geohunter.util import *


class TestEagle(unittest.TestCase):

    def setUp(self):
        with Eagle() as api:
            self.state = api.get('(-8.02, -41.01, -3.0, -33.0)',
                                 largest_geom=True,
                                 name='Rio Grande do Norte')
            self.city = api.get('(-8.02, -41.01, -3.0, -33.0)',
                                 largest_geom=True,
                                 name='Natal')
            self.poi = api.get(self.city,
                                amenity=['school', 'hospital'],
                                highway='primary',
                                natural='*')
            self.all_cities = api.get(self.state, sjoin_op='within',
                                admin_level='8')
            self.biggest_city = api.get(self.state, sjoin_op='within', largest_geom=True,
                                admin_level='8')

    def test_osm_get_poi(self):
        self.poi['area'] = self.poi.area
        self.assertEqual(set(self.poi['mf_key']), {'amenity', 'highway', 'natural'})
        self.assertEqual(self.poi.groupby('mf_key').sum()['area'].idxmax(), 'natural')

    def test_osm_get_admin_level(self):
        self.assertEqual(len(self.all_cities), 167)
        self.assertEqual(len(self.biggest_city), 1)
        self.assertEqual(pd.json_normalize(self.biggest_city['tags'])['name'][0],
                        'Mossoró')

    def test_util_kde_aggr(self):
        grid = kde_interpolation(self.poi, area=self.city,
                    bw=10/110, resolution=0.5)
        self.assertEqual(grid.shape, (638, 4))
        self.assertTrue(grid['density'].quantile(0.1) > 0)


if __name__ == '__main__':
    unittest.main()
