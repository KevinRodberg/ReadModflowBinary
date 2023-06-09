"""
..module:: ReadModflowBinaryV2
  :
  :    -gui  Entering this optional argument will provide
  :          a Graphical User Interface for all command line arguments
  :
  :synopsis: Read Modflow Binary and create ArcGIS rasters and features
  ::created: 13-Sep-2013
  ::Recent mods: 02-12-2020
  ::Recent mods: 06-30-2021 option to write out ascii file added (BM)  
  ::Recent mods: 05-05-2022 enhanced performance with added seek function 
  ::                        betwwen selected stress periods.  Process just SP 11688 in less than a second.
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
import sys
import time
import glob
import easygui as ez
import RMFB.MFargDefaults.setDefaultArgs as defs
import RMFB.MFgui.MFgui as MFgui
import RMFB.MFbinary.MFbinaryData as mf
import RMFB.MFgis.MFgis as MFgis
from datetime import datetime
try:
    import easygui as ez
except ImportError:
    print('GUI interface not available.')
    
try:
    from osgeo import gdal  #, gdalconst, osr, ogr
except ImportError:
    print("GDAL libraries are not available.")

if sys.version_info[0] == 3:    from tkinter import *
else:  from Tkinter import Tk   ## notice capitalized T in Tkinter

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
    and produce ArcGIS geodatabases of Rasters and Point Features
    or as georeferenced tif files and ESRI shapefiles in a Rasters folder

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

    The following steps show definition of network drive letters to shorten
    command line filename.
        Note:  UNC paths can be used, if mapped drives aren't wanted.

    net use G: \\ad.sfwmd.gov\DFSRoot\data\wsd\GIS\GISP_2012\WorkingDirectory\KAR\ModflowProcessing
    net use M: \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE
    net use T: \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python

    C:\python27\arcGIS10.3\python T:\RMB3.py -mod WCFM -hds -lay 1 -strPer 31 -nam m:\wcfm.nam

    Equivalent UNC:

    C:\python27\arcGIS10.3\python "\\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python\RMB3.py"
        -mod WCFM -hds -lay 1 -strPer 31 -nam \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE\wcfm.nam

A quick Note about
Flow Budget signs (+/-)

  IE: negative FLOW_RIGHT_FACE is actually flow into the eastern Face
  If you see negative FLOW_LOWER_FACE you have vertical flow going up.

"""

def main():
    cmdLine = checkExec_env()
    if cmdLine: print('Running in Command line')
    else: print('Running in Python IDLE')

    global running
    global discDict
    global CBCbytesPer
    CBCbytesPer = 0
    running = True  # Global flag for Terminate Button

#--------------------------------------------------------------------
#   parserArgs is a Namespace and
#   optArgs is a dictionary assigned to parserArgs
#       which can be accessed in the guiArgs function in MFgui module
#           and throughout the program
#--------------------------------------------------------------------
    discDict ={}
    argHelp ={}
    try:
        parserArgs,argHelp = defs.getArgsFromParser()

        optArgs = vars(parserArgs)
        if not optArgs['quiet']:
            for k in optArgs.items():
                label, value = k
                print ("{!s:<15} {!s:>6}".format(label, value))
    except:
        sys.exit(0)
        
    # if not optArgs['ascii']:
    #   optArgs['ascii'] = None
    if not optArgs['quiet']:
       optArgs['quiet'] = True
         
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
          ftypes = ["*.nam", ["*nam*","*.name","Non Standard Namefiles"]]
          reply = ez.fileopenbox(msg=namMsg,title=title,default='*.nam',filetypes=ftypes)
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

        discDict=mf.setDISfile(path, namfile)
        print('discDict defined',discDict)

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
# Reset previously user assigned noArc to True if not able to import arcpy
# mostlikely because it is not being ran from Citrix)
#--------------------------------------------------------------------------
    if not optArgs['noArc']:
        try:
            import arcpy
        except ImportError:
            print ('ESRI ArcGIS arcpy library is not availble')
            optArgs['noArc'] = True

#--------------------------------------------------------------------------
# Compile arguments into a single runstring useful for batch file execution:
#--------------------------------------------------------------------------
    runString = sys.executable.replace('pythonw.exe','python.exe') + " " + \
            r'\\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python' + \
                r'\RMB3.py'
    runSpyderString = "runfile(r'\\\\ad.sfwmd.gov\\dfsroot\\data\\wsd\\SUP\\devel\\source\\Python" + \
                "\\RMB3.py',  " + \
                "wdir=r'\\\\ad.sfwmd.gov\\dfsroot\\data\\wsd\\SUP\\devel\\source\\Python '," +\
                "args='"
    start_time=time.time()

