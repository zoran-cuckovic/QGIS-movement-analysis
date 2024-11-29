# -*- coding: utf-8 -*-

"""
!! TODO NODATA HANDLING !! =COST MAX

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
try:
    from skimage import graph
except: pass
from .modules import Raster as rst 
from .modules  import Points as pts
from .modules import doNetworks as nt

def drainage(traceback_skimage):
    traceback = traceback_skimage
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
        
    return accum_values

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
    ANALYSIS_TYPES = ['Accumulated cost surface' , 'Accumulated paths']
    COMBINE_MODES = ['exclusive','addition', 'min', 'max', 'average']
   

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
                [QgsProcessing.TypeVectorPoint]
            ))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr('Maximum distance'),
             defaultValue=10000))          
            
        self.addParameter(QgsProcessingParameterNumber(
            self.INNER_RADIUS,
            self.tr('Inner buffer'),
             defaultValue=0))
            
                
        self.addParameter(QgsProcessingParameterEnum (
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.ANALYSIS_TYPES,
            defaultValue=0))
            
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
      #  points.clean_parameters()
        points.take(dem.extent, dem.pix)
        if points.count == 0:
            err= "  \n ******* \n ERROR! \n No viewpoints in the chosen area!"
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err )   
        
        pt = points.pt # for convenience
            
        # 0 : single raster, 1 : addition, 2 : minimum, etc.
        # average mode = SPECIAL
        dem.set_buffer(mode=(cumul_mode if cumul_mode < 4 else 1), live_memory = True)
        
        
        if cumul_mode >= 4 :# AVERAGE :  track the number of visits per pixel
            #This is a hack : need a file on the disk to initialise
            dem_counter = rst.Raster(friction.source(), output_path)
            # Must be live memory (othewise writes to disk !)
            dem_counter.set_buffer(mode= 1, live_memory = True)
            dem_counter.set_master_window(radius, background_value=0)
            dem_counter.set_mask(radius//dem.pix)
            
            # we assign an empty numpy matrix
            dem_counter.result = np.zeros(dem.size)
            
            counter_mask = np.ones(dem_counter.window.shape)
            if inner_buffer:
                counter_mask[dem_counter.mx_dist < inner_buffer/dem.pix]=0
        
        
        # Specify the size of the cell
        # cost = surface cost * cellsize
        #SciKit calls this ANISOTROPIC : not true !! it's only geometric correction!
        sample = (1,1) # could be : (dem.pix, dem.pix) = pixel size x and y
        
        
        if cumul_mode: #otherwise the entire raster 
            dem.set_master_window(radius, background_value=0)
        
            dem.set_mask(radius//dem.pix) # pixelated radius...
            # can be adjusted individually, for each point - NOT USEFUL ?
            # eg. pt[id1]['radius'] (already pixelated radius)
        
            # We operate on standardised window size 
            # radius_pix is assiged upon set_master_window()
            departs = [(dem.radius_pix, dem.radius_pix)]
            

            """                            
            if Anisotropic: 
                dem_aniso = rst.Raster(Anisotropic_DEM)
                dem_aniso.set_master_window(radius_pix , background_value= 999999)
            """
           
            for cnt, id1 in enumerate(pt):
                
                
                pix_point = pt[id1]['pix_coord']
                       #determine the standard window size
                         
                
                dem.open_window (pix_point) #"radius is set as master window
                data= dem.window
                
                # cannot handle 0
                data[data < 0.000001]=0.000001
                
                #REVERSE for speed (higher the better) === NOT USED =====
               
                #if speed : data = 1/data # NOT USED !!
                
                # handle noData (cause they're like 0 for scikit !)
                # we *could* do this:  nodata_mask =  data == dem.nodata but nodata may not be assigned (nans etc)
                data[(data>0) == False]= 9**99 # Nan always gives False
                
                print ("Bad cells count: " , np.count_nonzero([data<0.0001]))
                
                # From the cost-surface create a 'landscape graph' object which can then be
                # analysed using least-cost modelling
                
                # if Anisotropic:
                    
                #    dem_aniso.open_window (pix_point)
                # #graph.MCP_Geometric = isotropic!
                #    lg = MCP_Aniso(dem_aniso.window , sampling=sample)
                #    lg.assign_isotropic_cost(data)
                   
                # else: 
                
                lg = graph.MCP_Geometric (data )
              
                # Calculate the least-cost distance from the start cell to all other cells
                lcd, traceback = lg.find_costs(starts=departs)
                
                if analysis_type == 1: #'DRAINAGE'
                    
                    out = drainage (traceback)
                                               
                else: out = lcd
                    
                    
                if inner_buffer:
                    out[dem.mx_dist < inner_buffer/dem.pix]=0
                
                # 4 FOR DISTANCES
                # acc/= lcd 
                
                
                #   creating SAGA source point ...
                #c = np.zeros(data.shape)
                #c[radius_pix, radius_pix] = 1
                       
              
                dem.add_to_buffer(out)
                
                
                if cumul_mode >= 4 :
                    dem_counter.open_window (pix_point) 
                    dem_counter.add_to_buffer(counter_mask)
                     
                if feedback.isCanceled(): return None
                feedback.setProgress(int(cnt / points.count * 100))
                
                
            
        else: # EXCLUSIVE
            
            data = dem.open_raster()
            lg = graph.MCP_Geometric (data , sampling=sample)
         
            lcd, traceback = lg.find_costs(
                # extract coord from dict ==> reverse x / y [::-1]
                        starts=[ pt[i]['pix_coord'][::-1] for i in pt ])
            
            dem.result = traceback 
            traceback_path = output_path.replace('.','_traceback.')
            dem.write_output(traceback_path)
            
            if analysis_type == 1: #'DRAINAGE'
                
                lcd = drainage (traceback)
                                           
            dem.result = lcd
            
        
        if cumul_mode >= 4: # MUST BE IN LIVE MEMORY MODE
            
            dem.result/= dem_counter.result
      
        dem.write_output(output_path)
        
        
    
        return {self.OUTPUT:None} #prevoiusly  ___ : output_path


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Least cost surface'

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
