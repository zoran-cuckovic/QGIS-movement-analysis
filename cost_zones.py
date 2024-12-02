# -*- coding: utf-8 -*-

"""
/***************************************************************************
 TestProcessing
                                 A QGIS plugin
 Some descr
                              -------------------
        begin                : 2017-03-10
        copyright            : (C) 2017 by Zoran Cuckovic
        email                : 
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

__author__ = 'Zoran Cuckovic'
__date__ = '2017-03-10'
__copyright__ = '(C) 2017 by Zoran Cuckovic'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'



from PyQt5.QtCore import QCoreApplication


from qgis.core import (QgsProcessing,
                       
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,

                       #individual files
                       QgsProcessingOutputRasterLayer,

                       
                      QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber,
                      QgsProcessingParameterField,
                       QgsProcessingParameterEnum ,
                      QgsProcessingParameterFile,

                      QgsProcessingException,

                       QgsMessageLog)

from processing.core.ProcessingConfig import ProcessingConfig


from osgeo import gdal
import numpy as np
from .modules import doNetworks as nt



class CostZones(QgsProcessingAlgorithm):

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.


    TRACEBACK = 'TRACEBACK'
    COST_SURF = 'COST_SURF'
    
    MAX_COST = 'MAX_COST'
    OUTPUT_RASTER = 'OUTPUT_RASTER'

    def initAlgorithm(self, config):

        
        self.addParameter(QgsProcessingParameterRasterLayer
                          (self.COST_SURF,
            self.tr('Cumulative cost raster')))
            
        self.addParameter(QgsProcessingParameterRasterLayer
                          (self.TRACEBACK,
            self.tr('Traceback raster')))
       
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_COST,
            self.tr('Maximum accumulated cost'),
            QgsProcessingParameterNumber.Double, 
            defaultValue = 0))
        

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_RASTER,
            self.tr("Output file")))


    def processAlgorithm(self, parameters, context, feedback):
        
        cst = self.parameterAsRasterLayer(parameters,self.COST_SURF, context)
        tcb = self.parameterAsRasterLayer(parameters,self.TRACEBACK, context)
        max_cst = self.parameterAsDouble(parameters,self.MAX_COST, context)

        output_path = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER,context)

        if cst.source() == tcb.source():
            try: d = gdal.Open(tcb.source().replace ('.', '_traceback.' )  )             
            except : 
                err = "Traceback raster was not found !"
                feedback.reportError(err, fatalError = True)
                raise Exception(err)
            
        else: d = gdal.Open(tcb.source())           
        r=d.ReadAsArray().astype(int)
        
        d2 = gdal.Open(cst.source())
        c=d2.ReadAsArray().astype(float)
        
        
       # Nodata = -2 (impossible index) ==> set to self link (-1 for Scikit)
        nodata_mask = r==-2
            
        if max_cst: #assign out of reach to nodata
            nodata_mask = np.logical_or(nodata_mask, c > max_cst )
# TEST HERE IF EVERYTHING IS MASKED !!
         
        r[nodata_mask]=-1 #Artificial peaks
    
        #Reformat Scikit indexing to numpy (Scikit has totaly arbitrary indexing...) ....
        r[r >3 ] +=1
        r[r==-1] = 4
       
        y,x =np.unravel_index (r, (3,3))
        y_parent, x_parent = np.indices(r.shape) 
       
       #again some acrobacy with scikit indexes ...
        y_parent -= (y-1); x_parent -= (x-1)
       
      
       # x_parent, y_parent = nt.merge(r, x_parent, y_parent, merge)
           
       # give ids - simple numpy indices
        #child_ids, steps = nt.assign_ids(x_parent, y_parent, give_step = True )
        #slope = nt.slope(r, x_parent, y_parent)
        #degrees = nt.degrees(x_parent, y_parent)
     
        #mins = nt.accum_avg (slope,  x_parent, y_parent, steps, degrees)
      
        #gives -1 to non-peaks
        
        peaks = nt.peaks (x_parent, y_parent, return_ids=True)
        temp = np.zeros_like(peaks)
        
        cnt_start = np.count_nonzero(peaks == -1)
     
        cnt = 1
        while cnt : 
            
            temp[:]= peaks[y_parent, x_parent]
                       #propoagate peak ID
            peaks[:] = temp[:]
            
            cnt = np.count_nonzero(peaks == -1)
           
            if feedback.isCanceled(): return None
            feedback.setProgress( int( 100 - cnt/cnt_start * 100))
            
  
        peaks[nodata_mask] = -999
        
               
        out = peaks
        
        driver = gdal.GetDriverByName('GTiff')

        # FORMAT : should be flexible: int for ranks etc
        outDs = driver.Create(output_path,
                              d.RasterXSize, d.RasterYSize,1,
                              gdal.GDT_Float32)       
        outDs.SetGeoTransform(d.GetGeoTransform())
        outDs.SetProjection(d.GetProjection())
       
        outDs.GetRasterBand(1).WriteArray(out)


        results = {}
        
        for output in self.outputDefinitions():
            outputName = output.name()
                
            if outputName in parameters :
                results[outputName] = parameters[outputName]

    
        return results
    
    def name(self):
         return 'Least cost zones'    
     
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
        return 'Movement analysis'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CostZones()
