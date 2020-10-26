# Geohunter

[![Documentation Status](https://readthedocs.org/projects/geohunter/badge/?version=latest)](https://geohunter.readthedocs.io/en/latest/?badge=latest)

Geohunter is a python package for parsing and analyzing data from the Overpass API in a pandas-like programming framework. There are similar packages to ours, but our purpose is to create a bridge between data from the OpenStreetMap platform to the geopandas data structures, which offer lots of useful tools for geospatial data analysis.

This package was originally created with the purpose of providing volunteered geographic information to machine learning pipelines. Data from points-of-interest of the city may represent an important source for feature extraction. There are cases where the density of geographic information may help predict a particular variable. For example, consider a set of various points-of-interest.

![Points of interest](https://github.com/adaj/geohunter/blob/master/docs/images/poi.png?raw=true)

In our package, we provide some geographic feature extraction procedures, for example with the function `util.kde_interpolation` (see result in figure below), based on the Scipy implementation of KDE.

![KDE estimation](https://github.com/adaj/geohunter/blob/master/docs/images/kde_schools.png?raw=true)

## Installation

Clone the package, go to the repository directory (where setup.py is) and `pip install .` should start the installation.

## Usage

Please take a look at the /example folder while the documentation is under construction.

## Requirements

Pandas, geopandas, shapely, requests. For visualization (optional), matplotlib and descartes.


## Contributing

We are welcome to your contribution, submit your pull request!

## Authors

Adelson Araújo (adelson.dias@gmail.com)
João Marcos do Valle (jmarcos.araujo96@gmail.com)