#--------------------------------------------------------------------------
# check each optArg item to see if it has been assigned
#   Each assigned option [key] are paired with str[val]
#       or string converted from a tuple or list and delimited by '|'
#--------------------------------------------------------------------------
    for arg,val in optArgs.items():
      if val:
        for key, value in argHelp.items():
          if value[2] == arg:
       #     print(value[2],arg,len(value))              
            if value[2] == 'ascii':
                print(value)
            if value[2] == 'gui':
                runSpyderString += ' -'+value[2]
            elif len(value) < 4 :
                runString += ' -'+key
                runSpyderString += ' -'+key
            elif value[2] == 'terms':
              runString += ' -terms '
              runSpyderString += ' -terms '
              if type(val) is list or type(val) is tuple:
                  # Add | to separate each terms
                  for trm in val: Sval = '|'.join(map(str,val))
                  runString += '"'+Sval+'"'
                  runSpyderString += '"'+Sval+'"'
              else:
                  # remove single quotes from terms
                  runString += '"'+val.strip('\'')+'"'
                  runSpyderString += '"'+val.strip('\'')+'"'
            elif value[3] != val:
                # DOS likes backslashes
                runString += ' -'+key + ' ' + str(val.replace('/','\\'))
                # Spyder likes forwardslashes
                runSpyderString += ' -'+key + ' ' + str(val.replace('\\','/'))
    runSpyderString += "')"


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
        RED     = "\033[1;31m"  
        BLUE    = "\033[1;34m"
        RESET   = "\033[0;0m"

        print (RED,'Rasters will be created here: ',
               BLUE, optArgs['rasFolder'],RESET)

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

      if (optArgs['model'] in ['C4CDC','NPALM','ECSM','LWCSIM']):
        #print(ocFilename)
        HeadsUnit = mf.getUnitNum(ocFilename_full,1,3)
        #print(ocFilename,HeadsUnit)
        if (HeadsUnit == 'UNIT'):
            HeadsUnit = mf.getUnitNum(ocFilename_full,1,0)
      else:
        print('Retrieving unit number from FREEFORM OC file')
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
#      concfile = os.path.join(path,'MT3D001.UCN')

#      print ("Checking for standard MT3D binary file: ",concfile)
        print ("Checking for MT3D binary file in NAM file ")
#      if not os.path.exists(concfile):
#        print ('...Not found..\n Looking for named binary TDS file in nam file')
        concfile = mf.getFileByNum(os.path.join(path,namfile), 201)
        concfile = os.path.join(path,concfile)
        
        if not os.path.exists(concfile):
            print ("Modflow Concentration file does not exist: ",concfile)
            concfile = os.path.join(path,'MT3D001.UCN')
          #  concfile = os.path.join(path,concfile)
            if not os.path.exists(concfile):      
              print ("Modflow Concentration file does not exist")
              exit(999)
            print('Using standard MT3D binary file: MT3D001.UCN')
        else:          
          print ('Found user defined:',concfile,'.')      
        mf.readBinHead(concfile,'CONC',optArgs)

#--------------------------------------------------------------------------
#   Process binary UZF CellxCell Budgets
#--------------------------------------------------------------------------
    if optArgs['uzfcbc']:
      uzfFilename = mf.FileByInitials(os.path.join(path,namfile), 'UZF')
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
      #print('Ready to readBinCBC',CBCbytesPer)
      ocFilename = mf.FileByInitials(os.path.join(path, namfile), 'OC')
      ocFilename_full = os.path.join(path, ocFilename)
      npers = int(discDict['nperiod'])
      nlays = int(discDict['layer'])
      print(ocFilename_full)
      OCsp=mf.getSP_OC(ocFilename_full, npers, nlays)
      noterms = mf.readCBCterms(path, namfile,optArgs)  #provides OCsp
      mf.readBinCBC(cbcfilename,None,optArgs,OCsp)

#--------------------------------------------------------------------------
#   Setup and process binary LPF CellbyCell and Create Flow Vectors:
#--------------------------------------------------------------------------
    if optArgs['vector']:
      if 'OCsp' not in locals():
          ocFilename = mf.FileByInitials(os.path.join(path, namfile), 'OC')
          ocFilename_full = os.path.join(path, ocFilename)
          npers = int(discDict['nperiod'])
          nlays = int(discDict['layer'])
          OCsp=mf.getSP_OC(ocFilename_full, npers, nlays)
          noterms = mf.readCBCterms(path, namfile,optArgs)  #provides OCsp
      else:
          print('OCsp defined earlier')
      cbcfilename=mf.identBudFile(path,namfile)
      if optArgs['terms'] != 'RIGHT|FRONT':
        optArgs['terms'] = 'RIGHT|FRONT'
        print ("""Overriding terms option for flow vectors:
           required terms are -- 'RIGHT|FRONT'
           indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE """)
      mf.readBinCBC(cbcfilename,'VEC',optArgs,OCsp)

