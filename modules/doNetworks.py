

from osgeo import gdal    #, ogr
import numpy as np
# from numpy.lib.stride_tricks import as_strided 


'''
SPEED ! ufunc.at is slow (https://github.com/numpy/numpy/issues/5922)
use bincount or accumarray or numpy groupies


Window fitting for matrix borders
radius = distance in pix from the center 
diameter = radius * 2 + 1 

NB, numpy tolerates too large indices  eg. [3 : 9999...]

NUMPY MOVING WINDOW

>>> arrtrans2 = arr[::2, ::2] + arr[::2, 1::2] + arr[1::2, ::2] + arr[1::2, 1::2]


Where ::2 and 1::2 are translated by 0, 2, 4, ... and 1, 3, 5, ... respectively.

'''

def views (indices=False):

    """
    indices:
    0  1  2
    3  4  5
    6  7  8
    """

    v=[ [np.s_[:-1, :], np.s_[1:, :]],
        [np.s_[:, :-1], np.s_[: , 1:]],
        [np.s_[:-1, 1:], np.s_[1:, :-1]],
        [np.s_[:-1, :-1], np.s_[1:, 1:]]  ]
      
    i = [(1,7), (3,5), (2, 6), (0,8)]

    return zip(v,i) if indices else v


def window (x, y, x_size, y_size, radius): 

    left, up = max(0, y-radius), max(0, x-radius)
    right, bottom  = min ( x_size -1,  x+radius), min(y_size -1, y +radius)
    
    return left, right, up, bottom
    

def degrees(x_parents, y_parents):

    d = np.zeros(x_parents.shape)
    np.add.at(d, (y_parents, x_parents), 1)
   
    #peaks have a self-link : must be lowered by 1 ...
    indices_y, indices_x  = np.indices(x_parents.shape)
    d[(x_parents == indices_x ) * (y_parents == indices_y) ] -= 1
    
    """
    for t in range(9): 
       # if t ==4 : continue
        msk_t = direction_matrix == t
        d[y_parents [msk_t], x_parents[msk_t]] += 1 
    """
    return d


def peaks (parents_x, parents_y, return_ids=False):
    #give nice IDs that can be translated into cell indices 
    child_ids = np.arange (parents_x.size).reshape(parents_x.shape).astype(int)
    
    #find tops (where indices of parents are not shifted)
    mask= child_ids == np.ravel_multi_index((parents_y , parents_x) , parents_x.shape)

    if return_ids :  
        child_ids[~mask]=-1 ; return child_ids
    
    else: return parents_x[mask], parents_y[mask]


"""

# == REORGANIZE  ==
# It shiuld take slope + aspect rasters, not DEM : above, only a method to make aspect !!

Find the heighest neighbour.
window = 1 pixel => larger sizes are problematic

Problem : multiple additional matrices

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CAN BE DONE WITH SAGA: gradient vector from surface !!
# AND Scipy.signal.convolve2D    https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.convolve2d.html
# numpy gradient ??



"""
def links (dem): 

    #dem =np.array([[2,3,5],[7,8,9],[1,5,2]])

    out = np.zeros(dem.shape).astype(int) 

    out[:]=4 #this is the flat index of the central pix

    temp = np.copy(dem)
    
    
    for v, ix in views(indices=True):

        #views and indices are in opposite pairs!
        a,b = v
        a_i, b_i = ix

        for i in [0,1]: #swapping
            
            # test the opposite side 
            if i: a, a_i, b, b_i = b, b_i, a, a_i 
          
            # correction for pixel diagonals : sqrt 2
            # ! diagonal indices are  even 
            if a_i in [0,2,6,8]:   
                
                #problem with zero division use multiplication (1/1.4142)
                hgt =  dem [a]+ (dem[b] - dem[a])*.7071
       
            else: hgt = dem[b]

            msk =  temp[a] < hgt   #[b]
                    
            out[a][msk]= b_i
            
            temp[a][msk]=hgt[msk] 

    
    # note that directions cannot be negative if 0 is top left : 
    # 0 has to be in the center of matrix, so  - radius [initialize to -1]
    # unravel is read only , cannot do -=
    
    y,x =np.unravel_index(out, (3,3))

    # translate links to indices 
    y_parent, x_parent  = np.indices(out.shape) 
    # -1 to center 
    y_parent += y-1;  x_parent +=  x-1

    return x_parent ,y_parent

