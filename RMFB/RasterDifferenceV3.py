"""
..module:: RasterDifferenceV3
    :platform: Windows
    ::creation: 04-Feb-2016
    ::revision: 12-Jan-2020
    :purpose:  Create raster differences where raster names match across 2 workspaces
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""
import numpy as np
import os
import re
import glob
import RMFB.MFgis.MFgis as MFgis
import RMFB.MFgui.MFgui as MFgui
import RMFB.MFargDefaults.setDefaultArgs as defs
import sys
from datetime import datetime

try:
    from osgeo import gdal
except ImportError:
    print('GDAL not installed')


#    -h              --help          Show help message and exit
#[Arguments required with the following Options:]
#    -noArcGIS                          Process binary files without using ArcGIS
#    -bgdb   BGDB                       Rasters to be subtracted from found in B-workspace or folder
#    -fgeo   FGDB                       Rasters names from F-workspace found in B-workspace will be subtracted (B-F)
#    -one    rasterName                 Single raster to subtract from rasters in bgdb [BGDB]
#    -rasras (FirstRaster SecondRaster) SecondRaster is subtracted from FirstRaster
#    -ogeo   OGDB                       Saves rasters in O-workspace
#    -ratio  ratio                      calculate difference and Percent Change
#  [for instance:]
#   net use t: \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python
#
#   Subrtract all rasters in WCFMbase.gdb that have the same names as rasters in WCFMfb.gdb
#   ---------------------------------------------------------------------------------------
#   C:\python27\arcGIS10.2\python T:\RasDif.py
#                                               -bgeo T:\WCFM\WCFMbase.gdb -fgeo L:\WCFM\WCFMfb.gdb
#                                               -ogeo=L:\WCFM\WCFMdiffs.gdb
#
#   Subrtract all rasters in Heads2040 that have the same names as rasters in Heads2014
#   ---------------------------------------------------------------------------------------
#   C:\ProgramData\Anaconda3\pythonw.exe T:\RasDif.py -noArcGIS
#                                               -bgeo H:\\Documents\\ArcGIS\\Rasters\\Heads2040
#                                               -fgeo H:\\Documents\\ArcGIS\\Rasters\\Heads2014
#                                               -ogeo  H:\\Documents\\ArcGIS\\Rasters\\HeadsDiff
#
#   Subrtract one raster: HEAD_00012_1 from each raster in WCFMbase.gdb
#   ---------------------------------------------------------------------------------------
#   C:\python27\arcGIS10.2\python T:\RasDif.py -bgeo L:\WCFM\WCFMbase.gdb
#                                                -one L:\WCFM\WCFMbase.gdb\HEAD_00012_1
#                                                -ogeo L:\WCFM\WCFMdiffsV1.gdb
#
#   Subrtract raster named: HEAD_00012_1 from raster named CONC_08766_1
#       workspace identified in -bgeo is required for app consistency by not used for input data
#           although it should be consistent with other workspace types (folder w/folder or .gdb w/.gdb)
#   ---------------------------------------------------------------------------------------
#   C:\python27\arcGIS10.2\python T:\RasDif.py
#                                                 -bgeo L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb
#                                                 -rasras L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb\CONC_08766_1
#                                                         L:\MB\GIS\Spatial\TDS\gdb\KARecfmtds2016b.gdb\CONC_00365_1
#                                                 -ogeo L:\MB\GIS\Spatial\TDS\gdb\KARtdsDiffs.gdb
#   """

# KAR slight modification to sort list of files
    # previous unsorted list made reviewng progress 
    # awkward as the files were processed in an unusual sequence.
def myListDatasets(workspace):
    # Creates arry list of Rasters from workspace
    if not optArgs['noArc']:
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
        arraylist = sorted(glob.glob("*.tif"))
    return arraylist

def rasProps(fRas):
    ds= gdal.Open(fRas)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    [cols, rows] = arr.shape
    SR=ds.GetProjection()
    geoTrans=ds.GetGeoTransform()
    return(SR,geoTrans,cols,rows)

