""" log helper """

# from solnlib.log import Logs

from logging import getLogger, Logger

def get_logger(name: str) -> Logger:
    """ getter """
    return getLogger(name)
