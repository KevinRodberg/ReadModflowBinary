"""
..module:: ReadModflowBinaryV2
  :
  :    -gui  Entering this optional argument will provide 
  :          a Graphical User Interface for all command line arguments
  :
  :synopsis: Read Modflow Binary and create ArcGIS rasters and features
  ::created: 13-Sep-2013
  ::Recent mods: 10-23-2019
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
import sys
import time
import easygui as ez
import MFargDefaults.setDefaultArgs as defs
import MFgui.MFgui as MFgui
import MFbinary.MFbinaryData as mf
import MFgis.MFgis as MFgis
try:
    from osgeo import gdal, gdalconst, osr, ogr
except ImportError:
    print("GDAL libraries are not available.")

if sys.version_info[0] == 3:    from tkinter import *  
else:  from Tkinter import *   ## notice capitalized T in Tkinter
    
import numpy as np
import os
import re
  
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

"""    
..Program Description::
    ReadModflowBinaryV2 is designed to post process Modflow model output 
    and producing ArcGIS geodatabases of Rasters and Point Features
    or as georeferenced raster tif files and ESRI shapefiles in a Rasters folder

    Reading Binary Heads, TDS Concentrations, SWI Zetas and CellXCell budgets 
    terms are supported for the following models:
        ECFT,ECFTX,LKBGWM,LECSR,C4CDC,NPALM,LWCSAS,LWCSIM,LWCFAS,ECFM,WCFM

    Python script compatible to run with:
        ArcGIS/w Python 2.7 (pythonwin) 
            configured to support pandas, numpy, and arcpy
    or:
        Python 3.6 configured to support pandas, numpy and gdal

    This python program provides alternate user interfaces:
      GUI interface for argument and keyword selection
        (when supplied -gui command line arg)
      Command line argument parser works with python or pythonwin
        (Argument usage and help  available with -h)
      Batch execution using python.exe
        (if arguments are understood and known in advance)

    If ArcGIS is avaialble on the host a Modflow model is ran with 
    Batch processing is an ideal approach for post processing 
    model runs. A couple extra steps can be added to an existing batch file 
    to execute post processing steps when the model finishes.
    
    The following steps show definition of network drive letters to shorten 
    command line filename.

    Note:  UNC paths can be used, if mapped drives aren't wanted.
    
    net use G: \\ad.sfwmd.gov\DFSRoot\data\wsd\GIS\GISP_2012\WorkingDirectory\KAR\ModflowProcessing
    net use M: \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE
    net use T: \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python\ReadModflowBinary
                        
    C:\python27\arcGIS10.3\python T:\ReadModflowBinary.py -mod WCFM -hds -lay 1 -strPer 31 -nam m:\wcfm.nam

    Equivalent UNC:

    C:\python27\arcGIS10.3\python \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python\ReadModflowBinary\ReadModflowBinary.py
        -mod WCFM -hds -lay 1 -strPer 31 -nam \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE\wcfm.nam
