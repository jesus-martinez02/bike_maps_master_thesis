# This file is part of the Demand Generation Tool, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers and Jeroen Verstraete
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

from setuptools import setup, find_packages

DESC = ("Demand Generation Based on Points-of-Interest.")

README = "See docs on [Gitlab](https://gitlab.kuleuven.be/ITSCreaLab/publications/poidpy-1.0)"

setup(
    name='poidpy',
    version='1.0.0',
    description=DESC,
    packages=find_packages(),
    url="https://gitlab.kuleuven.be/ITSCreaLab/publications/poidpy-1.0",
    author_email="itscrealab@kuleuven.be",
    long_description=README,
    long_description_content_type="text/markdown",
    license="GPLv3")
