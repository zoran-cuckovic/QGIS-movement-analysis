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

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                        QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum)


from osgeo import gdal
import numpy as np
from skimage import graph

from .modules import Raster as rst 
from .modules  import Points as pts
from .modules import doNetworks as nt


class CostSurface(QgsProcessingAlgorithm):
        # Constants used to refer to parameters and outputs. They will be
       # used when calling the algorithm from another algorithm, or when
       # calling from the QGIS console.
    
    FRICTION_SURF = 'FRICTION_SURF'
      # SPEED_TOGGLE = 'SPEED_TOGGLE'
    POINTS = 'POINTS'
    OUTPUT = 'OUTPUT'
    RADIUS = 'RADIUS'
    INNER_RADIUS = 'INNER_RADIUS'
    ANALYSIS_TYPE = 'ANALYSIS_TYPE'
    COMBINE_MODE = 'COMBINE_MODE'
       ##Centripetal=boolean True
       ##Peripheric=boolean True
       ##Anisotropic=boolean False
       ##Anisotropic_DEM=raster 
    ANALYSIS_TYPES = ['cost_surface' , 'drainage']
    COMBINE_MODES = ['addition', 'min', 'max']
   

    def initAlgorithm(self, config=None):
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.FRICTION_SURF,
                self.tr('Friction surface')
            ) )
        """
        self.addParameter(QgsProcessingParameterBoolean(
            self.SPEED_TOGGLE,
            self.tr('Using speed vaules instead of friction'),
            False, False)) 
        """
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.POINTS,
                self.tr('Destination points'),
                [QgsProcessing.TypeVectorAnyGeometry]
            ))
    
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr('Radius'),
            0, # QgsProcessingParameterNumber.Integer = 0
            5000, False, 0, 99999))
            
            
        self.addParameter(QgsProcessingParameterNumber(
            self.INNER_RADIUS,
            self.tr('Inner radius'),
            0, # QgsProcessingParameterNumber.Integer = 0
            0, False, 0, 99999))
            
                
        self.addParameter(QgsProcessingParameterEnum (
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.ANALYSIS_TYPES,
            defaultValue=1))
            
        self.addParameter(QgsProcessingParameterEnum (
            self.COMBINE_MODE,
            self.tr('Cumulation mode'),
            self.COMBINE_MODES,
            defaultValue=0))
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Output file")))

    def processAlgorithm(self, parameters, context, feedback):
        

        Anisotropic = 0 # NOT IMPLEMENTED
        
            
        Centripetal = 1
        Peripheric = 1

        friction = self.parameterAsRasterLayer(parameters,self.FRICTION_SURF, context)
        points = self.parameterAsSource(parameters, self.POINTS, context)
        #speed = self.parameterAsBool(parameters,self.SPEED_TOGGLE,context)
        speed = False # NOT SMART !!
        #thick = self.parameterAsBool(parameters,self.THICK,context)
        radius = self.parameterAsInt(parameters,self.RADIUS,context)
        inner_buffer = self.parameterAsInt(parameters,self.INNER_RADIUS,context)
        analysis_type = self.parameterAsInt(parameters,self.ANALYSIS_TYPE,context)
        cumul_mode = self.parameterAsInt(parameters,self.COMBINE_MODE,context)
        output_path = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
    
        dem = rst.Raster(friction.source(), output_path)
               
        points = pts.Points(points)
              
        points.take(dem.extent, dem.pix)
        if points.count == 0:
            err= "  \n ******* \n ERROR! \n No viewpoints in the chosen area!"
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err )   
                        # 0 : single raster, 1 : addition, 2 : minimum, etc.
        dem.set_buffer(mode=cumul_mode+1, live_memory = True)
        
        dem.set_master_window(radius, background_value=999999)
        
        dem.set_mask(radius//dem.pix) # pixelated radius...
            # can be adjusted individually, for each point - NOT USEFUL ?
            # eg. pt[id1]['radius'] (already pixelated radius)
        
        # We operate on standardised window size 
        # radius_pix is assiged upon set_master_window()
        departs = [(dem.radius_pix, dem.radius_pix), (dem.radius_pix + 100, dem.radius_pix + 100)]
            
                                      
        if Anisotropic: 
            dem_aniso = rst.Raster(Anisotropic_DEM)
            dem_aniso.set_master_window(radius_pix , background_value= 999999)
        
        # Specify the size of the cell
        # cost = surface cost * cellsize
        #SciKit calls this ANISOTROPIC : not true !! it's only geometric correction!
        sample = (1.0, 1.0) # could be : (dem.pix, dem.pix) = pixel size x and y
        
        pt = points.pt
        
        for cnt, id1 in enumerate(pt):
            
            
            pix_point = pt[id1]['pix_coord']
                   #determine the standard window size
                     
            
            dem.open_window (pix_point) #"radius is set as master window
            data= dem.window
            
            # cannot handle 0
            data[data < 0.000001]=0.000001
            
            #REVERSE for speed (higher the better) === NOT USED =====
            # SHOULD BE data = 1/data
            # OLD NOT CORRECT !!! data -=np.max(data); data *-1
            if speed : data = 1/data # NOT USED !!
            
            # handle noData (cause they're like 0 for scikit !)
            # we *could* do this:  nodata_mask =  data == dem.nodata but nodata may not be assigned (nans etc)
            data[(data>0) == False]= 9**99 # Nan always gives False
            
            print ("Bad cells count: " , np.count_nonzero([data<0.0001]))
            
            
            # From the cost-surface create a 'landscape graph' object which can then be
            # analysed using least-cost modelling
            
            if Anisotropic:
                
               dem_aniso.open_window (pix_point)
            #graph.MCP_Geometric = isotropic!
               lg = MCP_Aniso(dem_aniso.window , sampling=sample)
               lg.assign_isotropic_cost(data)
               
            else: 
                lg = graph.MCP_Geometric (data , sampling=sample)
                
          
            # Calculate the least-cost distance from the start cell to all other cells
            lcd, traceback = lg.find_costs(starts=departs)
            
            if analysis_type == 1: #'DRAINAGE'
            
                # print (np.unravel_index(traceback + 1, (3,3)))
                
                # TopoNetworks create network (negative for draining)
                #  x_parent, y_parent = nt.links(lcd * -1) 
                
                 #Scikit has totaly arbitrary indexing ....
                traceback[traceback >3 ] +=1
                traceback [traceback==-1] =4
                
                y,x =np.unravel_index (traceback, (3,3))
                y_parent, x_parent = np.indices(traceback.shape) 
                
                #again some acrobacy with scikit indexes ...
                y_parent -= (y-1); x_parent -= (x-1)
                
                parents_flat = np.ravel_multi_index((y_parent,x_parent), 
                               traceback.shape).flatten()
                
                """ NOT USED : topo networks
                ids, steps = nt.assign_ids(
                    x_parent, y_parent, give_step = True )
                
                #for average accum !
                #slope = nt.slope(r, x_parent, y_parent)
                
                #not used (node degrees)
                #degrees = nt.degrees(x_parent, y_parent)
                
                accum = np.ones (steps.shape)
                # 1  NICE RESULT
                # leave sinks only = those not in parent index  :)
                if Peripheric: accum[y_parent, x_parent]=0
                
                 # 3   accum top : INTERESTING
                #accum = nt.degrees(x_parent, y_parent)
                
                # ACCUMULATION ALGO NOT CORRECT !!
                out = nt.accum(x_parent, y_parent, steps, 
                                        accum, upwards = Centripetal)
                                        
                                        
               
                """
                #CUSTOM ACCUMULATION
                accum_values = np.ones(traceback.shape)
                live_cells = np.ones(traceback.shape)
                sinks = np.ones(traceback.shape)
                
                # test NUMBA
                #test_ac= accumulation_numba(accum_values, x_parent, y_parent) 
                
                
                # mark only sinks ! ( parents are not sinks :) 
                sinks[y_parent, x_parent]= 0
                # HERE DISTANCE DELETE !!
                # mask[distances > x] = 0
                
                children = np.arange(traceback.size)
                missing = np.in1d(children, parents_flat, invert = True) 
                sinks2 = children[missing]
                
                child_y, child_x = np.indices (traceback.shape)
           
                # center cell is always 1 ... (bit costly to count...)
               # while np.count_nonzero(live_cells) > 1:
            
                while sinks2.size > 0 :
                    
                                    
                    """ OLD METHOD nicer but slow
                    mask = sinks == 1
                    s_y, s_x = y_parent[mask],x_parent[mask]
                    #add at - super SLOW
                    np.add.at(accum_values,(s_y, s_x), accum_values[mask])
                    """
                    
                    # bincount does not use indexing !!! ???
                    # it returns the entire sequence of bins 
                    # EVEN THE VALUES NOT SUPPLIED !!
                    # eg. for groups 2,2,3,3,5,8 =>0,1,2,3,4,5,6,7,8
                    # we have to use the entire sequence of parent Ids to ensure correct indexing
                    v = np.bincount(parents_flat, accum_values.flat).astype(int)
                    # SHENNANIGAN : the squence does not start or end with a specific number
                    idx = np.unique(parents_flat[sinks2])   #sinks2[mask2]
                        
                    #print (v.size, accum_values.size, parents_flat.size)
                    accum_values.flat[idx] += v[idx]
                    #accum_values.flat[idx] += step
                    # find sinks - those not being someones parent
                    # ?? this is not working : missing = np.in1d(idx, parents_flat[idx], invert = True)                    
                    parents_flat[sinks2]= 0 # have to use the entire array
                    missing = np.in1d(idx, parents_flat, invert = True) 
                    sinks2 = idx[missing]
                    
                                        
                out = accum_values 
                                           
            else : #' SIMPLE COST SURF'
                out = lcd
                
            if inner_buffer: 
                out[dem.mx_dist < inner_buffer/dem.pix]=0
            
            # 4 FOR DISTANCES
            # acc/= lcd 
            
            
            #   creating SAGA source point ...
            #c = np.zeros(data.shape)
            #c[radius_pix, radius_pix] = 1
            
                   
          
            dem.add_to_buffer(out)
            
            feedback.setProgress(int(cnt / points.count * 100))
        
      
        dem.write_output(output_path)
    
        return {self.OUTPUT: output_path}


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Cost surface'

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
        return CostSurface()
