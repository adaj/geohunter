.. Geohunter documentation master file, created by
   sphinx-quickstart on Tue May  5 23:54:56 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Geohunter
=====================================

Geohunter is a python package for parsing and analyzing data from the Overpass API in a pandas-like programming framework. There are similar packages to ours, but our purpose is to create a bridge between data from the OpenStreetMap platform to the geopandas data structures, which offer lots of useful tools for geospatial data analysis.

This package was originally created with the purpose of providing volunteered geographic information to machine learning pipelines. Data from points-of-interest of the city may represent an important source for feature extraction. There are cases where the density of geographic information may help predict a particular variable. For example, consider a set of various points-of-interest.

.. image:: https://raw.githubusercontent.com/adaj/geohunter/master/examples/images/poi.png

In our package, we provide some geographic feature extraction procedures with the function `util.kde_interpolation` (see result in figure below), based on the Scipy implementation of KDE. See the plot below with an example for schools density.

.. image:: https://raw.githubusercontent.com/adaj/geohunter/master/examples/images/kde_schools.png

If you find any opportunity to do so, feel free to open an issue, fork the repository and contribute to this project.


.. toctree::
   :maxdepth: 2

   modules
   setup
   example



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
