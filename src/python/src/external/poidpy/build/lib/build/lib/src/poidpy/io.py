"""
Read and write pickle files
"""
# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

import os
import pickle

def write_pickle(obj, filename, path=None):
    if path is None:
        path = os.getcwd()
    filename = os.path.join(path, filename)
    filename = os.path.normpath(filename)
    with open(filename, 'wb') as a:
        pickle.dump(obj, a)


def read_pickle(filename, path=None):
    if path is None:
        path = os.getcwd()
    filename = os.path.join(path, filename)
    filename = os.path.normpath(filename)
    with open(filename, 'rb') as a:
        obj = pickle.load(a)
    return obj
