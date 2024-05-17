
from PyQt4.QtCore import *
from PyQt4.QtGui import * #this is only for the message box !!
from qgis.core import *
from processing.tools.vector import VectorWriter
import numpy as np
import doNetworks as nt

class TopoGraph:


    # tu sve radnje!!!
    #assembly etc
    def __init__(self):
        self.nodes = {} #Fields : class_i, ID_tree_i, step_i, z
        self.edges = {} #Fields: slope_f
        self.relations={}
        self.entities={} 
        
        # where: _i = integer, _f = float


    """
    Nije dobro: jedno je vektor, a drugo su podaci u rasteru!
    bespotrebno puni memoriju s podacima koji su u rasteru

    == za vector fields: connect shapefile with raster (=Postgis ??)
    """

    def assembly(self,  parents_x, parents_y,
                 ids = None, steps = None, ranks=None,
                 exclude_id=None):
    
        # to do : convert to dict
        # b = {name:a[name] for name in a.dtype.names}
        # or zip + enumerate
        tree = None
        for j in xrange(ids.shape[0]):
            for i in xrange(ids.shape[1]):

                source = (i,j)    
                target = (parents_x[j,i], parents_y[j,i])
                
                if isinstance(ids, np.ndarray):
                    if ids[j,i] == exclude_id: continue
                    tree= ids[j,i]
                
              
# LOSE!!! svaki put mask tre!!!???
                
          #      mask = np.logical_and( ids == tree, ranks== rank)      

            # FOR BRANCHES : NOT USED !!
##                pts = np.hstack(parents_x[mask], parents_y[mask])
##                #sort for proper drawing
##                #actually can be done without sort : only debase all to zero
##                pts = pts[np.argsort(steps[mask]))
            # --------------------------------
                
                self.nodes[source]= {"points":[source, target]}#to initialise sub dict

                if tree is not None: self.nodes[source]["ID_tree_i"]= tree 

                if isinstance(steps, np.ndarray):
                    self.nodes[source]["step_i"]=steps[j,i]
                
                if isinstance(ranks, np.ndarray):
                    self.nodes[source]["rank_i"]= ranks[j,i]
                
                try:    self.relations[source].append(target)
                except: self.relations[source] = [target]
                
                

            #CANNOT : entities get erased on merge !!                    
                   # self.entities[j*raster_size_x + i]={'point' : target}
        #nije dobro: entities se popunjava nakon merge, ali ako nema merge !!??

