"""
..module:: RasterDiff
    :platform: Windows
    ::creation: 04-Feb-2016
    :purpose:  Create raster differences where raster names match across 2 workspaces
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""

import os
import arcpy
from argparse import ArgumentParser

def getOptions(model_choices):
    """Return command line arguments and options.

    -h              --help          Show help message and exit
 [Positional arguments:]
    bgdb                    Rasters to be subtracted from found in B-geoDatabase

 [Arguments required with the following Options:]

    -fgeo FGDB              Rasters names from F-geoDatabase found in B-geoDatabase will be subtracted (B-F)
    -one  rasterName        
    -ogeo GEODB             Saves rasters in GeoDatabase
        
  [for instance:]
  
   C:\python27\arcGIS10.2\python T:\RasterDifference.py T:\WCFM\WCFMbase.gdb -fgeo T:\WCFM\WCFMfb.gdb -ogeo=T:\WCFM\WCFMdiffs.gdb
   or
   C:\python27\arcGIS10.2\python T:\RasterDifference.py T:\WCFM\WCFMbase.gdb  -one T:\WCFM\WCFMbase.gdb\HEAD_00012_1 -ogeo t:\WCFM\WCFMdiffsV1.gdb    
   or
   C:\python27\arcGIS10.2\python T:\RasterDifference.py T:\WCFM\WCFMbase.gdb  -one T:\WCFM\WCFMbase.gdb\clpHEAD_00012_1 -ogeo t:\WCFM\WCFMclpDiffsV2.gdb    
   