def links__OLD (dem): #window = 1 pixel => larger sizes are problematic

# -------------- 1 directions --------------------------- 
# only one pix !

    r= dem
    dirs = np.zeros(r.shape).astype(int)
    
    #(np.arange(ysize)[: , None] , np.arange(xsize) [None,:])  )

    # correction for pixel diagonals
    
    rt = 1.414213562373095
    mx_corr = np.array([[rt, 1, rt],
                        [1,1,1],
                        [rt, 1, rt]])
                                    
    # more simple than to recalc window ...
    r_pad= np.pad(r, 1, 'constant', constant_values= -9999999)     

    # this may be inefficient, but we have to avoid creating additional arrays
    # that risk to saturate memory
    for j in range(1,r.shape[0]+1):
        for i in range(1, r.shape[1] +1):
           #FLAT , has to be unraveled to a 2D
           # take care of padding (j-=1, i-=1)!
            dirs[j-1,i-1]= np.argmax( (r_pad[j-1 : j+2, i-1: i+2] -  r_pad[j,i] ) 
                                                     / mx_corr)
                                                     
    
    
    # note that directions cannot be negative if 0 is top left : 
    # 0 has to be in the center of matrix, so  - radius [initialize to -1]
    #unravel is read only , cannot do -=
    
    y,x =np.unravel_index(dirs, (3,3))
    
        # translate links to indices 
    y_parent, x_parent  = np.indices(r.shape)  
    # -1 to center 
    y_parent += y-1;  x_parent += x-1
    
    return x_parent ,y_parent


"""
Topographic networks are structured as trees : 
we can do a simple propagation to simulate a breadth first algorithm  (child_id = parent_id)
It starts with an arbitary number of iterations, but will be rerun if ithere are unassigned ids.
For optimisation purposes the number of runs can be changed (iter = 30)

SLOW : test with mask over assigned ids

force break : premature exit, leaves unassigned nodes...
"""
def assign_ids (parents_x, parents_y,
                give_step = False,
                iterations = 30,
                force_break = False):
    
    #give nice IDs that can be translated into cell indices 
    child_ids = np.arange (parents_x.size).reshape(parents_x.shape).astype(int)
    
    #find tops (where indices of parents are not shifted)
    mask = child_ids == np.ravel_multi_index((parents_y , parents_x) , parents_x.shape)
   
  #this is only to monitor progress, could do without
    child_ids[ ~ mask]= -1

    if give_step:
        step = np.zeros(parents_x.shape).astype(int) 
   
    #arbitrary num of iterations - to avoid checking in each loop np.any...
    while iterations :   
        iterations -= 1
        #must lag behind propagating IDs
        #given to those areas not yet reached
        if give_step:   step[child_ids < 0] +=1
        
        #this is all that is needed ....
        child_ids=child_ids[parents_y, parents_x]
   
        #optimisation ?
        if iterations == 0 and not force_break:  
            if np.any(child_ids == -1) :  iterations=5 

    if give_step: return child_ids, step
    else: return child_ids
    
    
