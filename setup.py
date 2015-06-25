import setuptools
import os

setuptools.setup(
    name='lsi',
    version='0.0.1',
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    provides=setuptools.find_packages('src'),
    install_requires=open('requirements.txt').readlines(),
    entry_points={
        'console_scripts': ['lsi = lsi.lsi:main']
    }
)