"""
    parser = ArgumentParser(prog='RasterDifference')
    parser.add_argument("bgdb",
                        help="Rasters to be subtracted from found in B-geoDatabase")
    parser.add_argument("-fgeo",dest="fgdb",
                        help="Rasters from F-geoDatabase will be subtracted from rasters in B-geoDatabase")
    parser.add_argument("-one",dest="oneras",
                        help="Single Raster is subtracted from by each raster in the B-geoDatabase (One Raster - B Rasters)")
    parser.add_argument("-ogeo",dest="ogdb",default='Default.gdb',
                        help="Rasters will be saved in O-geoDatabase.  Default value is: Default.gdb")

    args = parser.parse_args()
    print args
 
    return args

def setModelOrigins():
    
   # Provide Default Sparial Reference to assure output is properly projected
    global SR
    SR = arcpy.SpatialReference(2881)
    
   # Model origins are not currently needed but are useful for reference
    modelOrigins = dict(C4CDC=arcpy.Point(763329.000,437766.000),
                        ECFM=arcpy.Point(565465.000,-44448.000),
                        ECFT=arcpy.Point(330706.031,1146903.250),
                        LECSR=arcpy.Point(680961.000,318790.000),
                        NPALM=arcpy.Point(680961.000,318790.000),                        
                        LKBGWM=arcpy.Point(444435.531,903882.063),
                        LWCFAS=arcpy.Point(438900.000,-80164.000),
                        LWCSAS=arcpy.Point(292353.000,456228.000),
                        WCFM=arcpy.Point(20665.000,-44448.000)
                        )
    return

def get_SpatialA():
    arcpy.CheckInExtension("Spatial")   
    # Check out the ArcGIS Spatial Analyst extension license
    availability = arcpy.CheckExtension("Spatial")
    if availability == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        arcpy.AddError("%s extension is not available (%s)"%("Spatial Analyst Extension",availability))
        arcpy.AddError("Please ask someone who has it checked out but not using to turn off the extension")
        exit()
    return(availability)
 
def define_workspace(geodb,usetype):
    
    # Set base paths for Modflow namefile and ESRI workspace.
    out_folder_path = "H:\\Documents\\ArcGIS"

    if geodb == "Default.gdb":
        out_name = "Default.gdb"
        print "Default geodatabase path defined as: " + out_folder_path
    elif geodb <> None:
        (temp_path, gdbfile) = os.path.split(geodb)
        out_folder_path = temp_path
        out_name = geodb        
    else:
        print "Unspecified working path.  Assigning: " + path
        out_folder_path =  path
        (out_folder_path, gdbfile) = os.path.split(out_folder_path)
        out_name = gdbfile

    workspace = os.path.join(out_folder_path, gdbfile)
    print "Workspace: "+ workspace + " exists: ", arcpy.Exists(workspace)
    
    if not arcpy.Exists(workspace):
        print "Workspace does not exist..."
        if usetype == 'input':
            print "Input workspace required.  Please provide valid input workspace"
            exit()
        else:
            (temp_path, gdbfile) = os.path.split(workspace)
            if temp_path == "":
                temp_path = out_folder_path
            print "Creating: " + temp_path    +     gdbfile
            arcpy.CreateFileGDB_management(temp_path, gdbfile)
            arcpy.env.workspace = os.path.join(temp_path, gdbfile)
    else:
        arcpy.env.workspace = workspace
        
    print usetype + " processes are using: " + workspace
    arcpy.env.overwriteOutput = True 
    return arcpy.env.workspace

def myListDatasets(workspace):
    # Creates arry list of Rasters from workspace
    arcpy.env.workspace = workspace
    datasetList = arcpy.ListDatasets("*", "Raster")
    arraylist = []
    
    for dataset in datasetList:
        #print "Dataset:" + dataset
        ##get path
        desc = arcpy.Describe(dataset)
        ## append to list
        #print "Dataset Path: " + dataset
        arraylist.append(desc.catalogPath)
    return arraylist  

model_choices = setModelOrigins()
options = getOptions(model_choices)

if options.bgdb == None or (options.fgdb == None and options.oneras == None):
    """
    Provide warning that required arguments must be supplied
    """
    print "Unable to process Raster data without bgdb and (fgdb workspace or single raster) details."
    exit()
    
if options.ogdb:
    oWorkspace = define_workspace(options.ogdb,'output')
if options.bgdb:
    bWorkspace = define_workspace(options.bgdb,'input')
if options.fgdb:
    fWorkspace = define_workspace(options.fgdb,'input')

get_SpatialA()

arraylistB = myListDatasets(bWorkspace)

# List  datasets and print Features for fgdb
if options.fgdb:
    arcpy.env.workspace = fWorkspace
    fRasList = arcpy.ListRasters()
    for fRas in fRasList:
        for bRas in arraylistB:
            (temp_path, ras) = os.path.split(bRas)
            if fRas == ras:
                rasType, stressPeriod, layer = ras.split("_",2)
                rasType, stressPeriod, layer
                outputName = "D_"+ ras
            
                ras1 = arcpy.Raster(bRas)
                ras2 = arcpy.Raster(ras)
                oras = ras1 - ras2
                
                results = oWorkspace + "\\" + outputName
                if arcpy.TestSchemaLock(results):
                    print ras1 , ' minus ' , ras2 , ' equals ' , outputName
                    oras.save(results)
                else:
                	print "Output SKIPPED [Schema lock present]. Can't save ", results
                	print "trying anyhow"
                	print ras1 , ' minus ' , ras2 , ' equals ' , outputName
                	oras.save(results)
 

        #    else:
        #        print "Raster Names Do Not Match[",fRas," <> ",ras,"]"
                
if options.oneras:
    (temp_path, initRaster) = os.path.split(options.oneras)
    initRasType, initSP, initLay = initRaster.split("_",2)
    for bRas in arraylistB:
        (temp_path, ras) = os.path.split(bRas)
        rasType, stressPeriod, layer = ras.split("_",2)
        if initRasType == rasType:
            if initLay == layer:
                outputName = rasType + "_diff_" + stressPeriod + "_" + layer
                ras2 = arcpy.Raster(bRas)
                ras1 = arcpy.Raster(options.oneras)
                oras = ras2 - ras1
                results = oWorkspace + "\\" + outputName
                if arcpy.TestSchemaLock(results) :
                    print ras2 , ' minus ' , ras1 , ' equals ' , outputName
                    oras.save(results)
                elif not arcpy.Exists(results):
                	print ras2 , ' minus ' , ras1 , ' equals ' , outputName
                	oras.save(results)
                else:
                	print "Output SKIPPED [Schema lock present]. Can't save ", results
            else:
                print "Layers Do Not Match [",initLay,"<>",layer,"]"
        else:
            print "Raster Types Do Not Match[",initRasType,"<>",rasType,"]"
print "End of Execution"