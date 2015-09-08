import setuptools
import os

# This will add the __version__ to the globals
execfile('src/lsi/__init__.py')

setuptools.setup(
    name='lsi',
    version=__version__,
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    provides=setuptools.find_packages('src'),
    install_requires=open('requirements.txt').readlines(),
    entry_points={
        'console_scripts': ['lsi = lsi.lsi:main']
    }
)