# not working!!! cant delete on iteration
    def clean(dict_object): #remove nodes without ID: makes problems..
        if dict_object=='nodes':
            for key, sub_dict in n.items():
                if not 'ID_tree_i' in sub_dict: del n[key]
        elif dict_object=='edges':
            # DO!
            pass

    def RASTER_______merge_peaks(self, radius, DEM_array):

        entity_id=0

        raster_size_x = len(DEM_array[0])
        
        #cannot use Z values from nodes: no relations...
        for k in self.nodes:
            if self.nodes[k]['class_i']==0:
                x,y=k

                z = DEM_array[y,x]
                max_z = z
                source =0
                for j in xrange(y- radius, y+ radius + 1):
                    for i in xrange(x- radius, x+ radius +1):
                        if j<0 or i<0: continue   #Numpy can see negative indices !!!

                        try: z2= DEM_array[j,i]
                        except: continue # out of raster!
                            
                        if z2 > max_z:
                            max_z = z2    
                            source = (i, j)
                            
                if source:           
                    self.nodes[k]['class_i'] = 1 # has one source, NOT PEAK ANYMORE
                    self.edges[source,k]= {'slope_f': max_z - z}
                    try: self.relations[source].append(k) 
                    except: self.relations[source]=[k]
            #choose entities AFTER MERGE
                else :
                    #fomula for ids : 0 rests as unclassified
                    entity_id += 1
                    self.entities[entity_id]={'point' : k, 'saddles':[], 'nodes':[]}


    def RASTER______BFS_traversal(self):# breadth first search

        
        for k in self.entities: 
                 
            id_root = k #given in merge_peaks routine
            key= self.entities[k]['point']
            

            self.nodes[key]["step_i"]=0
            self.nodes[key]["ID_tree_i"]= id_root
                 
            cnt1 = 1; cnt2 = 0; step=0
            # maintain a queue of paths
            queue = []
 #           parent= {} # to nicemu ne sluzi !!!!!!!!

            # push the first path into the queue
            queue.append(key)
            #except: continue #IMA VRHOVAZ KOJI NISU U GRAFU ???

            while queue:
                # get the first path from the queue
                node = queue.pop(0)
                # get the last node from the path
    ##            # path found  PATH FINDING
    ##            if node == end:
    ##                return path
                # ------ counting steps ----------------
                if cnt2 == 0:
                    step += 1
                    cnt2 = cnt1
                    cnt1 = 0
                
                cnt2 -= 1 # record popped node
                # --------------------------------------
                # enumerate all adjacent nodes, construct a new path and push it into the queue
                is_sink=True           
                for adjacent in self.relations.get(node, []):
                
                   # parent[adjacent]= node
                    queue.append(adjacent)
                    
        #            out_list.append ([[adjacent, node], id_root, step, node, adjacent])
                    cnt1 += 1
                    is_sink= False
                    
                    self.nodes[adjacent]["ID_tree_i"]= id_root
                    self.nodes[adjacent]["step_i"]= step
                    
                    self.edges[node,adjacent]["ID_tree_i"]=id_root
                    self.entities[id_root]['nodes'].append(adjacent)
                    
                if is_sink:
                    #register sinks - good to have
                    #NOT Working!!!
                    self.nodes[node]['class_i'] = -9
                    
       # QMessageBox.information(None, "podatak:", str(self.relations))
    
    # THIS CREATES A NEW GRAPH (and takes the full topographic network)
    #repeating most of the code from assembly : but on dict, not on an array!
    def SN_assembly (self,ids , elevations):

        


        #step 1 - borders

        for j in ids.shape[0]:
            for i in ids.shape[1]:

                ix1 =[j,i]

            #find opposite = border
                for m in [(1,0),(0,-1)]: #no diagonal ! no-need, recessed pixels are always too high

                    ix2 = [ + m[1], i+ m[0]]

                    id1 = ids[ix1]; id2 =  ids[ix2]
                    
                    if id2 != id1:

                        e1 = elevations[ix1]; e2 = elevations[ix2]

                        node, tree = ix1, id1 if e1 < e2 else ix2, id2
                    
                        try: self.nodes[node]=[id1,id2] #fill new graph
                            
                        except: continue #out of limits...

        #step 2, connect
        
        for n in self.nodes:
        #min z - trazi najdublju
            
            i,j = n
            min_z = DEM_array[j,i] 
            cnt = 0
            
            for jj in xrange(j- 1, j+2): # allows diagonal connections !
                for ii in xrange(i- 1, i+ 2):
                
                    if (ii,jj) in self.nodes : 
                        z2 = DEM_array[jj,ii]
                        
                        if z2 < min_z  :
                            min_z = z2
                            source=(ii,jj)
                            cnt +=1
                                  
            if cnt > 0:

                self.nodes[n]["class_i"] = cnt

                try:    self.relations[source].append(n)
                except: self.relations[source] = [n]

                self.edges[source,n]= {'slope_f': z2 - min_z}
        #QMessageBox.information(None, "podatak:", str(c))

                # 3 --------------------- BORDER LINES ------------------------

  
    


        

    def write_shp (self, file_name,
                 coordinate_ref_system, gdal_geo_transform ,
                 center_pixel=True, shp_type = 'line' ):

        #line = {points: [(4,6), field: val ....}

# this should be attribute of graph !!
        pix = gdal_geo_transform[1]
        half_pix = pix/2 if center_pixel else 0
        
        raster_x_min = gdal_geo_transform[0]
        raster_y_max = gdal_geo_transform[3]

# -----------------------------------------

                          
        keys=[]
        fields = QgsFields() #there's a BUG in QGIS here (?), normally : fields = .... 