def main():
#--------------------------------------------------------------------
#  cmdLine variable is used to determine gui options
#--------------------------------------------------------------------
    cmdLine = checkExec_env()
    if cmdLine: print('Running in Command line')
    else: print('Running in Python IDLE')

    global running
    global optArgs
    global runSpyderString
    global runString
    
    running = True  # Global flag for Terminate Button

    runString = sys.executable.replace('pythonw.exe','python.exe') + " " + \
            r'\\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python' + \
                r'\RasDif.py'
    runSpyderString = "runfile(r'\\\\ad.sfwmd.gov\\dfsroot\\data\\wsd\\SUP\\devel" + \
                "\\source\\Python\\RD3.py',  " + \
                "wdir=r'\\\\ad.sfwmd.gov\\dfsroot\\data\\wsd\\SUP\\devel\\source\\Python '," +\
                "args='"
                
#--------------------------------------------------------------------
#   parserArgs is a Namespace and
#   optArgs is a dictionary assigned to parserArgs
#       which can be accessed via the guiArgs function in MFgui module
#           and throughout the program
#--------------------------------------------------------------------
    argHelp ={}
    try:
        parserArgs,argHelp = defs.getArgsFromParser(prog='RD3.py')

        optArgs = vars(parserArgs)
        if not optArgs['quiet']:
            for k in optArgs.items():
                label, value = k
                print ("{!s:<15} {!s:>6}".format(label, value))
    except:
        sys.exit(0)
    if(optArgs['gui'] != True) :
        optArgs['gui']= False
    if (
      #  (optArgs['ListOf2'] == None ) or
         (optArgs['BGDB']== None or optArgs['FGDB']==None)
      #  or (optArgs['BGDB'] == None or optArgs['rasterName']==None)
        ):
         optArgs['gui'] = True
    if (optArgs['ListOf2'] is not None):
        if len(optArgs['ListOf2']) < 2:
            print(optArgs['ListOf2'],len(optArgs['ListOf2']))
#--------------------------------------------------------------------------
#  GUI interface option selection
#--------------------------------------------------------------------------
    if not optArgs['noArc']:
        try:
            import arcpy
            MFgis.get_SpatialA()
        except ImportError:
            print ('ESRI ArcGIS arcpy library is not availble')
            optArgs['noArc'] = True
    if optArgs['gui']:   MFgui.guiArgs(optArgs,argHelp,prog='RasterDifference')
    print(optArgs)
    print("optArgs['BGDB']:",optArgs['BGDB'])
    if optArgs['BGDB']== None or (optArgs['ListOf2'] == None
                                and optArgs['FGDB'] == None
                                and optArgs['rasterName']==None):
    #--------------------------------------------------------------------------
    #   Provide warning that required arguments must be supplied
    #--------------------------------------------------------------------------
        print ("""
        ----------------------------------------------
        Unable to process Raster data without bgdb and
        (fgdb workspace or single raster) details.
        ----------------------------------------------  """)
        sys.exit(1)

    #--------------------------------------------------------------------------
    # Reset previously user assigned noArc to True if not able to import arcpy
    # mostlikely because it is not being ran from Citrix)
    #--------------------------------------------------------------------------
    if not optArgs['noArc']:
        try:
    #--------------------------------------------------------------------------
    #   Define workspace areas, depending upon availability of arcpy functions
    #--------------------------------------------------------------------------
            if optArgs['OGDB']:
                oWorkspace = MFgis.setWorkspc(optArgs['OGDB'])
            if optArgs['BGDB']:
                bWorkspace = MFgis.setWorkspc(optArgs['BGDB'])
            if optArgs['FGDB']:
                fWorkspace = MFgis.setWorkspc(optArgs['FGDB'])
        except ImportError:
            print ('ESRI ArcGIS arcpy library is not availble')
            optArgs['noArc'] = True
    else:
        print ('processing without ArcGIS')
        if optArgs['BGDB']:
            bWorkspace = optArgs['BGDB']
            print("Base rasters will be selected from here:\n\t",bWorkspace)
        if optArgs['FGDB']:
            fWorkspace = optArgs['FGDB']
            print("future rasters will be selected from here:\n\t",fWorkspace)
        if optArgs['OGDB']:
            oWorkspace = optArgs['OGDB']
            print("output rasters will be created here:\n\t",oWorkspace,
                  "\nIf filenames include:" )

