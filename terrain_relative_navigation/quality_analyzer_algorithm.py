# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QualityAnalyzer
                                 A QGIS plugin
 This plugin computes a localization quality raster from viewshed information.
                              -------------------
        begin                : 2021-03-10
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
"""

__author__ = "NASA JPL"
__date__ = "2021-03-10"
__copyright__ = "(C) 2021 by NASA JPL"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingOutputRasterLayer,
                       QgsProcessingOutputNumber,
                       QgsProcessingOutputMultipleLayers,
                       QgsProcessingFeatureSourceDefinition,
                       QgsProject,
                       QgsVectorLayer,
                       QgsRasterFileWriter,
                       QgsRasterPipe,
                       Qgis,
                       QgsRasterLayer,
                       QgsLayerTreeGroup,
                       QgsRasterBlock)

# from QgsProcessingFeatureSourceDefinition import FlagCreateIndividualOutputPerInputFeature

import processing
from osgeo import gdal
import osr
import os
import numpy as np

from . import quality_analysis



class QualityAnalyzerAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    LANDMARKS_LAYER = "INPUT_LANDMARKS"
    VIEWSHEDS_DIR = "OUTPUT_VIEWSHEDS"
    FIMS_DIR = "FIMS_DIR"
    RADIUS_OF_ANALYSIS = "RADIUS_OF_ANALYSIS"
    LANDMARK_HEIGHT = "LANDMARK_HEIGHT"
    ROBOT_HEIGHT = "ROBOT_HEIGHT"
    POINTING_ACCURACY = "POINTING_ACCURACY"
    QUALITY_METRIC = "QUALITY_METRIC"

    NUM_LANDMARKS = "NUM_LANDMARKS"
    INDIVIDUAL_VIEWSHEDS = "INDIVIDUAL_VIEWSHEDS"

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # Elevation Map
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr("DEM"),
            )
        )

        # Landmarks Layer
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LANDMARKS_LAYER,
                self.tr("Landmarks"),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.RADIUS_OF_ANALYSIS,
                self.tr("Radius of analysis, meters"),
                QgsProcessingParameterNumber.Integer,
                defaultValue=10000
            ),
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LANDMARK_HEIGHT,
                self.tr("Landmark height, meters"),
                QgsProcessingParameterNumber.Double,
                defaultValue=2.0
            ),
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.ROBOT_HEIGHT,
                self.tr("Robot height, meters"),
                QgsProcessingParameterNumber.Double,
                defaultValue=2.0
            ),
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.POINTING_ACCURACY,
                self.tr("Pointing accuracy, milliradians"),
                QgsProcessingParameterNumber.Double,
                defaultValue=1.75
            ),
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.QUALITY_METRIC,
                self.tr("Quality metric"),
                # ["sqrt(trace(C)) (\"GDOP\")", "sqrt(max_eigenvalue(C)) (\"Worst-Case\")"],
                ["GDOP = sqrt(trace(C))", "Worst-Case = sqrt(max_eigenvalue(C))"],
                defaultValue=0
            )
        )

        # Viewsheds Folder
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.VIEWSHEDS_DIR,
                self.tr("Viewsheds Output Folder"),
                optional=False
            )
        )

        # FIM's Folder
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.FIMS_DIR,
                self.tr("FIMs Output Folder"),
                optional=False
            )
        )

        # Output (quality) layer destination
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr("Quality Layer Output Destination")
            )
        )

        self.addOutput(
            QgsProcessingOutputNumber(
                self.NUM_LANDMARKS,
                self.tr("Number of landmarks processed")
            )
        )

        self.addOutput(
            QgsProcessingOutputMultipleLayers(
                self.INDIVIDUAL_VIEWSHEDS,
                self.tr("Individual viewshed rasters")
            )
        )
    
    def viewshed_filename(self, i):
        return f"viewshed_{i}.tif"
    
    def fim_filename(self, i):
        return f"FIM_{i}.tif"
    
    def write_raster_layer_to_file(self, raster_layer, filename):
        file_writer = QgsRasterFileWriter(filename)
        pipe = QgsRasterPipe()
        provider = raster_layer.dataProvider()
        if not pipe.set(provider.clone()):
            msg = "Cannot set pipe provider"
            raise RuntimeError(msg)

        file_writer.writeRaster(
            pipe,
            provider.xSize(),
            provider.ySize(),
            provider.extent(),
            provider.crs()
        )

    def write_raster_data_to_layer(self, filename, array, template_raster_filename, bands=1):
        if array.shape[0] != bands:
            raise ValueError("given array size does not match given number of bands")
        
        template_ds = gdal.OpenShared(template_raster_filename)
        
        driver = gdal.GetDriverByName("GTiff")
        dtype = template_ds.GetRasterBand(1).DataType   # use same datatype as template
        out_ds = driver.Create(filename, array.shape[2], array.shape[1], bands, dtype)

        out_ds.SetGeoTransform(template_ds.GetGeoTransform())
        out_ds.SetProjection(template_ds.GetProjection())

        for i in range(bands):
            out_ds.GetRasterBand(i + 1).WriteArray(array[i])

        # # if bands == 3:
        # #     raise ValueError(array.shape, np.nanmin(array[0]), np.nanmax(array[0]), np.nanmin(array[1]), np.nanmax(array[1]), np.nanmin(array[2]), np.nanmax(array[2]))

        # template_ds = gdal.OpenShared(template_raster_filename)

        # # create a temporary data store with a driver that supports adding bands
        # temp_ds = gdal.GetDriverByName("MEM").CreateCopy("", template_ds, 0)
        # for _ in range(bands - template_ds.RasterCount):
        #     temp_ds.AddBand()
        
        # for i in range(bands):

        #     temp_ds.GetRasterBand(i + 1).WriteArray(array[i])

        # # convert to desired driver
        # gdal.GetDriverByName("GTiff").CreateCopy(filename, temp_ds, 0)


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        landmarks_layer = self.parameterAsSource(parameters, self.LANDMARKS_LAYER, context)
        num_landmarks = landmarks_layer.featureCount()

        # Generate viewpoints vector layer
        viewpoints_layer_path = processing.run(
            "visibility:create_viewpoints",
            {
                "OBSERVER_POINTS": parameters[self.LANDMARKS_LAYER],
                "DEM": parameters[self.INPUT],
                "RADIUS": parameters[self.RADIUS_OF_ANALYSIS],
                "OBS_HEIGHT":  parameters[self.LANDMARK_HEIGHT],
                "TARGET_HEIGHT": parameters[self.ROBOT_HEIGHT],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
            },
            is_child_algorithm=True,
            context=context,
            feedback=feedback
        )["OUTPUT"]

        # print(viewpoints_layer_name)
        # viewpoints_layer = self.parameterAsSource(viewpoints_result, "OUTPUT", context)
        viewpoints_layer = context.takeResultLayer(viewpoints_layer_path)


        # Run viewshed analysis
        viewsheds_dir = self.parameterAsFileOutput(parameters, self.VIEWSHEDS_DIR, context)

        if not os.path.isdir(viewsheds_dir):
            os.mkdir(viewsheds_dir)        

        viewsheds_paths = []
        viewsheds = []
        for i, viewpoint in enumerate(viewpoints_layer.getFeatures()):
            # stop execution if canceled
            if feedback.isCanceled():
                break
            feedback.setProgress(int(100 * i / num_landmarks))

            scratch_layer = QgsVectorLayer("Point", "temporary_points", "memory")
            scratch_provider = scratch_layer.dataProvider()

            scratch_layer.startEditing()
            scratch_provider.addAttributes(viewpoints_layer.fields())
            scratch_layer.updateFields()
            scratch_provider.addFeatures([viewpoint])
            
            filename = os.path.join(viewsheds_dir, self.viewshed_filename(i))

            viewshed_path = processing.run(
                "visibility:Viewshed",
                {
                    "OBSERVER_POINTS": scratch_layer,
                    "DEM": parameters[self.INPUT],
                    "OUTPUT": filename
                },
                is_child_algorithm=True,
                context=context,
                feedback=feedback
            )["OUTPUT"]
            viewsheds_paths.append(viewshed_path)
            viewsheds.append(
                QgsRasterLayer(viewshed_path, f"viewshed_{i}", "gdal")
            )


        # Run quality analysis on the computed viewsheds (now written to disk) and write results to the new rasters
        fims_dir = self.parameterAsFileOutput(parameters, self.FIMS_DIR, context)
        if not os.path.isdir(fims_dir):
            os.mkdir(fims_dir)

        pointing = self.parameterAsDouble(parameters, self.POINTING_ACCURACY, context) * 1e-3
        fim_arrays = quality_analysis.compute_fims(viewpoints_layer, viewsheds_paths)

        metric_id = self.parameterAsEnum(parameters, self.QUALITY_METRIC, context)
        quality_array = quality_analysis.compute_quality(fim_arrays, pointing, metric=metric_id)
        # raise ValueError(quality_array)

        # write resulting arrays to layers

        quality_raster_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        self.write_raster_data_to_layer(quality_raster_path, np.array([quality_array]), viewsheds_paths[0])

        quality_raster = QgsRasterLayer(quality_raster_path, "GDOP" if metric_id == 0 else "Worst-Case")      # reload and name layer


        # Add Viewsheds, FIM's, and Quality layer to map and index
        project_instance = QgsProject.instance()
        root = project_instance.layerTreeRoot()

        viewshed_node_group = QgsLayerTreeGroup("Viewsheds")
        root.addChildNode(viewshed_node_group)
        for viewshed in viewsheds:
            project_instance.addMapLayer(viewshed)
            viewshed_node_group.addLayer(viewshed)
        
        fims_node_group = QgsLayerTreeGroup("FIMs")
        root.addChildNode(fims_node_group)
        for i, fim_array in enumerate(fim_arrays):
            name = self.fim_filename(i)
            full_name = os.path.join(fims_dir, name)
            fixed_array = np.moveaxis(fim_array, -1, 0)
            self.write_raster_data_to_layer(full_name, fixed_array, viewsheds_paths[0], bands=3)
            fim_layer = QgsRasterLayer(full_name, name)
            project_instance.addMapLayer(fim_layer)
            fims_node_group.addLayer(fim_layer)

        project_instance.addMapLayer(quality_raster)
        root.addLayer(quality_raster)

        return {
            self.OUTPUT: quality_raster_path,
            self.NUM_LANDMARKS: num_landmarks,
            self.INDIVIDUAL_VIEWSHEDS: viewsheds_paths
        }


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "localization_quality"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        # return self.tr(self.name())
        return "Localization Quality"

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ""

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return QualityAnalyzerAlgorithm()
