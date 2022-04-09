""" log helper """

from solnlib.log import Logs


def get_logger(name):
    """ getter """
    return Logs().get_logger(name)
