from setuptools import setup

setup(
    name='geohunter',
    version='0.1.0',    
    description="Geographic feature extraction for machine learning with OpenStreetMap's data",
    url='https://github.com/adaj/geohunter',
    author="Adelson Araujo jr",
    author_email='adelsondias@gmail.com',
    license='MIT',
    packages=['geohunter'],
    python_requires='>=3.6',
    install_requires=['scikit-learn', 'pandas', 'pysal', 'dill'],

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License'
    ],
)

