"""Logging handler"""

import logging
import sys


def get_log_handler(log_file_name, logging_level, logger_name):

    """Create a loghandler that logs to file and to console"""

    lvl = logging_level.lower()

    if lvl == 'critical':
        lvl = logging.CRITICAL
    elif lvl == 'error':
        lvl = logging.ERROR
    elif lvl == 'warning':
        lvl = logging.WARNING
    elif lvl == 'info':
        lvl = logging.INFO
    elif lvl == 'debug':
        lvl = logging.DEBUG
    elif lvl == 'notset':
        lvl = logging.NOTSET

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(log_format)

    logging.basicConfig(filename=log_file_name, level=lvl, format=log_format)

    logger = logging.getLogger(logger_name)

    log_console = logging.StreamHandler(sys.stdout)
    log_console.setFormatter(formatter)

    logger.addHandler(log_console)

    return logger
