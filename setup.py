import setuptools
import os

# This will add the __version__ to the globals
with open("src/lsi/__init__.py") as f:
    exec(f.read())

setuptools.setup(
    name='lsi',
    version=__version__,
    author="Narrative Science",
    author_email="anelson@narrativescience.com",
    url="https://github.com/NarrativeScience/lsi",
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    provides=setuptools.find_packages('src'),
    install_requires=open('requirements.txt').readlines(),
    entry_points={
        'console_scripts': ['lsi = lsi.lsi:main']
    }
)
