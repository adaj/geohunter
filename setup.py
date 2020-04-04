from setuptools import setup

setup(
    name='geohunter',
    version='0.1.2',
    description="Package for parsing and analyzing OpenStreetMap data",
    url='https://github.com/adaj/geohunter',
    author="Adelson Araujo",
    author_email='adelson.dias@gmail.com',
    license='MIT',
    packages=['geohunter'],
    python_requires='>=3.7',
    install_requires=['pandas', 'matplotlib',  'scipy',
        'geopandas==0.7.0', 'descartes', 'requests',
        'geojsoncontour'],
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License'
    ],
)
