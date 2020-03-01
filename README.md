# Geohunter

Geohunter is a python package for parsing and analyzing data from the Overpass API in a pandas-like programming framework. There are similar packages to ours, but our purpose is to create a bridge between data from the OpenStreetMap platform to the geopandas data structures, which offer lots of useful tools for geospatial data analysis.

This package was originally created with the purpose of providing volunteered geographic information (VGI) to machine learning pipelines. There are cases where the density of geographic information may help predict a particular variable. Data from points-of-interest (PoI) of the city shall represent an important source for feature extraction.


![enter image description here](https://github.com/adaj/adaj.github.io/blob/master/images/poi_data.png?raw=true)

In our package, we provide some geographic feature extraction procedures, for example with the function `utils.kde_interpolation` (see result in figure below), based on the Scipy implementation of KDE. This geographic feature extraction aspect of our framework is continuously being incremented to get even powerful variables.

![enter image description here](https://github.com/adaj/adaj.github.io/blob/master/images/poi_kde.png?raw=true)

## Installation

Clone the package, go to the repository directory (where setup.py is) and `pip install .` should start the installation.

## Usage

Take a look at the /example folder.

## Requirements

Pandas, geopandas, shapely, requests. For visualization (optional), matplotlib and descartes.


## Contributing

We are welcome to your contribution, submit your pull request!

## Authors

Adelson Araújo (adelson.dias@gmail.com)
João Marcos do Valle (jmarcos.araujo96@gmail.com)
