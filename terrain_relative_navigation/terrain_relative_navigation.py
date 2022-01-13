# -*- coding: utf-8 -*-

"""
/***************************************************************************
 TerrainRelativeNavigation
                                 A QGIS plugin
 This plugin analyzes terrain for the purpose of automatic bearing-based robotic navigation
                              -------------------
        begin                : 2021-04-05
        copyright            : (C) 2021 by NASA JPL
        email                : russells@jpl.nasa.gov
 ***************************************************************************/
"""

__author__ = 'NASA JPL'
__date__ = '2021-04-05'
__copyright__ = '(C) 2021 by NASA JPL'

__revision__ = '$Format:%H$'

import os
import sys
import inspect

from qgis.core import QgsProcessingAlgorithm, QgsApplication
from .terrain_relative_navigation_provider import TerrainRelativeNavigationProvider

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


class TerrainRelativeNavigationPlugin(object):

    def __init__(self):
        self.provider = None

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.provider = TerrainRelativeNavigationProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