#--------------------------------------------------------------------------
# Compile arguments into a single runstring useful for batch file execution:
#--------------------------------------------------------------------------
# check each optArg item to see if it has been assigned
#   Each assigned option [key] are paired with str[val]
#       or string converted from a tuple or list and delimited by '|'
#--------------------------------------------------------------------------
    for arg,val in optArgs.items():
      if val:
     #   print(arg)
        for key, value in argHelp.items():
     #     print(key,value)
          if value[2] == arg:
            if value[2] == 'gui':
                runSpyderString += ' -'+value[2]
            elif len(value) < 4 :
                runString += ' -'+key
                runSpyderString += ' -'+key
    #         elif value[2] == 'terms':
    #           runString += ' -terms '
    #           runSpyderString += ' -terms '
    #           if type(val) is list or type(val) is tuple:
    #               # Add | to separate each terms
    #               for trm in val: Sval = '|'.join(map(str,val))
    #               runString += '"'+Sval+'"'
    #               runSpyderString += '"'+Sval+'"'
    #           else:
    #               # remove single quotes from terms
    #               runString += '"'+val.strip('\'')+'"'
    #               runSpyderString += '"'+val.strip('\'')+'"'
            elif (value[3] != val and key !='rasras'):
                 # DOS likes backslashes
                 print(key,val)
                 runString += ' -'+key + ' ' + str(val.replace('/','\\'))
                 # Spyder likes forwardslashes
                 runSpyderString += ' -'+key + ' ' + str(val.replace('\\','/'))
            elif (key == 'rasras'):
                if (isinstance(val,list)):
                    valstr = ' '.join(val)
                    print(valstr)
                    val= valstr
                runString += ' -'+key + ' ' + str(val.replace('/','\\'))
                runSpyderString += ' -'+key + ' ' + str(val.replace('\\','/'))
    runSpyderString += "')"

    print("runString:\n",runString)
    print("runSpyderString:\n",runSpyderString)

            
    arraylistB = myListDatasets(bWorkspace)
    driver = gdal.GetDriverByName( 'GTiff' )
    DataType = gdal.GDT_Float32
    if '/' in bWorkspace:
        Bpth1=bWorkspace.split('/')[-2]
        Fpth2=fWorkspace.split('/')[-2]
    elif '\\' in bWorkspace:
        Bpth1=bWorkspace.split('\\')[-2]
        Fpth2=fWorkspace.split('\\')[-2]
    else:
        print("separator not found in path")
        exit

    # List  datasets and print Features for fgdb
    if optArgs['FGDB']:
        fRasList = myListDatasets(fWorkspace)
        if not optArgs['quiet']:print(arraylistB)

        for fRas in fRasList:
            if not fRas.startswith("D_"):
                if optArgs['noArc']: (SR,geoTrans,cols,rows) = rasProps(fRas)
                for bRas in arraylistB:
                    if not bRas.startswith("D_"):                
                        (temp_path, ras) = os.path.split(bRas)
                        if fRas == ras:
                            outputName = "D_"+ ras
                            results = os.path.join(oWorkspace,outputName)
                            print(results)
                            print ("{}/{} minus {}/{} equals {}".format(Bpth1,bRas,Fpth2,ras,outputName))
                            if not optArgs['noArc']:
                                ras1 = arcpy.Raster(bRas)
                                ras2 = arcpy.Raster(fRas)
                                if not optArgs['ratio']:oras = ras1 - ras2
                                if optArgs['ratio']:oras = (ras1 - ras2) / ras2
                                oras.save(results)
                            else:
                                os.chdir(bWorkspace)
                                ras1 = MFgis.rasFile2array(bRas)
                                os.chdir(fWorkspace)
                                ras2 = MFgis.rasFile2array(fRas)
                                if not optArgs['ratio']:oras = ras1 - ras2
                                if optArgs['ratio']:oras = (ras1 - ras2) / ras2
                                try:
                                    outdata = driver.Create(results, rows, cols, 1, DataType)
                                    outdata.SetGeoTransform(geoTrans)
                                    outdata.SetProjection(SR)
                                    outdata.GetRasterBand(1).WriteArray( oras )
                                    outdata.FlushCache()
                                    print('Saving:', results)
                                except:
                                    outdata.FlushCache()
                                    RED     = "\033[1;31m"  
                                    RESET   = "\033[0;0m"
                                    print(RED,'Raster file: {} could be locked'.format(outputName),RESET)

    if optArgs['rasterName']:
        (temp_path, initRaster) = os.path.split(optArgs['rasterName'])
        initRasType, initSP, initLay = initRaster.split("_",2)
        initAggType =""
        if initRasType in ['MIN','MAX','MEAN']:
            initAggType, initRasType, initSP, initLay = initRaster.split("_",3)
        elif initRasType not in ['HEAD','CONC']:
                initRasType, initLay, initSP = initRaster.split("_",2)
        if not optArgs['quiet']:print (arraylistB)
        if optArgs['noArc']: (SR,geoTrans,cols,rows) = rasProps(optArgs['rasterName'])
        for bRas in arraylistB:
            if not optArgs['quiet']:print('Layers ', bRas)
            (temp_path, ras) = os.path.split(bRas)
            print(temp_path, ras)
            rasType, stressPeriod, layer = ras.split("_",2)
            aggType =""
            if rasType in ['MIN','MAX','MEAN']:
                aggType, rasType, layer = ras.split("_",3)
            elif rasType not in ['HEAD','CONC','clpHEAD','clpCONC']:
                rasType, layer, stressPeriod, TS = ras.split("_",3)
            if initRasType == rasType:
                print('Types match',initRasType, rasType,bRas)
                print(initLay.upper(),layer.upper())
                if initLay.upper().replace('.tif','') == layer.upper().replace('.tif',''):
                    print('Layers match',initLay, layer, bRas)
                    if aggType =="":
                        outputName = "D1_"+ aggType + "_" + rasType + "_" + stressPeriod + "_" + layer
                    else:
                        outputName = "D1_"+ aggType + "_" + rasType + "_"  + layer
                    results = os.path.join(oWorkspace,outputName)
                    # print ("{} minus {} equals {}".format(bRas,optArgs['rasterName'],outputName))
                    if not optArgs['noArc']:
                        ras2 = arcpy.Raster(bRas)
                        ras1 = arcpy.Raster(optArgs['rasterName'])
                        if not optArgs['ratio']:oras = ras1 - ras2
                        if optArgs['ratio']:oras = (ras1 - ras2) / ras2
                        if arcpy.TestSchemaLock(results) or not arcpy.Exists(results):
                            oras.save(results)
                        else:
                            print ("Output SKIPPED [Schema lock present]. Can't save {}".format(results))
                    else:
                        print(bRas,bWorkspace,fWorkspace)
                        inRas = os.path.join(bWorkspace,bRas)
                        print(inRas)
                        ras1 = MFgis.rasFile2array(inRas)
                        #ras1 = MFgis.rasFile2array(bRas)
                        ras2 = MFgis.rasFile2array(optArgs['rasterName'])
                        if not optArgs['ratio']:oras = ras1 - ras2
                        if optArgs['ratio']:oras = (ras1 - ras2) / ras2
                        try:
                            outdata = driver.Create(results, rows, cols, 1, DataType)
                            outdata.SetGeoTransform(geoTrans)
                            outdata.SetProjection(SR)
                            outdata.GetRasterBand(1).WriteArray( oras )
                            outdata.FlushCache()
                        except:
                            outdata.FlushCache()
                            RED     = "\033[1;31m"  
                            RESET   = "\033[0;0m"
                            print(RED,'Raster file: {} could be locked'.format(outputName),RESET)                        
                else:
                    if not optArgs['quiet']:print ("Layers Do Not Match [{} != {}]".format(initLay,layer))
            else:
                if not optArgs['quiet']:print ("Raster Types Do Not Match[{} != {}]".format(initRasType,rasType))
    if optArgs['ListOf2']:
        print ('Processing ListOf2 rasters')
        print(optArgs['ListOf2'])
        if (isinstance(optArgs['ListOf2'],list)):
            ListOF2Str = ' '.join(optArgs['ListOf2'])
            print(ListOF2Str.split(' ')[0])
            optArgs['ListOf2']=ListOF2Str
        if optArgs['noArc']: (SR,geoTrans,cols,rows) = rasProps(optArgs['ListOf2'].split(' ')[0])
        print (optArgs['ListOf2'].split(' ')[0],optArgs['ListOf2'].split(' ')[1])
        (temp_path,Ras1) = os.path.split(optArgs['ListOf2'].split(' ')[0])
        (temp_path,Ras2) = os.path.split(optArgs['ListOf2'].split(' ')[1])
        rasType1, stressPeriod1, layer1 = Ras1.split("_",2)
        rasType2, stressPeriod2, layer2 = Ras2.split("_",2)
        if rasType1 == rasType2 and layer1 == layer2:
            outputName = rasType1 + '_'+stressPeriod1 + "-"+stressPeriod2+'_'+layer1
            print (outputName)
        else:
            print('rasters are mismatched')
            return(0)
        results = os.path.join(oWorkspace,outputName)
        print ("{} minus {} equals {}".format(optArgs['ListOf2'][0],optArgs['ListOf2'][1],outputName))
        if not optArgs['noArc']:
            ras1 = arcpy.Raster(optArgs['ListOf2'][0])
            ras2 = arcpy.Raster(optArgs['ListOf2'][1])
            if not optArgs['ratio']:oras = ras1 - ras2
            if optArgs['ratio']:oras = (ras1 - ras2) / ras2
            oras.save(results)
        else:
            ras1 = MFgis.rasFile2array(optArgs['ListOf2'].split(' ')[0])
            ras2 = MFgis.rasFile2array(optArgs['ListOf2'].split(' ')[1])
            if not optArgs['ratio']:oras = ras1 - ras2
            if optArgs['ratio']:oras = (ras1 - ras2) / ras2
            try:
                outdata = driver.Create(results, rows, cols, 1, DataType)
                outdata.SetGeoTransform(geoTrans)
                outdata.SetProjection(SR)
                outdata.GetRasterBand(1).WriteArray( oras )
                outdata.FlushCache()
            except:
                outdata.FlushCache()
                RED     = "\033[1;31m"  
                RESET   = "\033[0;0m"
                print(RED,'Raster file: {} could be locked'.format(outputName),RESET)
#--------------------------------------------------------------------
#  Provide date_time stamped log file in rasFolder   [KAR Jun 06,2022]
#--------------------------------------------------------------------
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")  
    
    with open(oWorkspace+"/RD3_log.txt", "a+") as logFile:
        appendEOL = False
        # Move read cursor to the start of file.
        logFile.seek(0)
        # Check if file is not empty
        data = logFile.read(100)
        if len(data) > 0:
            logFile.write("\n")
        # Append element at the end of file
        logFile.write(dt_string+':'+runSpyderString)
        logFile.close()
#--------------------------------------------------------------------

def checkExec_env():
    cmdL = False
    a = sys.executable
    m = '\\'
    m = m[0]
    while True:
        b = len(a)
        c = a[(b - 1)]
        if c == m: break
        a = a[:(b - 1)]
    if sys.executable == a + 'python.exe': cmdL=True
    else:
        print (sys.executable)
        cmdL=False
    return (cmdL)


if __name__ == '__main__':

        main()
        print ("End of Execution")


