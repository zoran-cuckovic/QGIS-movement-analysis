# Movement Analysis for QGIS

![image](https://github.com/user-attachments/assets/db2152a1-d708-4c1d-b8b2-fa6ccfdd8a63)


The Movement Analysis plugin features raster based algorithms such as accumulated cost surface, least cost path and accumulated paths. The calculations are based on Scikit Image library, which should be installed in QGIS Python. This library enables rapid calculations on large datasets. 

## Requirements
Featured algorithms run on Python Scikit-Image library, which is not included in regular QGIS installation. If missing, you should install the library with the following command 
``` pip --default-timeout=1000 install scikit-image```

In Windows, this is executed in OSGeo4W Shell (see my tutorial : https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/). In Linux/Mac this should be done in the centralised package management unit.

## Instalation
Movement Analysis is avaialble as a regular QGIS plugin (go to Plugins >> lnstall). Note that you need to *enable experimental plugins* under plugin manager settings. 

Manual installation : download the code (green button) and go to Plugins >> Manage >> Install from ZIP.
![image](https://github.com/zoran-cuckovic/QGIS-movement-analysis/assets/6622934/fc6e2ede-cf8e-4077-af68-b5f18f7fe263)

# Manual
## Least cost path
*Friction surface*: a raster where each pixel represents difficulty of movement (energy expenditure, time, etc.).

*Departure points / destinations points*: two sets of points which will be connected by least cost paths. Same dataset can be used for both parameters, if needed. 

*Maximum distance*: points beyond this limit will not be connected. 

*Output*: a vector file (lines) of least cost paths. 

## Least cost surface 
*Friction surface*: a raster where each pixel represents difficulty of movement (energy expenditure, time, etc.).

*Destination points*: a set of points for which the accumulated cost surfaces (ACS) will be calculated. 

*Maximum distance*: areas beyond this limit will not be analysed. 

*Inner buffer*: exclusion zone around each destination point which will be ingored. 

*Analysis type*: 
* *Accumulated cost surface*: cost of reaching the nearest destination point (increases as we move away from the destination). 
* *Accumulated paths*: movement corridors from all neighbouring locations (i.e. pixels), towards the nearest destination point. The obtained values mark the frequency of passages. 

*Cumulation mode*:
* *Exclusive*: accumulated surfaces or paths will only connect to the most accessible point. 
* *Addition*: in cases of overlaps, given the distance parameters, the obtained values for individual destinations will sum up. 
* *Min/Max*: same as above, but only the minimum or maximum value will be retained
* *Average*: same as above, except that the average value will be calculated instead. 

*Output*: Accumulated cost surfaces / accumulated paths which connect to chosen locations. 
If exclusive mode is chosen a supplementary traceback model will be produced, which registers moves from each pixel towards the most accessible destination. 

### Helpers – SciKit installation module
* A convenience function to install SciKit in QGIS Python. Important: a restart of QGIS is necessary after the installation. 
