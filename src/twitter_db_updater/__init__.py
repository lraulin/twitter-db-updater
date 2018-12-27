# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound
import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = 'twitter-db-updater'
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound

