from setuptools import setup

setup(
    name='geohunter',
    version='0.1.3',
    description="Package for parsing and analyzing OpenStreetMap data",
    url='https://github.com/adaj/geohunter',
    author="Adelson Araujo",
    author_email='adelson.dias@gmail.com',
    license='MIT',
    packages=['geohunter'],
    python_requires='>=3.7',
    install_requires=['pandas', 'matplotlib',  'scipy',
        'statsmodels==0.12.1', 'geopandas', 'descartes', 'requests',
        'geojsoncontour'],
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License'
    ],
)
