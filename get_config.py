
"""
Opens config file and returns config object
"""

import os
import configparser
from configparser import SafeConfigParser


def get_config(config_file_name, safe=False):

    """
    Look in directory this script is running for
    a config file and parse it

    Args:
    Name of config file

    Returns:
    Config object
    """

    # Check config file exists and can be accessed, then open
    try:

        this_dir = os.path.dirname(os.path.abspath(__file__))

        filepath = this_dir + (lambda: '/' if os.name == 'posix' else '\\')() + config_file_name

        print(filepath)

        if not os.path.isfile(filepath):
            print("Error - Missing Config File: %s" % (config_file_name))
            raise IOError('Config file does not exist')

        if safe:
            safe_config = SafeConfigParser()
            safe_config.read(filepath)
            return safe_config

        else:
            config = configparser.ConfigParser()
            config.read(filepath)
            return config

    except IOError:
        print("Error - Unable to access config file: %s" % (config_file_name))
        exit()

    return None
