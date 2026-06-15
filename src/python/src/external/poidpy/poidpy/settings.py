"""
General settings to be used throughout the project
"""
# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Lotte Notelaers
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

import os
from pathlib import Path

# Initialize path to package and config folder
path_to_module = os.path.dirname(os.path.dirname(__file__))
config_folder = os.path.join(path_to_module, 'config')
Path(config_folder).mkdir(parents=True, exist_ok=True)

# Different EPSG codes for coordinate reference system transformations
epsg_wgs84 = 4326
etrs89_eu = 3035
webmercator = 3857

proj_crs = webmercator # to be specified to a projected coordinate reference system which is applicable for the study area

# logging setup
log_to_file = True
log_folder = 'logs'
log_level = 20  # Info level
log_filename = 'poidpy'
log_name = 'POID'

# Others
priority_column = 'priority'
classification_col = 'classification'
point_count = 'points_in_poly'