##        for key in dict_lines[dict_lines.keys()[0]]:# take ANY record to read fields 
##            if key != 'points':
##            
##                f_name=str(key[0:-2])
##
##                if key[-2]=="_i":
##                    fields.append(QgsField(f_name, QVariant.Int,'integer',10))
##                elif key[-2]=="_f":
##                    fields.append(QgsField(f_name, QVariant.Double,'double',10,5))
##                else :
##                    fields.append(QgsField(f_name, QVariant.String, 'string',50))
##                    
##                keys.append([key, f_name, key[-2]])

        fields.append(QgsField("tree", QVariant.Int,'integer',10))
        fields.append(QgsField("rank", QVariant.Int,'integer',10))
        fields.append(QgsField("step", QVariant.Int,'integer',10))

        if shp_type=='line' : layer_type= 2
        elif shp_type=='point': layer_type= 1

        
        # coords are in a string from gdal : QGIS don't eat it ...
        crs = QgsCoordinateReferenceSystem()
        crs.createFromWkt(coordinate_ref_system)
        writer = QgsVectorFileWriter( file_name, None, fields,
                                      layer_type, crs) #, "ESRI Shapefile"
                                                #CP... = encoding

        if writer.hasError() != QgsVectorFileWriter.NoError:
            QMessageBox.information(None, "ERROR!", "Cannot write network file (?)")
            return 0
           

        for r in self.nodes :
     
           # coords=[r]+graph[r] # FOR COMPEX LINES !!
            coords= self.nodes[r]['points']
            pts=[]
            for c in coords: # for each target node - new line !!!

               #pts=[  QgsPoint (r[0]*pix + raster_x_min + half_pix, (raster_y_max - r[1]*pix) - half_pix)]
                pts.append(QgsPoint (c[0]*pix + raster_x_min + half_pix, (raster_y_max - c[1]*pix) - half_pix))              
            
            feat = QgsFeature() # create a new feature

            if shp_type == 'line': feat.setGeometry(QgsGeometry.fromPolyline(pts))
            elif shp_type == 'point':feat.setGeometry(QgsGeometry.fromPoint(pts[0]))
        ##            # do not cast ID to string: unicode problem  -- angle * distance in pixels -- distance * pixel_size
        ##            #feat.setAttributes([ str(r[0]), str(r[3]), bool(r[6]), float(r[7] * r[8]),  ])
                
##            if keys:
##                feat.setFields(fields)
##                for key in keys:  #list of keys and field names (key - [-2] + type of value)
##                    try:
##                        val= dict_lines[r][key[0]]
##                        if key[2]=="_i": v= int(val)
##                        elif key[2]=="_f": v= float(val)
##                        else : v= str(val)
##                        feat[key[1]] = v#first and last give the name
##                    except: pass
            feat.setFields(fields)

    #TEMPORARY --- DANGEREOUS !!
            try:
                feat['tree'] = int(self.nodes[r]['ID_tree_i'])
                feat['step'] = int(self.nodes[r]['step_i'])
                feat['rank'] = int(self.nodes[r]['rank_i'])
            except: pass
      
                          
            writer.addFeature(feat) 
       #     del feat

        del writer
        layer = None
        return file_name + ".shp"
                              

    def getNodes (self): return self.nodes
    # ----------------------   NOT USED ------------------------------

    def addVertex(self,key):
        self.numVertices = self.numVertices + 1
        newVertex = Vertex(key)
        self.vertList[key] = newVertex
        return newVertex

    def getVertex(self,n):
        if n in self.vertList:
            return self.vertList[n]
        else:
            return None

    def __contains__(self,n):
        return n in self.vertList

    def addEdge(self,f,t,cost=0):
        if f not in self.vertList:
            nv = self.addVertex(f)
        if t not in self.vertList:
            nv = self.addVertex(t)
        self.vertList[f].addNeighbor(self.vertList[t], cost)

    def getVertices(self):
        return self.vertList.keys()

    def __iter__(self):
        return iter(self.vertList.values())
