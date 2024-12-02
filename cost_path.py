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
from qgis.core import (QgsProcessing,
                    QgsField, QgsFields,QgsPoint,QgsFeature,QgsGeometry,
                    QgsFeatureSink,
                    QgsWkbTypes,
                   
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorDestination,
                        QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum)


from osgeo import gdal
import numpy as np
    
IMPORT_ERROR = False
try: from skimage import graph
except ImportError : IMPORT_ERROR = True 

from .modules import Raster as rst 
from .modules  import Points as pts
from .modules import doNetworks as nt


class CostPath(QgsProcessingAlgorithm):
        # Constants used to refer to parameters and outputs. They will be
       # used when calling the algorithm from another algorithm, or when
       # calling from the QGIS console.
    
    FRICTION_SURF = 'FRICTION_SURF'
 # SPEED_TOGGLE = 'SPEED_TOGGLE'
    DEPARTURES = 'DEPARTURES'
    DESTINATIONS = 'DESTINATIONS'
    RADIUS = 'RADIUS'
    OUTPUT = 'OUTPUT'
    ANALYSIS_TYPE = 'ANALYSIS_TYPE'
  
    ANALYSIS_TYPES = ['NOT IMPLEMETED']
   

    def initAlgorithm(self, config=None):
        
        if IMPORT_ERROR :  raise Exception (
                "Scikit Image not installed ! Cannot proceed further.")      
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.FRICTION_SURF,
                self.tr('Friction surface')
            ) )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.DEPARTURES,
                self.tr('Departure points'),
                [QgsProcessing.TypeVectorPoint]
            ))
            
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.DESTINATIONS,
                self.tr('Destination points'),
                [QgsProcessing.TypeVectorPoint]
            ))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr('Maximum distance'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10000))
        
        """         
        self.addParameter(QgsProcessingParameterEnum (
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.ANALYSIS_TYPES, 
            defaultValue=0))
        """  

        self.addParameter(QgsProcessingParameterFeatureSink(
                self.OUTPUT,
            self.tr("Least cost paths")))

    def processAlgorithm(self, parameters, context, feedback):
               
        friction = self.parameterAsRasterLayer(parameters,self.FRICTION_SURF, context)
        departures = self.parameterAsSource(parameters, self.DEPARTURES, context)
        destinations = self.parameterAsSource(parameters, self.DESTINATIONS, context)
        radius =self.parameterAsInt(parameters, self.RADIUS, context)
        
      #  analysis_type = self.parameterAsInt(parameters,self.ANALYSIS_TYPE,context)
        
           
        dem = rst.Raster(friction.source())
               
        dep_pts = pts.Points(departures)
        dest_pts = pts.Points(destinations) 
                     
        dep_pts.take(dem.extent, dem.pix)
        dest_pts.take(dem.extent, dem.pix)
        
        # Swap for efficiency (this is valid only for ISOTROPIC approach)
        if dep_pts.count > dest_pts.count : 
            dep_pts, dest_pts = dest_pts, dep_pts
        
        if dep_pts.count == 0 or dest_pts.count == 0 :
            err= "  \n ******* \n ERROR! \n No destination/departure points in the chosen area!"
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err )   
                        # 0 : single raster, 1 : addition, 2 : minimum, etc.
       # dem.set_buffer(mode=0, live_memory = True)
        
        data = dem.open_raster() # entire raster !
        # cannot handle 0
        data[data < 0.000001]=0.000001
        
        # handle noData (cause they're like 0 for scikit !)
        # we *could* do this:  nodata_mask =  data == dem.nodata but nodata may not be assigned (nans etc)
        data[(data>0) == False]= 9**99 # Nan always gives False
            
        print ("Bad cells count: ", np.count_nonzero([data<0.0001]))
        
        #raster_y_min is broken !
        raster_x_min, raster_y_max = dem.extent[0], dem.extent[3]
                 
        # ============   prepare output
        
        fds = [("Departure", QVariant.String, 'string',255),
               ("Destination", QVariant.String, 'string',255),
               ("Cost", QVariant.Double, 'double',10,3)]

        qfields = QgsFields()
        for f in fds : qfields.append(QgsField(*f))
        
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                            qfields,
                            QgsWkbTypes.LineString,
                            dep_pts.crs)
           
               
        # Specify the size of the cell
        # cost = surface cost * cellsize
        #SciKit calls this ANISOTROPIC : not true !! it's only geometric correction!
        sample = (1.0, 1.0) # could be : (dem.pix, dem.pix) = pixel size x and y
        lg = graph.MCP_Geometric (data)
        
        dep_pts.network(dest_pts, override_radius_pix = radius/dem.pix)
        
        half_pix = dem.pix/2
        cnt = 1
        for key, ob in dep_pts.pt.items():
            
            pix_dep = [ob['pix_coord'][::-1]]
            
            pix_dest =[] 
            for key, tg in ob['targets'].items() : 
                
                pix_dest += [ tg['pix_coord'][::-1]]
            
            if not pix_dest : continue # skip if no destinations
                                             
           
       
            # Calculate the least-cost distance from the start cell to all other cells
            lcd, backtrack = lg.find_costs(starts=pix_dep, ends = pix_dest) 
            
# This is slow !?
            for end in pix_dest:
                #find traceback path
                tcb = lg.traceback(end)
                #to obtain geographical distance from pixelated :  * dem.pix)
                # swap x/y ==> [:,::-1] 
                line_pix = np.array(tcb)[:,::-1] * dem.pix 
             
                line_pix[:,0] += raster_x_min + half_pix
                line_pix[:,1] = raster_y_max - line_pix[:,1] - half_pix
                
               
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(*i) for i in line_pix]))

                feat.setFields(qfields)
                feat['Departure'] = ob["id"]
                
                #find matching target id (not guaranteed that scikit will be in order)
                for key, tg in dest_pts.pt.items(): 
                    if tg['pix_coord'][::-1] == end : break
   
                feat['Destination'] = tg['id']
                feat['Cost'] =  float(lcd[end]) # the last point.                
           
                sink.addFeature(feat, QgsFeatureSink.FastInsert) 
                
            if feedback.isCanceled(): return None    
            feedback.setProgress(int(cnt / len(dep_pts.pt) * 100))
            cnt += 1
   
        return {self.OUTPUT: dest_id}



    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Least cost paths'

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
        return CostPath()