"""

def main():
#--------------------------------------------------------------------   
#   GUI to select Namefile if not provided on command line
#--------------------------------------------------------------------     
    if not optArgs['namefile']:
      optArgs['gui'] = True
      title ="Read Modflow Bianry Produces ArcGIS Rasters and Features"
      namMsg = """
      Please locate and select a Modflow name file
      which will properly identify the model results to process"""
      reply = None
      while True:
        if not optArgs['namefile']:
          ftypes = ["*.nam", ["*.txt","*.name","Non Standard Namefiles"]]
          reply = ez.fileopenbox(msg=namMsg,title=title,default='*',filetypes=ftypes)
        else: break
        if reply: break
      if reply: optArgs['namefile'] = reply
      print ("{} has been selected as the Namefile for {} model."\
             .format(optArgs['namefile'],optArgs['model']))
    if optArgs['namefile']:
        (path, namfile) = os.path.split(optArgs['namefile'])
        if path == '':
          print ("""Explicit path missing.  
                Using default path for testing""")
          path = 'H:\\'
        global discDict
        discDict=mf.setDISfile(path, namfile)
        
    else:
        print ("""Unable to process Binary data without file location details.
        nam/namfile argument is required:
            -nam NAMEFILE,
            --namfile=NAMEFILE  Read data from .NAM FILE""")
        exit()
        
#--------------------------------------------------------------------------
#  GUI interface option selection
#--------------------------------------------------------------------------
    if optArgs['gui']:   MFgui.guiArgs(optArgs,argHelp)
    
#--------------------------------------------------------------------------
# Compile arguments into a single runstring useful for batch file execution:
#--------------------------------------------------------------------------
    runString = r'C:\Python27\ArcGIS10.3\python.exe' + \
            r'\\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python' + \
                r'\ReadModflowBinary\ReadModflowBinaryV2.py'
    start_time=time.clock()
            
#--------------------------------------------------------------------------                
# check each optArg item to see if has been assigned
#   Each assigned option [key] are paired with str[val]
#       or string converted from a tuple or list and delimited by '|'
#--------------------------------------------------------------------------
    for arg,val in optArgs.items():
      if val:
        for key, value in argHelp.items():
          if value[2] == arg:
            if value[2] == 'gui':  pass
            elif len(value) < 4 :  runString += ' -'+key                    
            elif value[3] != val:  runString += ' -'+key + ' ' + str(val)
            elif value[2] == 'terms': 
              runString += ' -terms '
              if type(val) is list or type(val) is tuple:
                  for trm in val: Sval = '|'.join(map(str,val))
                  runString += '"'+Sval+'"'
              else: runString += '"'+val.strip('\'')+'"'
                      
#--------------------------------------------------------------------------                       
# Reset previously user assigned noArc to True if not able to import arcpy  
# mostlikely because it is not being ran from Citrix)       
#--------------------------------------------------------------------------
    if not optArgs['noArc']:
        try:
            import arcpy
        except ImportError:
            print ('ESRI ArcGIS arcpy library is not availble')
            optArgs['noArc'] = True
            
    print ("""Command line execution string:
    {} 
    """.format(runString))
        
#--------------------------------------------------------------------------                       
#   Define workspace areas, depending upon availability of arcpy functions
#--------------------------------------------------------------------------                       
    if not optArgs['noArc']:
        MFgis.getSpatialA()
        if not optArgs['geodb']:  optArgs['geodb'] = r'H:\Documents\ArcGIS\Default.gdb'
        arcpy.env.workspace = MFgis.setWorkspc(optArgs['geodb'])
        if optArgs['clpgdb']: print ("Clip Workspace = {}".format(optArgs['clpgdb']))
        else:
            optArgs['clpgdb']=optArgs['geodb']
            print ("No Clip Workspace defined...")
            print("Using Primary Workspace if Clipped Rasters are needed")
        arcpy.env.workspace = MFgis.setWorkspc(optArgs['clpgdb'])
    else:
        print ('Rasters will be created here: ' + optArgs['rasFolder'])
        
#--------------------------------------------------------------------------                       
#   Define Clipping Extents if needed
#--------------------------------------------------------------------------                       
    if optArgs['clipBox']:
      if not optArgs['clipBox'] != 'Default.shp':
        clips = MFgis.modelClips(optArgs['model'])
        if clips == (0,0,0,0):  print ("No default clip extents")
        else: print("clip extents={} for {}".format(clips, optArgs['model'] ))
      else: print ("No clip extents")
        
#--------------------------------------------------------------------------                       
#   Process binary Heads file:
#--------------------------------------------------------------------------   
    if optArgs['heads']:
      ocFilename = mf.FileByInitials(os.path.join(path, namfile), 'OC')
      ocFilename_full = os.path.join(path, ocFilename)
      print ("Output Control filename: {}".format(ocFilename))

      if (optArgs['model'] in ['C4CDC','NPALM','ECFTX']):
        HeadsUnit = mf.getUnitNum(ocFilename_full,1,3)
      else:
        HeadsUnit = mf.getUnitNum(ocFilename_full,1,0)

      headsfile = mf.getFileByNum(os.path.join(path,namfile),HeadsUnit)
      headsfile = os.path.join(path,headsfile)
      print ("heads binary filename: {}".format(headsfile))
      
      mf.readBinHead(headsfile,'HEAD',optArgs)
      
#--------------------------------------------------------------------------                       
#   Process SWI Zeta file:
#       returned results have not been tested       
#-------------------------------------------------------------------------- 
    if optArgs['zeta']:
      swiFilename = mf.FileByInitials(os.path.join(path,namfile), 'SWI2')
      swiFilename_full = os.path.join(path,swiFilename)
      zetaUnit = mf.getUnitNum(swiFilename_full,1,4)
      
      zetafilename = mf.getFileByNum(os.path.join(path,namfile), zetaUnit)
      zetafilename = os.path.join(path,zetafilename)
      print ("....attempting to process zeta binary file")
      print (zetafilename)
      
      mf.readBinHead(zetafilename,'HEAD',optArgs)
      
#--------------------------------------------------------------------------                       
#   Process binary TDS concentrations
#       Currently input filename is hard coded      
#-------------------------------------------------------------------------- 
    if optArgs['conc']:
      concfile = os.path.join(path,'MT3D001.UCN')
      print ("....attempting to process MT3D binary file")
      if not os.path.exists(concfile):
        print ("Modflow Concentration file does not exist")
        exit(999)
      mf.readBinHead(concfile,'CONC',optArgs)

#--------------------------------------------------------------------------                       
#   Process binary UZF CellxCell Budgets
#-------------------------------------------------------------------------- 
    if optArgs['uzfcbc']:
      uzfFilename = FileByInitials(os.path.join(path,namfile), 'UZF')
      uzfFilename_full = os.path.join(path,uzfFilename)
      uzfUnit = getUnitNum(uzfFilename_full,1,6)
      
      uzfcbcfilename = getFileByNum(os.path.join(path,namfile), uzfUnit)
      uzfcbcfilename = os.path.join(path,uzfcbcfilename)
      print ("CellxCell Flow filename: {}".format(uzfcbcfilename))
      
      mf.readBinCBC(uzfcbcfilename,None,optArgs)
      
#--------------------------------------------------------------------------                       
#   Setup and process binary LPF Cell by cell Budgets:
#-------------------------------------------------------------------------- 
    if optArgs['cbc']:
      cbcfilename=mf.identBudFile(path,namfile)
      mf.readBinCBC(cbcfilename,None,optArgs)
      
#--------------------------------------------------------------------------                       
#   Setup and process binary LPF CellbyCell and Create Flow Vectors:
#-------------------------------------------------------------------------- 
    if optArgs['vector']:
      cbcfilename=mf.identBudFile(path,namfile)
      if optArgs['terms'] != 'RIGHT|FRONT':
        optArgs['terms'] = 'RIGHT|FRONT'
        print ("""Overriding terms option for flow vectors: 
           required terms are -- 'RIGHT|FRONT' 
           indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE """)
            
      mf.readBinCBC(cbcfilename,'VEC',optArgs)
      
#--------------------------------------------------------------------------                       
#   Clean up memory and release Spatial Analyst if using arcpy on Citrix
#-------------------------------------------------------------------------- 
    if not optArgs['noArc']:
        MFgis.clearINMEM()
        arcpy.CheckInExtension("Spatial")
        
#--------------------------------------------------------------------------                       
#   End of the program
#-------------------------------------------------------------------------- 
    print ("...finished")
    print(time.clock()-start_time, ' seconds execution time')

#--------------------------------------------------------------------
#  cmdLine variable is used to determine gui options
#--------------------------------------------------------------------
if __name__ == '__main__':
    cmdLine = checkExec_env()
    if cmdLine:
        print('Running in Command line')
  #      pool = multiprocessing.Pool()        
    else:
        print('Running in Python IDLE')
  #  platform = (None, 'mp')[cmdLine]

    global running
    running = True  # Global flag for Terminate Button

#--------------------------------------------------------------------
#   parserArgs is a Namespace and
#   optArgs is a dictionary assigned to parserArgs
#       which can be accessed in the guiArgs function in MFgui module
#           and throughout the program
#--------------------------------------------------------------------   
    discDict ={}
    argHelp ={}
    parserArgs,argHelp = defs.getArgsFromParser()
    optArgs = vars(parserArgs)
    for k in optArgs.items():
      label, value = k
      print ("{!s:<15} {!s:>6}".format(label, value))
    main()  
    