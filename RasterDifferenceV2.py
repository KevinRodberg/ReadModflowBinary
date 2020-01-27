"""
..module:: RasterDiffV2
    :platform: Windows
    ::creation: 04-Feb-2016
    ::revision: 08-Jan-2020
    :purpose:  Create raster differences where raster names match across 2 workspaces
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""
import numpy as np
import os
import re
import glob
import MFgis.MFgis as MFgis

try:
    from osgeo import gdal
except ImportError:
    print('GDAL not installed')    
    
from argparse import ArgumentParser

def getOptions():
    """Return command line arguments and options.
    -h              --help          Show help message and exit
 [Arguments required with the following Options:]
    -noArcGIS                          Process binary files without using ArcGIS
    -bgdb   BGDB                       Rasters to be subtracted from found in B-workspace or folder    
    -fgeo   FGDB                       Rasters names from F-workspace found in B-workspace will be subtracted (B-F)
    -one    rasterName                 Single raster to subtract from rasters in bgdb [BGDB]
    -rasras (FirstRaster SecondRaster) SecondRaster is subtracted from FirstRaster
    -ogeo   GEODB                      Saves rasters in O-workspace 
        
  [for instance:]
   net use t: \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python
   
   Subrtract all rasters in WCFMbase.gdb that have the same names as rasters in WCFMfb.gdb
   ---------------------------------------------------------------------------------------
   C:\python27\arcGIS10.2\python T:\ReadModflowBinary\RasterDifference.py 
                                               -bgeo T:\WCFM\WCFMbase.gdb -fgeo L:\WCFM\WCFMfb.gdb 
                                               -ogeo=L:\WCFM\WCFMdiffs.gdb
                                               
   Subrtract all rasters in Heads2040 that have the same names as rasters in Heads2014
   ---------------------------------------------------------------------------------------   
   C:\ProgramData\Anaconda3\pythonw.exe T:\ReadModflowBinary\RasterDifferenceV2.py -noArcGIS
                                               -bgeo H:\\Documents\\ArcGIS\\Rasters\\Heads2040  
                                               -fgeo H:\\Documents\\ArcGIS\\Rasters\\Heads2014  
                                               -ogeo  H:\\Documents\\ArcGIS\\Rasters\\HeadsDiff
                                               
   Subrtract one raster: HEAD_00012_1 from each raster in WCFMbase.gdb
   ---------------------------------------------------------------------------------------
   C:\python27\arcGIS10.2\python T:\ReadModflowBinary\RasterDifference.py -bgeo L:\WCFM\WCFMbase.gdb 
                                                -one L:\WCFM\WCFMbase.gdb\HEAD_00012_1 
                                                -ogeo L:\WCFM\WCFMdiffsV1.gdb    

   Subrtract raster named: HEAD_00012_1 from raster named CONC_08766_1
       workspace identified in -bgeo is required for app consistency by not used for input data 
           although it should be consistent with other workspace types (folder w/folder or .gdb w/.gdb)
   ---------------------------------------------------------------------------------------     
   C:\python27\arcGIS10.2\python T:\ReadModflowBinary\RasterDifference.py 
                                                 -bgeo L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb 
                                                 -rasras L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb\CONC_08766_1 
                                                         L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb\CONC_00365_1 
                                                 -ogeo L:\MB\GIS\Spatial\TDS\gdb\KARtdsDiffs.gdb
   """

    parser = ArgumentParser(prog='RasterDifference')
    parser.add_argument("-noArcGIS",action="store_true",
                        help="Process binary files without using ArcGIS")
    parser.add_argument("-bgeo",dest="bgdb",
                        help="Rasters to be subtracted from found in B-gdb")
    parser.add_argument("-fgeo",dest="fgdb",
                        help="Subtract rasters from F-gdb matching raster names in B-gdb")    
    parser.add_argument("-one",dest="oneras",
                        help="Subtract a raster from each raster in B-gdb")
    parser.add_argument("-rasras",nargs=2,dest="rasras",
                        help="Subtract 2 rasters: FirstRaster-SecondRaster")
    parser.add_argument("-ogeo",dest="ogdb",default='Default.gdb',
                        help="Rasters will be saved in O-gdb.")
    args = parser.parse_args()
    return args

def myListDatasets(workspace):
    # Creates arry list of Rasters from workspace
    if not options.noArcGIS:
        arcpy.env.workspace = workspace
        datasetList = arcpy.ListDatasets("*", "Raster")
        arraylist = []
        for dataset in datasetList:
            ##get path
            desc = arcpy.Describe(dataset)
            ## append to list
            arraylist.append(desc.catalogPath)
    else:
        os.chdir(workspace)
        arraylist = glob.glob("*.tif")
    return arraylist  

options = getOptions()
if not options.noArcGIS:
    try:
        import arcpy
        MFgis.get_SpatialA()
    except ImportError:
        print ('ESRI ArcGIS arcpy library is not availble')
        options.noArcGIS = True
optArgs = options
print("options.bgdb:",options.bgdb)
if options.bgdb == None or (options.rasras == None
                            and options.fgdb == None
                            and options.oneras == None):
#--------------------------------------------------------------------------                       
#   Provide warning that required arguments must be supplied
#--------------------------------------------------------------------------                       
    print ("""
    ----------------------------------------------  
    Unable to process Raster data without bgdb and 
    (fgdb workspace or single raster) details.
    ----------------------------------------------  """)
    exit()

#--------------------------------------------------------------------------                       
# Reset previously user assigned noArc to True if not able to import arcpy  
# mostlikely because it is not being ran from Citrix)       
#--------------------------------------------------------------------------
if not options.noArcGIS:
    try:
#--------------------------------------------------------------------------                       
#   Define workspace areas, depending upon availability of arcpy functions
#--------------------------------------------------------------------------                       
        if options.ogdb:
            oWorkspace = MFgis.setWorkspc(options.ogdb)
        if options.bgdb:
            bWorkspace = MFgis.setWorkspc(options.bgdb)
        if options.fgdb:
            fWorkspace = MFgis.setWorkspc(options.fgdb)
    except ImportError:
        print ('ESRI ArcGIS arcpy library is not availble')
        options.noArcGIS = True
else:
    if options.bgdb:
        bWorkspace = options.bgdb
        print("Base rasters will be selected from here:\n\t",bWorkspace)        
    if options.fgdb:
        fWorkspace = options.fgdb  
        print("future rasters will be selected from here:\n\t",fWorkspace)        
    if options.ogdb:
        oWorkspace = options.ogdb
        print("output rasters will be created here:\n\t",oWorkspace, "\nIf filenames include:" )
arraylistB = myListDatasets(bWorkspace)
driver = gdal.GetDriverByName( 'GTiff' )
DataType = gdal.GDT_Float32

def rasProps(ds):
    ds= gdal.Open(fRas)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    [cols, rows] = arr.shape
    SR=ds.GetProjection()
    geoTrans=ds.GetGeoTransform()
    return(SR,geoTrans,cols,rows)
    
# List  datasets and print Features for fgdb
if options.fgdb:
    if not options.noArcGIS:
        arcpy.env.workspace = fWorkspace
        fRasList = arcpy.ListRasters()
    else:
        os.chdir(fWorkspace)
        os.path.split(fWorkspace)
        fRasList = glob.glob("*.tif")
    print(fRasList)
    for fRas in fRasList:
        if options.noArcGIS: (SR,geoTrans,cols,rows) = rasProps(fRas)
        for bRas in arraylistB:
            (temp_path, ras) = os.path.split(bRas)
            if fRas == ras:
                rasType, stressPeriod, layer = ras.split("_",2)
                rasType, stressPeriod, layer
                outputName = "D_"+ ras
                results = os.path.join(oWorkspace,outputName)
              #  print ("{} minus {} equals {}".format(bRas,ras,outputName))
                if not options.noArcGIS:
                    ras1 = arcpy.Raster(bRas)
                    ras2 = arcpy.Raster(ras)
                    oras = ras1 - ras2                                    
                    oras.save(results)
                else:
                    ras1 = MFgis.rasFile2array(bRas)
                    ras2 = MFgis.rasFile2array(ras)
                    oras = ras1 - ras2                    
                    outdata = driver.Create(results, rows, cols, 1, DataType)
                    outdata.SetGeoTransform(geoTrans) 
                    outdata.SetProjection(SR) 
                    outdata.GetRasterBand(1).WriteArray( oras )
                    outdata.FlushCache()
if options.oneras:
    (temp_path, initRaster) = os.path.split(options.oneras)
    initRasType, initSP, initLay = initRaster.split("_",2)
    print (arraylistB)
    if options.noArcGIS: (SR,geoTrans,cols,rows) = rasProps(options.oneras)
    for bRas in arraylistB:
        (temp_path, ras) = os.path.split(bRas)
        rasType, stressPeriod, layer = ras.split("_",2)
        if initRasType == rasType:
            if initLay == layer:
                outputName = rasType + "_diff_" + stressPeriod + "_" + layer
                results = os.path.join(oWorkspace,outputName)
               # print ("{} minus {} equals {}".format(bRas,options.oneras,outputName))
                if not options.noArcGIS:
                    ras2 = arcpy.Raster(bRas)
                    ras1 = arcpy.Raster(options.oneras)
                    oras = ras2 - ras1
                    if arcpy.TestSchemaLock(results) or not arcpy.Exists(results):
                        oras.save(results)
                    else:
                    	print ("Output SKIPPED [Schema lock present]. Can't save {}".format(results))
                else:
                    ras1 = MFgis.rasFile2array(bRas)
                    ras2 = MFgis.rasFile2array(options.oneras)
                    oras = ras1 - ras2                    
                    outdata = driver.Create(results, rows, cols, 1, DataType)
                    outdata.SetGeoTransform(geoTrans) 
                    outdata.SetProjection(SR) 
                    outdata.GetRasterBand(1).WriteArray( oras )
                    outdata.FlushCache()
            else:
                print ("Layers Do Not Match [{} != {}]".format(initLay,layer))
        else:
            print ("Raster Types Do Not Match[{} != {}]".format(initRasType,rasType))
if options.rasras:        
    if options.noArcGIS: (SR,geoTrans,cols,rows) = rasProps(options.rasras[0])
    print (options.rasras[0],options.rasras[1])
    (temp_path,Ras1) = os.path.split(options.rasras[0])
    (temp_path,Ras2) = os.path.split(options.rasras[1])
    rasType1, stressPeriod1, layer1 = Ras1.split("_",2)
    rasType2, stressPeriod2, layer2 = Ras2.split("_",2)
    if rasType1 == rasType2 and layer1 == layer2:
        outputName = rasType1 +'_'+layer1 + '_'+stressPeriod1 + "_"+stressPeriod2
        print (outputName)
    else:
        print('rasters are mismatched')
    results = os.path.join(oWorkspace,outputName)
  #  print ("{} minus {} equals {}".format(options.rasras[0],options.rasras[1],outputName))
    if not options.noArcGIS:    
        ras1 = arcpy.Raster(options.rasras[0])
        ras2 = arcpy.Raster(options.rasras[1])
        oras = ras1 - ras2
        oras.save(results)
    else:
        ras1 = MFgis.rasFile2array(options.rasras[0])
        ras2 = MFgis.rasFile2array(options.rasras[1])
        oras = ras1 - ras2                    
        outdata = driver.Create(results, rows, cols, 1, DataType)
        outdata.SetGeoTransform(geoTrans) 
        outdata.SetProjection(SR) 
        outdata.GetRasterBand(1).WriteArray( oras )
        outdata.FlushCache()
print ("End of Execution")