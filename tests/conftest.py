"""Conftest"""

from sys import path
from os.path import realpath, dirname, sep

path.append(realpath(dirname(__file__) + f"{sep}.."))