"""
Merge peaks with neighbours in a preset window
returns a list of all recieved peaks, including those that are not merged
"""
def merge (dem,  parents_x, parents_y, radius):  #vertical stack!
    """
    <<<PROBLEM 0 >>>>
    merging peaks is affecting the balance valleys vs peaks
    two merged peaks = one valley less !
    which implies changing the DEM !

    merge has to be done in parallel with valley merge ??
    passes = crossings of valley lines vs ridgelines
        

    #    <<< PROBLEM 1 >> NO! can jump if steps += parent step 
    # it jumps over pixels = too short steps !! + incompatible with one step algo
    # needs to make a reverse path ....= an optimal path algo !
    # here only insert a "false" parent index
    #       << SOLUTION  >>
    # Dijkstra is essentially a BFS - which is what we have already
    # we care only about elevation, not distance
    # which means the path has to take the highest "pass"  
    # which also means consistency with surface networks
    # so 1) find highest  common /border sink and 2) follow the network upwards to the merged node
    # BUT - not constrained by the window !!

    # << PROBLEM 2 >>
    # tends to produce long strings along edges : undesirabe
    # restrain search to [radius + 1  :   x_size + raidus - 1] 
    
     << PROBLEM 3 >>
    tracing one path from the peak to the neighbour is not compeletely correct
    adjacent nodes should connect to the path !
    
    ==== THIS IS ABOUT DENOISING DEM !! =========
    ====== to be implemented directly on DEM, before the network stuff
           eg. find peaks and apply a window search ! ==============

    Pytagoras ajustement !!!! = dist matrix

    """
    
    size = (radius*2 +1 , radius *2 +1)
    # it's the half of the matrix
    center =  np.ravel_multi_index ((radius, radius), size )
    
    tops_x, tops_y = peaks( parents_x, parents_y ) 
   
#   = int (((radius * 2 +1) ** 2  - 1) / 2)   -1 because it begins with 0

# so much simpler than adjusting windows (though some extra memory..)
    r_pad = np.pad(dem, radius, 'constant', constant_values= -9999999)     

    tops_x += radius; tops_y += radius #ajust
    
    for i,j in zip(tops_x, tops_y):
        
 
        m = np.argmax( r_pad[j -radius  :  j + radius+1 ,
                            i- radius  :  i +radius +1])
            
        if m != center:  
            
            iy, ix=np.unravel_index( m, size)
            
            j_p, i_p = j - radius, i-radius
            
            parents_x [j_p,i_p] = i_p + (ix - radius )
            parents_y [j_p,i_p] = j_p + (iy - radius  )


    return parents_x, parents_y
    

"""
NOT TESTED !!

Remove all multiple connections to leave only branches
= write self-reference at the top of each branch

1) propagate value from child to parent (only maximum)
2) compare normal values with shifted (one step is enough!)
"""
def break_branches(x_parent, y_parent, values):

    v2 = np.zeros(values.shape)
    out_y = np.copy(y_parent)
    out_x = np.copy(x_parent)
    
    np.maximum.at(v2, ( y_parent, x_parent), values)

    iy, ix = np.nonzero(values - v2[y_parent, x_parent])

    out_y[iy, ix]=iy; out_x[iy, ix]=ix

    return out_x, out_y

    
    
def accum (x_parent, y_parent, steps, accum_array , upwards = True) :
    # ------------------- ACCUMULATION  SIMPLE ---------------
    
    accum = accum_array

    # arr[mask][parents]+=1
    #mask = arr = 0  ; LOOP

     # OR USE STEPS DETERMINED ABOVE


    # distance must be accumulated !! (+directions +1.414]

    # = 3D array !!!!
    
    if upwards:
        start, stop, step = np.max(steps), 0, -1 
    else:
        start, stop, step  = 1, np.max(steps), 1
        

        

    for p in range( start, stop, step): 
    #perhaps less calculation ?? because onle masked are calculated ???
    # for NO STEP : no solution ???
    # degree is good start (= projecting to parent)
    # but the problem is in propagation mask ... which takes care of merged, distant nodes etc...

        msk_p = (steps == p)

        

        step_y =  y_parent [msk_p]   
        step_x =  x_parent [msk_p]
        
        #cannot work directly on slope matrix,
        #must take an average of branches before
        
        #ufunc.at will accumulate multiple indices
        # DOES NOT EXIST !!
        # np.mean.at(temp,   ( step_y, step_x),   slope[msk_p])
        
        if upwards:
            np.add.at(accum,( step_y, step_x), accum[msk_p])
        else:
            accum[msk_p] += accum [step_y, step_x]  

        
