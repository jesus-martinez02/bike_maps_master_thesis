# This file is part of the Demand Generation Package, Poidpy, developed at KU Leuven.
# Contributors: Jeroen Verstraete, Lotte Notelaers
# License: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see license.txt
# More information at: https://gitlab.mech.kuleuven.be/ITSCreaLab or contact: ITScrealab@kuleuven.be

import logging
from .settings import log_filename, log_level, log_folder, log_to_file, log_name
from pathlib import Path
import datetime


def log(message, level=None, name=None, filename=None, log_path=None):
    """
    Write a message to the logger.

    This logs to file and/or prints to the console (terminal), depending on
    the current configuration of settings.log_file.

    Parameters
    ----------
    message : string
        the message to log
    level : int
        one of Python's logger. level constants
    name : string
        name of the logger
    filename : string
        name of the log file, without file extension
    log_path : string
        name of path to store log-file

    Returns
    -------
    None
    """
    if level is None:
        level = log_level
    if name is None:
        name = log_name
    if filename is None:
        filename = log_filename

    # if logging to file is turned on
    if log_to_file:
        # get the current logger (or create a new one, if none), then log
        # message at requested level
        logger = _get_logger(level=level, name=name, filename=filename, log_path=log_path)
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)


def _get_logger(level, name, filename, log_path=None):
    """
    Create a logger or return the current one if already instantiated.

    Parameters
    ----------
    level : int
        one of Python's logger. level constants
    name : string
        name of the logger
    filename : string
        name of the log file, without file extension

    Returns
    -------
    logger : logging.logger
    """
    logger = logging.getLogger(name)

    if log_path is None:
        log_path = log_folder
    # if a logger with this name is not already set up
    if not getattr(logger, "handler_set", None):

        # get today's date and construct a log filename
        date = "{:%Y-%m-%d}".format(datetime.datetime.now())
        log_filename_time = Path(log_path) / f'{filename}_{date}.log'

        # if the logs folder does not already exist, create it
        log_filename_time.parent.mkdir(parents=True, exist_ok=True)

        # create file handler and log formatter and set them up
        handler = logging.FileHandler(log_filename_time, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.handler_set = True

    return logger
