# -*- coding: utf-8 -*-

"""
/***************************************************************************
 MovementAnalysis
                                 A QGIS plugin
 Toolbox for raster based movement analysis: least-cost path, cost surface, accessibility.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-05-17
        copyright            : (C) 2024 by Zoran Čučković
        email                : cuckovic.zoran@gmail.com
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

__author__ = 'Zoran Čučković'
__date__ = '2024-05-17'
__copyright__ = '(C) 2024 by Zoran Čučković'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSink)

import subprocess
import sys
# pip in not allowed from code ....




class InstallScikit(QgsProcessingAlgorithm):
        # Constants used to refer to parameters and outputs. They will be
       # used when calling the algorithm from another algorithm, or when
       # calling from the QGIS console.
    OUTPUT = 'OUTPUT'
    
    def initAlgorithm(self, config=None): 
        self.addParameter(QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Fake layer")))

    def processAlgorithm(self, parameters, context, feedback):
        
        try: 
            from skimage import graph
            feedback.setProgressText("Scikit-image is installed - all OK")
        except:
            p=subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-image"])
            print (p)
        
        return {self.OUTPUT:None}



    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Install Scikit'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

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
        return 'Helpers'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return InstallScikit()
