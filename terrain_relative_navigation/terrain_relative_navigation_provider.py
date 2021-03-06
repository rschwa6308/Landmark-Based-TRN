# -*- coding: utf-8 -*-

"""
/***************************************************************************
 TerrainRelativeNavigation
                                 A QGIS plugin
 This plugin analyzes terrain for the purpose of automatic bearing-based robotic navigation
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-05
        copyright            : (C) 2021 by NASA JPL
        email                : russells@jpl.nasa.gov
 ***************************************************************************/
"""

__author__ = 'NASA JPL'
__date__ = '2021-04-05'
__copyright__ = '(C) 2021 by NASA JPL'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from .quality_analyzer_algorithm import QualityAnalyzerAlgorithm
from .peak_extractor_algorithm import PeakExtractorAlgorithm
from .path_animation_algorithm import PathAnimationAlgorithm


class TerrainRelativeNavigationProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(QualityAnalyzerAlgorithm())
        self.addAlgorithm(PeakExtractorAlgorithm())
        self.addAlgorithm(PathAnimationAlgorithm())


    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return "trn"

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr("Terrain Relative Navigation")

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