##        for q in range(9):  
##        #add directions as additional constraint
##            
##            msk_q = (directions ==q) * msk_p
##            
##            accum[y_parent[msk_q] , x_parent[msk_q]] += accum  [msk_q]
            
    return accum



def slope ( elevations, x_parent, y_parent):
    
    s = elevations[y_parent, x_parent] - elevations
     
    mask_diagonal = np.logical_and (
         x_parent == np.arange(elevations.shape[1]),
         y_parent == np.arange(elevations.shape[0])[:, None])
    
    s[mask_diagonal] /= 1.4142135623730951

    return s

    

def accum_avg (slope,  x_parent, y_parent, step, node_degree, mean_in_value=True):
    
    dgr = node_degree ; dgr[dgr == 0] = 1 # ZERO DIVISION problems ....
    temp = np.zeros(slope.shape)


    for p in range( np.max(step), 0, -1):  

    #perhaps less calculation ?? because onle masked are calculated ???
    # for NO STEP : no solution ???
    # degree is good start (= projecting to parent)
    # but the problem is in propagation mask ... which takes care of merged, distant nodes etc...

        msk_p= step == p
        
        step_y =  y_parent [msk_p]   
        step_x =  x_parent [msk_p]
        
        #cannot work directly on slope matrix,
        #must take an average of branches before
        
        #ufunc.at will accumulate multiple indices
        # DOES NOT EXIST !!
        # np.mean.at(temp,   ( step_y, step_x),   slope[msk_p])
        
        np.add.at(temp,   ( step_y, step_x),   slope[msk_p])
        
        temp[step_y, step_x] /= dgr[step_y, step_x]
        
        
    
        slope [step_y, step_x] += temp[step_y, step_x] 
       # slope[y_parent[msk_q] , x_parent[msk_q]] += \
           # slope  [msk_q] / dgr[y_parent[msk_q] , x_parent[msk_q]] 
        
    """
    TRACK ALL POSSIBLE CASES (= 8 directions)
        for q in range(9):  
            #FALI -1 = merged peaks !!!
            #add directions as additional constraint
            msk_q = (directions ==q)  * mask_p
            
         
        
            #inefficent (repetitive divisions)
            # else a temp matrix is needed to store values, divide with PARENT degree when out of loop, and then +=
            slope[y_parent[msk_q] , x_parent[msk_q]] += \
            slope  [msk_q] / dgr[y_parent[msk_q] , x_parent[msk_q]] 
         """   
       # slope[msk_p] /= dgr[msk_p] #divieds all (should only branches )!!
    return slope

"""
Propagate sinks : rest of raster = 0
to reverse  *= -1

TODO : accum shortest sink

TODO : ?? no need for masking : minimum at is fine (but a lot of data copying ???)

Used for branch classification:
should be made to accumulate ranks of sinks 
"""
def propagate_min (sink_values,  x_parent, y_parent, step):
    # dont need steps - simple propagation - see speed ??
    
    mx_out = np.copy(sink_values)

    #prepare for accumulation : delete/overwrite all values except sinks
    # cannot initialise to 0 - if negative values!
    mx_out[y_parent, x_parent]=np.ptp(mx_out) #ptp = range from min to max    
   
    for p in range( np.max(step), 0, -1): 

        msk_p= step == p
        
        step_y =  y_parent [msk_p]   
        step_x =  x_parent [msk_p]
     
           #  msk_p= (dem == 0)  #(step == p) * 
        np.minimum.at(mx_out, ( step_y, step_x), mx_out[msk_p])

##        for r in range(5): #until not full !!
##            
##            msk2 = dem[msk_q] < mx_out[msk_q]
##            
##            msk_q *= msk2
##            
##            mx_out[y_parent[msk_q] , x_parent[msk_q]] = dem  [msk_q] 
            
       # slope[msk_p] /= dgr[msk_p] #divieds all (should only branches )!!
    return mx_out


