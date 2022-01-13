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

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'NASA JPL'
__date__ = '2021-04-05'
__copyright__ = '(C) 2021 by NASA JPL'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load TerrainRelativeNavigation class from file TerrainRelativeNavigation.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .terrain_relative_navigation import TerrainRelativeNavigationPlugin
    return TerrainRelativeNavigationPlugin()