#--------------------------------------------------------------------------
#   Aggregate rasters from current workspace with  MEAN, MAX, or MIN
#--------------------------------------------------------------------------
    if optArgs['aggregate']:
        for process in ['heads','conc','terms']:
            rasTypes =[]
            if optArgs['heads'] and process == 'heads':
                rasTypes = ['HEAD']
            elif optArgs['conc'] and process == 'conc':
                rasTypes = ['CONC']
            elif type(optArgs['terms']) == list and process == 'terms':
                rasTypes= optArgs['terms']
            elif optArgs['terms']:
              if len(optArgs['terms']) > 0 and process == 'terms':
                if type(optArgs['terms']) == list:
                    rasTypes = optArgs['terms']
                else:
                    rasTypes= optArgs['terms'].split("|")
                if  optArgs['vector'] :
                    rasTypes.remove('RIGHT')
                    rasTypes.remove('FRONT')
                    print('No aggregation for rasters supporting -vec processing')
            if(len(rasTypes)>0) or not optArgs['noArc']:
                print('\nCreating '+str(optArgs['aggregate']).upper()+' rasters for '+ str(rasTypes))
            else:
                if rasTypes:
                    print('Aggregation is not currently available with the options currently selected for '+ str(rasTypes))
            if optArgs['layerStr']:
                layerList = mf.parseRange(optArgs['layerStr'])
            else:
                layerList = mf.parseRange('1-'+mf.discDict['layer'])
            for typ in rasTypes:
                for lay in layerList:
                    # Search for budget raster with different wildCard pattern than Heads or Conc
                    # Currently ignores clp rasters
                    for pref in ['clp','']:
                        if optArgs['terms'] and process == 'terms' :
                            wildCardStr = '_'+str(lay)+'_*.tif'
                        else:
                            wildCardStr = '*_'+str(lay)+'.tif'
                        tifFiles = glob.glob(optArgs['rasFolder']+'\\'+pref+typ+wildCardStr)

                        L = [np.array(MFgis.rasFile2array(rasFile)) for rasFile in tifFiles
                             if 'clp' not in rasFile]
                        if len(L)> 0:
                          try:
                              if optArgs['aggregate'] == 'mean':
                                  summaryRas=np.mean(L,axis=0)
                                  print(optArgs['rasFolder']+'\\MEAN_'+pref+typ+'_'+str(lay))
                                  rasName=optArgs['rasFolder']+'\\MEAN_'+pref+typ+'_'+str(lay)
                              elif optArgs['aggregate'] == 'min':
                                  summaryRas=np.min(L,axis=0)
                                  rasName=optArgs['rasFolder']+'\\MIN_'+pref+typ+'_'+str(lay)
                              elif optArgs['aggregate'] == 'max':
                                  summaryRas=np.max(L,axis=0)
                                  rasName=optArgs['rasFolder']+'\\MAX_'+pref+typ+'_'+str(lay)
                              elif optArgs['aggregate'] == 'sum':
                                  summaryRas=np.sum(L,axis=0)
                                  rasName=optArgs['rasFolder']+'\\SUM_'+pref+typ+'_'+str(lay)
                              print('creating:',optArgs['aggregate']+' '+pref+typ+'_'+str(lay))
                              MFgis.numPy2Ras(summaryRas, rasName, optArgs, discDict)
                          except:
                              print('Summary Raster failed to calculate',optArgs['aggregate'],
                                    'for ', optArgs['aggregate']+' '+pref+typ+'_'+str(lay))
                              print('raster dimension:')
                              for x in L:
                                   print(x.shape)

#--------------------------------------------------------------------------
#   End of the program
#--------------------------------------------------------------------------

#   Define console print colors                                   
    RED     = "\033[1;31m"  
    YELLOW  = "\033[1;33m"  
    BLUE    = "\033[1;34m"
    CYAN    = "\033[1;36m"
    GREEN   = "\033[0;32m"
    RESET   = "\033[0;0m"
    BOLD    = "\033[;1m"
    REVERSE = "\033[;7m"    
                              
    if '-vec' in runString:
      print(RED,"""
      Notes for Flow Vectors:""")
      print(BLUE,"""      Symbology in ArcMap should have template arrow pointing East 
      with Advanced Symbology options type set for Dir as Geographic 
      """)
                               
    print(RED,"Command line execution string:")
    print(GREEN,"{}".format(runString))
    print(RED,"Spyder console execution string arguments:")
    print(GREEN,"{}".format(runSpyderString))
    print(RESET,round(time.time()-start_time,2), ' seconds execution time')

#--------------------------------------------------------------------
#  Provide date_time stamped log file in rasFolder   [KAR Jun 06,2022]
#--------------------------------------------------------------------
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")  
    
    with open(optArgs['rasFolder']+"/RMB3_log.txt", "a+") as logFile:
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
#  cmdLine variable is used to determine gui options
#--------------------------------------------------------------------
if __name__ == '__main__':
        main()