"""
Return sinks: as boolean ___ NO!
To return only borders : needs ids

"""
def sinks (parents_x, parents_y, ids_for_borders=None, branch_ids= False):
   
    s = np.ones(parents_x.shape).astype(bool)

    if isinstance(ids_for_borders, np.ndarray):

        ids = ids_for_borders
                   
        for v in views():
            a,b = v
            test = ids[a]==ids[b]
            #this is a hack: positives will always return 1!
            s[a]*=test; s[b]*=test
       
        #s = np.where(s==5, 0, 1)
        s[:]= ~s


        #parents are not sinks :) 
    else: s[parents_y, parents_x]=0     
        


    
    return s



"""
EXTREMELY SLOW!! ALI FUNKCIONIRA U REDU
only function is scipy = import moze biti spor - nije dobra praksa !!

TODO : samo sortiraj sinks (i procisti) i onda daj na akumulaciju min/max etc 

Nije dobro : eliminirati zatvorene sinks (koji ne diraju razlicit id)

RANK 1 = Surf. network; rank top (revrse) = ridge? (pod uvjetom da dira drugi ID)
"""

def ranks (ids,  values, mask = None):
    #is also done by double argsort (slower ??)
    #ranks = array.argsort().argsort()

    from scipy.stats import rankdata as rd

    r  = np.zeros (ids.shape)

    trees= np.unique(ids)
    
    for t in trees:
        
        if mask.any(): #cannot test mask as None !! (expensive ?)       
           #attention : mask is ~ because it is supplied as positive (more natural...?)
            m = np.logical_and(ids == t, ~ mask)
            
        else:   m = ids == t 
        
        r[m] = rd(values[m], method='dense')
    
    return r

"""
write ridgelines classified according to bottom pix.
"""
def write_shapefile(min_x, max_y, parents_x, parents_y, ids,  ranks):

    d = {}
    
    parents = np.hstack(parents_y, parents_x)
    childs = np.indices(parents_x) # two dimensional !!

    for j in range(parents.shape[0]):
        for i in range(parents.shape[1]):
            pass

			
def write_csv(output_file, directions_x, directions_y, data, gdal_geotransform): 
    
    pix = gdal_geotransform[1] 

    min_x = gdal_geotransform[0] 
    max_y = gdal_geotransform[3]
    
    #needs a vertical column 
    coord_y = max_y - ( np.arange( data.shape[0])[:, None] + directions_y) + pix/2
    coord_x = np.arange( data.shape[1]) + directions_x  + min_x + pix/2
    
    
    
    with open(output_file + ".csv", 'w', 3)  as csvfile:
        wr = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        wr.writerow([ "WKT","ID","Step"])
        for r in data_list:
    #GLOBAL!
    #adfGeoTransform[0] /* top left x */
    #adfGeoTransform[1] /* w-e pixel resolution */
    #adfGeoTransform[2] /* rotation, 0 if image is "north up" */
    #adfGeoTransform[3] /* top left y */
    #adfGeoTransform[4] /* rotation, 0 if image is "north up" */
    #adfGeoTransform[5] /* n-s pixel resolution */

    #QMessageBox.information(None, "podatak:", str(r))id1,id2,  visibile, pix_x, pix_y ,angle,angle_block,distance
            #OUTPUT LIST: id1,x1,y1,id2,x2,y2, visib, x, y, angle,angle_block,distance
            wr.writerow(["LINESTRING (" + str (r[0][0] * pix + gt[0] + half_pix) + " " + str(gt[3]- r[0][1]*pix -half_pix) +
                                ", " + str(r[1][0] * pix + gt[0] + half_pix) + " " + str(gt[3]- r[1][1] *pix -half_pix) +
                         ")", str(r[2]), r[3]])

#        #addition for writing WKT file
#                if r[6]: #if visible
#                    wkt_list.append(["LINESTRING (" + str (r[1]*pix + gt[0]) + " " + str(gt[3]- half_pix- r[2]*pix) +
#                                    ", " + str(r[4]*pix + gt[0] + half_pix) + " " + str(gt[3]- half_pix- r[5]*pix) + ")",
#                                    r[0], r[3]])
#        if wkt_list:
#            with open(output_file + "_wkt.csv", 'w', 3)  as csvfile:
#                wr = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
#                wr.writerow(["WKT", "ID1","ID2"])
#                for s in wkt_list: wr.writerow(s)
    #QMessageBox.information(None, "tocka ", str(wkt_list))




def main_NOT_USED(): 

    """
              ---------      MAIN      -----------
              ----- accumulate avg slope works
              the rest remains to be done ...
              
              prilagodba za brzi numpy : sva se stabla mogu razvuci u linije
              sinks | nodes | .......... | tops
              xx        xx          xx...       xy
              svaki clumn = step
    """       
           
           
    DEM= "U:/Users/zcuckovi/Desktop/temp/test_networks.tif"
    Output_raster= "U:/Users/zcuckovi/home/test"
    radius=3 #for merging peaks

        #TO TEST : perhaps not needed (np.any works fine !)
    iter=50 #guestimate, to avoid counting on each loop

    d= gdal.Open(DEM)
    r=d.ReadAsArray()

    ysize,  xsize = r.shape
        
    directions_x, directions_y = links(r)

    y_parent, x_parent  = np.indices(r.shape)  

    y_parent += directions_y;  x_parent += directions_x


    child_ids, steps = assign_ids(x_parent, y_parent, give_step = True )

    """
       #  ------- MERGING PEAKS  ---------------------
       # need IDs !
       # cannot be done without affecting the validity od sufrace network : must change DEM !!
    #old_peaks = np.vstack(np.where(directions == 4))

    new_peaks = merge (r, radius, directions_x, directions_y, child_ids)

        #register changes that break the rules ,,,,,
    mask = old_peaks - new_peaks
    mask = (mask[0] - mask[1] ) != 0
    directions[old_peaks[0], old_peaks[1]]  [mask] = -1 

    y_parent[old_peaks[0], old_peaks[1]] = new_peaks[ 0]
    x_parent[old_peaks[0], old_peaks[1]] = new_peaks[1]







            

    # -------------------- ACCUM SLOPE ------------------

    dgr = degrees(directions, x_parent, y_parent)

    #diagonal distances : just find all paired directions (begins with 0 so +2...)
    dist_mx = np.ones(r.shape)
    md = np.mod(directions + 2, 2)
    dist_mx[md== 0] = 1.414213562373095

    slope = (r[y_parent , x_parent] - r) / dist_mx
    slope [directions == 4 ] = 0
    # TODO ! SLOPE FOR MERGED (!?)

    accum = accum_slope (slope,  x_parent, y_parent, step, dgr, directions)

    # ------------------------------------------------------
    """

    slopes = r[y_parent, x_parent] - r 
    # adjust for diagonal pixels (both directions are 1 or -1)

    corners = abs(directions_y * directions_x)

    slopes [corners] /= 1.414213562373095

    dgr = degrees(x_parent, y_parent)

    out = accum_slope (slopes,  x_parent, y_parent, steps, dgr)

    out_x = out * directions_x; out_x [corners] *= 0.5
    out_y = out * directions_y;  out_y[corners] *= 0.5

    driver = gdal.GetDriverByName('GTiff')

    #for vector field calculator : define nodata !!
    o_x = Output_raster + "_x"; o_y=  Output_raster + "_y"
    c = driver.CreateCopy(o_x, d,0) #WHAT IS 0 ? : "strict or not" default =1
    c.GetRasterBand(1).WriteArray(out_x)

    c = driver.CreateCopy(o_y, d,0) #WHAT IS 0 ? : "strict or not" default =1
    c.GetRasterBand(1).WriteArray(out_y)

    c= None; d= None #to close properly, c is open for writing !
