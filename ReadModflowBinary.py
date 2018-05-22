"""
..module:: ReadModflowBinary
  :
  :	-gui  Enter this optional argument will provide 
  :	      a Graphical User Interface for all command line arguments
  :
  :synopsis: Read Modflow Binary and create ArcGIS rasters and features
  ::created: 13-Sep-2013
  ::Recent mods: 04-Aug-2017
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

..Program Description::
    ReadModflowBinary is designed to post process Modflow model
    output and produce results in ArcGIS geodatabases as Rasters
    and Point Features.

    Reading Binary Heads, TDS Concentrations, SWI Zetas and CellXCell
    budgets terms are supported for the following models:

    ECFT,ECFTX,LKBGWM,LECSR,C4CDC,NPALM,
    LWCSAS,LWCSIM,LWCFAS,ECFM,WCFM

    It's primary purpose is to produce ArcGIS datasets, which
    means ArcGIS is a minimum requirement, either with a local install
    or Citrix with Python 2.7 configured to support pandas, numpy, and arcpy.

    This python program provides alternate user interfaces:
    GUI interface for argument and keyword selection
        (when supplied -gui command line arg)
    Command line argument parser works with python or pythonwin
        (Argument usage and help  available with -h)
    Batch execution using python.exe
        (if arguments are understood and known in advance)

    If ArcGIS is avaialble on host the Modflow model is ran on
    Batch processing is an ideal approach for post processing 
    model runs. A couple extra steps can be added to an existing
    batch file to post process when the model finishes.
    The following steps show definition of network drive letters
    to shorten command line filename.

    UNC paths can be used, if mapped drives aren't wanted.
    
    net use G: \\ad.sfwmd.gov\DFSRoot\data\wsd\GIS\GISP_2012
                        \WorkingDirectory\KAR\ModflowProcessing
    net use M: \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE
    net use T: \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel
                        \source\Python\ReadModflowBinary
                        
    C:\python27\arcGIS10.3\python T:\ReadModflowBinary.py
                -mod WCFM -hds -lay 1 -strPer 31 -nam m:\wcfm.nam

    Equivalent UNC:

    C:\python27\arcGIS10.3\python \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel
            \source\Python\ReadModflowBinary\ReadModflowBinary.py
            -mod WCFM -hds -lay 1 -strPer 31
            -nam \\whqhpc01p\hpcc_shared\krodberg\WCFM\TRANS_COUPLE\wcfm.nam
"""
#
#   Import python modules
#

import sys
import easygui as ez
from Tkinter import *
import numpy as np
import pandas as pd
import os
import arcpy
import re
import argparse
import textwrap

def setDefaultArgs():
#
#   Define dictionary of arguments to use in ArgumentParser
#    
  resampleHelp="""\
    Resampling appropriately aggregates values from model results
      -Heads are averaged
      -Flow Magnitudes are summed
      -Flow Direction is averaged
      --------------------------
      -res 5 Aggregates 5x5 grid
      -res 1 Default or no resampling:[1x1]
      """
  
  modelHelp="""\
    Model defines Spatial Reference
    and Raster Lower Left Origin
    """
  
  stressPerHelp="""\
    Define Stress Periods to process:
    -- One stress period: '-strPer 218'  
    -- Multiple stress periods: '-strPer 1-12,218,288'
    -- Omit option [-strPer] for all stress periods
    -- Use '-strPer 0' for none (option testing)
    """
  
  layerHelp = """\
    Define Layers to process:
    -- Single layer:    '-lay 1'
    -- Multiple layers: '-lay 1,3-4,7'
    -- No Layers:       '-lay 0'
    -- All Layers:      '-lay None'
    -- Command line Default is all layers
    """

  termsHelp = """\
    Process 'Terms' for CellxCell budget.
    -- 'FLOW' indicates processing Right, Front and Lower face flow
    -- 'RIGHT|FRONT' indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE
    --  No parameters indicates all budget terms
    """
  
  argHelp={
    'bud':
    ['option',"Process CellxCell budgets",'cbc'],
    'gui':
    ['option',"GUI for options & arguments",'gui'],
    'hds':
    ['option',"Process Heads file.",'heads'],
    'swi':
    ['option',"Process SWI Zetas file.",'zeta'],
    'res':
       ['getArg',resampleHelp,'resample','1'],
    'tds':
    ['option',"Process TDS from MT3D file.",'conc'],
    'uzf':
    ['option',"Process UZF cellbycell budgets.",'uzfcbc'],
    'vec':
    ['option',"Process Flow budgets for flow vectors",'vector'],
    'mod':
    ['getArg',modelHelp,'model',None,model_choices],
    'nam':
    ['getArg',"Assign Modflow .NAM FILE",'namefile',None],
    'gdb':
    ['getArg',"Save rasters in GeoDatabase.",'geodb',
     r'H:\Documents\ArcGIS\Default.gdb'],
    'clpbox':
    ['getArg',"Clip rasters to extent.",'clipBox','Default.shp'],
    'clpgdb':
    ['getArg',"Separate Geodatabase for Clipped Rasters",'clpgdb',
     r'H:\Documents\ArcGIS\Default.gdb'],
    'strPer':
    ['getArg',stressPerHelp,'strStr',None],
    'lay':
    ['getArg',layerHelp,'layerStr',None],
    'terms':
    ['getArg',termsHelp,'terms',None]
    }

  return argHelp

def getArgsFromParser():
#
#   Loop through argHelp dictionary to add arguments to ArgumentParser
#
  parser = argparse.ArgumentParser(prog='ReadModflowBinary',
          formatter_class=argparse.RawTextHelpFormatter)
  argHelp=setDefaultArgs()
  for label, value in sorted(argHelp.iteritems()):
    parseArg = '-'+label
    
    if value[0] == 'option' :
      """
      True or False arguments mainly used to flag the types of binary
      data to process.
      parseArg == '-gui' invokes the qui tool to set/modify options      
      """
      parser.add_argument(parseArg,dest=argHelp[label][2],
          action="store_true",
          help=textwrap.dedent(argHelp[label][1]))

    elif len(argHelp[label]) <5:
      """
      argHelp value lists for non=true/false arguments
      define destination variable as item 2
      and item 3 provides default values      
      """
      parser.add_argument(parseArg,dest=argHelp[label][2],
          default=argHelp[label][3],          
          help=textwrap.dedent(argHelp[label][1]))
    else:
      """
      argHelp value lists with 5 items provide a list for
      ArgumentParser.choices      
      """
      parser.add_argument(parseArg,dest=argHelp[label][2],
          default=argHelp[label][3],
          choices=argHelp[label][4],
          help=textwrap.dedent(argHelp[label][1]))

  args = parser.parse_args()
  return args,argHelp

def parseRange(astr):
#
#   Parse a string to create list of values from input range
#      such as 1-5 produces 1,2,3,4,5
#      or 1,3-5,7 produces 1,3,4,5,7
#    
  result=set()
  if astr != None:
    for part in astr.split(','):
      x=part.split('-')
      result.update(range(int(x[0]),int(x[-1])+1))
  return sorted(result)

def getSpatialA():
#
#   Check availability and check out the ArcGIS Spatial Analyst
#   extension license required for processing binary modflow
#   output to ArcGIS rasters.  Exit program if not available.
#    
  availability = arcpy.CheckExtension("Spatial")
  if availability == "Available":
    print "Check availability of SA"
    arcpy.CheckOutExtension("Spatial")
    print("SA Ext checked out")
  else:
    print("Spatial Analyst Extensionis not available")
    print("Please ask someone who has it checked out")
    print("but not using to turn off the extension")
    exit()
  return

def getUnitNum(file, row_num, item_num):
#
#    Open and read the Modflow Output Control file
#    assign each line read to row[].
#
#    Parse selected row_num and assign
#    parsed item_num to unitnum.
#
#    If item_num == 0 use last item in the row
#
  row=[]
  try:
    f = open(file,'r')
  except IOError:
    print IOError
  else:      
    with f:
      for line in f.readlines(10):
        if not line.startswith('#'):
          row.append(line.split())
          if line[0] != 'HEAD' and row_num == 1 and item_num == 0:
            row_num = 1
            item_num = 4
          elif line[0] != 'HEAD' and row_num == 1 and item_num == 10:
            row_num = 1
            item_num = 0
  f.close()
  select_row = row[row_num-1]
  unitnum = select_row[item_num-1]
  del row
  return unitnum

def getFileName(sourcefile,pkgInitials):
#
#   Read Modflow Namefile searching for package initials
#   and return associated filename
#
  binlist=[]
  header = ['Initials', 'unitnum', 'filename', 'status']
  binlist.append(header)
#  print ("NameFile: \t %s" % sourcefile)
  with open(sourcefile, 'r') as f:
    for line in f.readlines()[1:]:
      if (not line.startswith('#') ):
        if len(line) >1:
         binlist.append(line.split()[0:4])
  f.close()

  df = pd.DataFrame(binlist, columns = header)
  newdf = df[df['Initials'] == pkgInitials]
  fileName = newdf['filename']

  theval = str(fileName.values)
  outval = theval.lstrip("['")
  outval = outval.rstrip("']")
  fileName = outval
  del df, newdf
  return fileName

def getFileByNum(sourcefile,fnumber):
#
#   Read Modflow Namefile searching for unit number
#   and returning associated filename
#    
  binlist=[]
  header = ['Initials', 'unitnum', 'filename', 'status']
  binlist.append(header)

  with open(sourcefile, 'r') as f:
    for line in f.readlines()[1:]:
      if not line.startswith('#'):
        binlist.append(line.split()[0:4])
  f.close()

  df = pd.DataFrame(binlist, columns = header)
  newdf = df[df['unitnum'] == fnumber]
  _unitnum = newdf['unitnum']
  _filename = newdf['filename']
  theval = str(_filename.values)
  outval = theval.lstrip("['")
  outval = outval.rstrip("']")
  filename = outval

  del df, newdf, _unitnum, _filename
  return filename

def getBASdata(file):
#
#   Read older Modflow BAS file rather than the newer DIS
#   files to populate the discritization dictionary: discDict
#
  global discDict
  row=[]
  print (file)
  with open(file, 'r') as f:
    for line in f.readlines(10):
      if not line.startswith('#'):
        row.append(line.split())
  f.close()

  layer = row[2][0]
  nrows = row[2][1]
  ncols = row[2][2]
  nper =  row[2][3]
  
  discDict['layer']=layer
  discDict['nrows']=nrows
  discDict['ncols']=ncols
  discDict['nperiod']=nper
  del row
  return 

def getBCFdata(file):
#
#   Read Modflow BCF when newer DIS file is not available
#   to populate the discretization dictionary: discDict
#    
  global discDict
  row=[]
  print (file)
  with open(file, 'r') as f:
    for line in f.readlines(10):
      if not line.startswith('#'):
        row.append(line.split())
  f.close()

  chkstr= row[5][1].find('(')
  if chkstr < 0:
    cellsize1 = row[4][1]
    cellsize2 = row[5][1]
  else:
    cellsize1 = row[4][1][:chkstr]
    cellsize2 = row[5][1][:chkstr]

  discDict['cellsize1']= cellsize1
  discDict['cellsize2']= cellsize2
  
  return 

def getDISdata(file):
#
#   Populate discretization dictionary from
#   the Modflow DIS file
#
  global discDict
  row=[]
  print (file)
  with open(file, 'r') as f:
    for line in f.readlines(10):
      if not line.startswith('#'):
        row.append(line.split())
  f.close()

  layer = row[0][0]
  nrows = row[0][1]
  ncols = row[0][2]
  nper  = row[0][3]

  chkstr= row[3][1].find('(')
  if chkstr < 0:
    cellsize1 = row[2][1]
    cellsize2 = row[3][1]
  else:
    cellsize1 = row[2][1][:chkstr]
    cellsize2 = row[3][1][:chkstr]

  discDict = {'layer':layer,
        'nrows':nrows,
        'ncols': ncols,
        'nperiod': nper,
        'cellsize1': cellsize1,
        'cellsize2': cellsize2}
  return 

def modelDisc():
#
#   Deconstruct the discDit returning
#   Modflow layer, row, column,
#   stress periods and cell sizes
#
  global discDict
  nlays = int(discDict['layer'])
  nrows = int(discDict['nrows'])
  ncols = int(discDict['ncols'])
  npers = int(discDict['nperiod'])
  cellsz1 = float(discDict['cellsize1'])
  cellsz2 = float(discDict['cellsize2'])
  return nlays,nrows,ncols,npers,cellsz1,cellsz2

def identBudFile():
#
#   Determine the filename for the CellxCell budget file
#   based on Namefile Package Initials
#    
  cbcPkgFilename = getFileName(os.path.join(path,namfile), 'LPF')
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = getFileName(os.path.join(path,namfile), 'BCF6')
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = getFileName(os.path.join(path,namfile), 'BCF')
    # BCF uses the older 'UNFORMATTED' FORTRAN binary output
    form='UF'
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = getFileName(os.path.join(path,namfile), 'UPW')    
  if cbcPkgFilename.strip() == "":
    print(" No supported flow Packages (BCF,BCF6,LPF or UPW) found in NAM file")
    exit(86)    
  cbcPkgFullName = os.path.join(path,cbcPkgFilename) 
  cbcUnit = getUnitNum(cbcPkgFullName,1,1)
  if int(cbcUnit) == 0:
    cbcUnit = getUnitNum(cbcPkgFullName,1,2)
  cbcFilename = getFileByNum(os.path.join(path,namfile), cbcUnit)
  binfilename = os.path.join(path,cbcFilename) 
  print ("CellxCell Flow filename {} on unit {}"\
         .format(binfilename,cbcUnit))
  return(binfilename)

def numPy2Ras(npArray, rasName):
#
#   Converts NumPy Array read from Modflow Binary
#   into an ArcGIS raster with appropriate Spatial
#   Reference for the Model being processed
#   Saving the raster to the proper Workspace
#
  dfval=[]
  dfattrib=[]
  cellsz1 = float(discDict['cellsize1'])
  cellsz2 = float(discDict['cellsize2'])
  llorigin = modelOrigins[optArgs['model']]
  SR = arcpy.SpatialReference(model_SR[optArgs['model']])  
  print ""
  ras = arcpy.NumPyArrayToRaster(npArray,llorigin,cellsz1,cellsz2,999)
  if 'IN_MEMORY' in rasName:
      print ("In_Memory Raster: {}".format(rasName))
      rasFilename = rasName
  elif 'clp' in rasName:
    rasFilename = os.path.join(optArgs['clpgdb'], rasName)
    print ("Clipped Raster: {} {}".format(optArgs['clpgdb'], rasName))
  else:
    rasFilename = os.path.join(optArgs['geodb'], rasName)
    print ("Raster: {}".format(rasName))
  ras.save(rasFilename)
  arcpy.DefineProjection_management(ras, SR)
#  if optArgs['view']:
#  GIFfile= 'H:/Documents/ArcGIS/'+rasName+'.gif'
#  if arcpy.Exists(GIFfile):
#    os.remove(GIFfile)
#    print ("removed {}".format(GIFfile))
#  arcpy.env.workspace = fgdb
#  print ("""
#    {}
#    {}
#    {}
#    """.format(arcpy.env.workspace, rasName, GIFfile))
#  arcpy.CopyRaster_management(rasName,GIFfile,
#                                "DEFAULTS","","","NONE" ,
#                                "NONE","8_BIT_UNSIGNED",
#                                "NONE","NONE")
#  root = Toplevel()
#  snapshot = PhotoImage(file=GIFfile)
#  explain = "Raster 1"
#  w = Label(root,
#            compound=CENTER,
#            text=explain,
#            image=snapshot).pack(side="right")
#  root.mainloop()
#    print("Raster Conversion failed")
#  """
  del npArray, ras
  return

def clipRaster(InRastername):
#
#   Clip ArcGIS raster to default extents
#   defined for the model being processed
#   or to the extents of a user defined Shapefile
#
  ws1 = optArgs['geodb']
  ws2 = optArgs['clpgdb']
  defClip=modelClips[optArgs['model']]
  path, ras = os.path.split(InRastername)
  if optArgs['clipBox'] != 'Default.shp':
    desc = arcpy.Describe(optArgs['clipBox'])
    ExtObj = desc.extent
    clip = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin,
                ExtObj.XMax, ExtObj.YMax)
  else:
    clip = "%d %d %d %d" % (defClip[0],defClip[1],
                defClip[2],defClip[3])
  clpRaster = "clp" +ras
  
  if defClip != (0,0,0,0):
    if path == 'IN_MEMORY':
      arcpy.env.workspace = r'IN_MEMORY'
    else:
      arcpy.env.workspace = ws2
    print ("Input Workspace: {}".format(ws1))
    print ("Current Workspace: {}".format(arcpy.env.workspace))
    print ("Input Raster path : {}".format(path))
    print ("Input Raster: {}".format(ras))
    InRasFullame = os.path.join(ws1,ras)
    print ("Input Raster: {}".format(InRasFullame))
    
    arcpy.gp.ExtractByRectangle_sa(InRasFullame,clip,clpRaster,"INSIDE")
    print ("Clipped Raster: {} {}".format(arcpy.env.workspace,clpRaster))
    arcpy.env.workspace = ws1
  else:
    pass
#    print("Clip Extent is undefined. Not producing {}".format(clpRaster))
  return

def magDirFunc(rFaceSlice, fFaceSlice):
#
#   Calculate Four-Quadrant Inverse Tangent
#   and convert radians to degrees
#   Negative results for degrees are adjusted
#   to reflect range from 180 thru 360 
#
  tmpdirSlice = np.arctan2(fFaceSlice,rFaceSlice)*180 / np.pi
  dirSlice = np.where(tmpdirSlice > 0.0,tmpdirSlice,(tmpdirSlice+360.0))
  magSlice = np.power((np.power(fFaceSlice,2)+np.power(rFaceSlice,2)),.5)
  return magSlice, dirSlice

def readBinHead(binfilename,binType):
#
#   Read Modflow 2D Binary file
#   such as the HEADS and CONC
#       Each non-Header Record is a layer
#       read as a 2D NumPy array (nrows,ncols)
#
  layerRange = optArgs['layerStr']
  strPerRange = optArgs['strStr']
  getSpatialA()
  read_data=[]
  nlays,nrows,ncols,npers,cellsz1,cellsz2=modelDisc()
  
  Hdr=binHdr[binType]
  knt= int(nrows)*int(ncols)
  shape = (nrows,ncols)
  if layerRange:
    layerList = parseRange(layerRange)
  else:
    layerList = parseRange('1-'+str(nlays))
  if strPerRange:
      strPerList = parseRange(strPerRange)
      maxStrPer =  max(strPerList)
  else:
      strPerList = None
      maxStrPer = npers + 1
  try:
      binfile=open(binfilename,'rb')
  except:
      print("binary heads file {} does not exist".format(binfilename))
      exit(86)
  endOfTime = False

  for strPerByLay in xrange(int(npers*nlays)):
    #Check root to see if process should be terminated
    if not cmdLine:
      root.update()
    #print ("checking Button Status...Condition = {}".format(running))
      if not running:
        root.destroy()
        exit(7)
    
    MFhdr  = []
    MFhdr  = np.fromfile(binfile,Hdr,count=1,sep='')
    if not MFhdr:
        exit(99)
    print (MFhdr)    
    kper   = MFhdr['KPER'][0]
    totim  = MFhdr['TOTIM'][0] 
    k      = MFhdr['K'][0]
    if binType == 'CONC':
        kper = int(totim)
    read_data = np.fromfile(file=binfile, dtype=np.float32,
                count=knt, sep='').reshape(shape)
#    print ("Min {}, max {}".format(np.amin(read_data), np.amax(read_data)))
    
    rastername = binType + '{:7.5f}'.format(((kper)/100000.0))+"_"+str(k)
    rastername = rastername.replace("0.","_")
    if layerList != [0] or strPerList != [0]:
      if k in layerList:
        if not strPerList or kper in strPerList:
          numPy2Ras(read_data, rastername)
          clipRaster(rastername)
        elif kper > maxStrPer:
          endOfTime = True
          print ("EndofTime reached: SP={} KPER= {} > MaxSP = {}"\
              .format(strPerList,kper, maxStrPer))
    if endOfTime:
      return
  binfile.close()
  return

def readCBCterms():
#
#   Read CellxCell Budget terms to populate GUI selection list
#    
  binfilename=identBudFile()
  nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc()
  read_data=[]
  termlist=[]
  shape = (nrows,ncols)
  recLen= nrows*ncols
  shp3d = (nlays,nrows,ncols)
  reclen3d= nlays*nrows*ncols
  firstPer = 0
  iper = 0
  cbcHdr=binHdr['CBC']
  cbcUFHdr=binHdr['CBCUF']
  xcbcHdr=binHdr['XCBC']
  binfile=open(binfilename,'rb')
  if form == 'UF':
      cbcHdr=cbcUFHdr
  else:
      cbcHdr = cbcHdr
  while iper == firstPer:
      
    MFhdr1 = []
    MFhdr2 = []
    MFhdr1 = np.fromfile(binfile,cbcHdr,count=1,sep='')
#    print ("CDC Header>> {}".format(MFhdr1))
    if MFhdr1.size < 1:
#      print ("End of File Encountered")
      return(termlist)
    if firstPer == 0:
      firstPer = int(MFhdr1["KPER"][0])
    iper = int(MFhdr1["KPER"][0])

    budget = MFhdr1["TEXT"][0].strip().replace(" ","_")
    cbclays = int(MFhdr1["K"][0])
    if cbclays < 0 :
        # Compact Cell by cell flow file
        MFhdr2 = np.fromfile(binfile,
                     dtype=xcbcHdr,count=1)
        read_data = np.fromfile(binfile,np.int32,recLen).reshape(shape)
        read_data = np.fromfile(binfile,np.float32,recLen).reshape(shape)
    else:
        if form == 'UF':
          bor = np.fromfile(binfile,np.int32,count=1)
        read_data = np.fromfile(binfile,np.float32,
                                count=reclen3d).reshape(shp3d)
        if form == 'UF':
          eor = np.fromfile(binfile,np.int32,count=1)
    if iper == firstPer:
        termlist.append(budget)      
  binfile.close()
  return (termlist)

def readBinCBC(binfilename,rasType):
#
#   Reads the Modflow Binary CellxCell Budget file
#   as NumPy arrays for selected TERMS to be made into rasters
#
  
  def doFlowVec():
  #
  #  Flow Vectors require Special processing to produce ArcGIS
  #  features (points) which can be symbolized as arrows in ArcMap
  #	Arrow Symbology should be rotated 180 to account for
  #	Modflow sign conventions of flow budget terms.
  #
  #	IE: negative FLOW_RIGHT_FACE is actually flow into the eastern Face
  #	If you see negative FLOW_LOWER_FACE you have fertical flow going up.
  #
  #  The optional Resampling argument also produces features representing
  #  an aggregation of X cells by X cells.
  #
    global rFaceSlice
    fgdb = optArgs['geodb']
    if budget == 'FLOW_RIGHT_FACE':
      rFaceSlice = slice

    if budget == 'FLOW_FRONT_FACE':
      fFaceSlice = slice
      (magSlice, dirSlice) = magDirFunc(rFaceSlice, fFaceSlice)
      rasterdir = "LAY0"+str(ilayer+1)+"DIR_"+'{:7.5f}'\
            .format(((iper)/100000.0))
      rasterdir = rasterdir.replace("_0.","_")
      rastermag = rasterdir.replace("DIR_","MAG_")
      rasterdir = os.path.join(fgdb,rasterdir)
      rastermag = os.path.join(fgdb,rastermag)
      numPy2Ras(dirSlice, rasterdir)
      numPy2Ras(magSlice, rastermag)
      
      if modelClips[optArgs['model']] != (0,0,0,0):
        clipRaster(rasterdir)
        clipRaster(rastermag)

      if csizeMultiplier > 1:
        print ("Resampling rasters ...")
        rasDirResamp="LAY0"+str(ilayer+1)+"DIRX_"+'{:7.5f}'\
                 .format(((iper)/100000.0))
        rasDirResamp = rasDirResamp.replace("_0.","_")
        rasMagResamp = rasDirResamp.replace("DIRX_","MAGX_")
        rasMagResamp= os.path.join(fgdb,os.path.basename(rasMagResamp))
        rasDirResamp=os.path.join(fgdb,os.path.basename(rasDirResamp))
        arcpy.Resample_management(rasterdir, rasDirResamp,
                      cellsize, "BILINEAR")
        arcpy.Resample_management(rastermag, rasMagResamp,
                      cellsize, "BILINEAR")
        if modelClips[optArgs['model']] != (0,0,0,0):
          clipRaster(rasDirResamp)
          clipRaster(rasMagResamp)

        rastDirX = rasDirResamp
        arrowFeatureX =  os.path.join(fgdb,os.path.basename(rasDirResamp)+"arw")
        inMemFCX = os.path.join(fgdb,os.path.basename(arrowFeatureX))

        print (os.path.basename(arrowFeatureX))
        arcpy.RasterToPoint_conversion(in_raster=rastDirX,
                        out_point_features=arrowFeatureX,
                        raster_field="VALUE")

        inRasterListX = rasMagResamp+ " Magnitude"
        arcpy.gp.ExtractMultiValuesToPoints_sa(arrowFeatureX,
                            inRasterListX,"NONE")
        express = "!Magnitude! * "+str(csizeMultiplier)+\
              " * "+str(csizeMultiplier)
        arcpy.CalculateField_management(in_table=arrowFeatureX,
                        field="Magnitude",
                        expression=express,
                        expression_type="PYTHON_9.3",
                        code_block="#")

        if modelClips[optArgs['model']] != (0,0,0,0):
          arcpy.env.workspace = optArgs['clpgdb']
          inMemRasDirXclp = os.path.join(fgdb,os.path.basename(rasDirResamp))
          arwFeatXclp = arcpy.env.workspace +"\\clp"\
                    +os.path.basename(rasDirResamp)+"arw"
          print (os.path.basename(arwFeatXclp))
          arcpy.RasterToPoint_conversion(in_raster=inMemRasDirXclp,
                          out_point_features=arwFeatXclp,
                          raster_field="VALUE")
          inRasterListXclp = os.path.join(fgdb,os.path.basename(rasMagResamp)+\
                             ' Magnitude')
          arcpy.gp.ExtractMultiValuesToPoints_sa(arwFeatXclp,
                              inRasterListXclp,"NONE")
          arcpy.CalculateField_management(in_table=arwFeatXclp,
                          field="Magnitude",
                          expression=express,
                          expression_type="PYTHON_9.3",
                          code_block="#")
          arcpy.env.workspace = fgdb
      else:
        print ("No resampling")

        (dir, rastDir) = os.path.split(rasterdir)
        if 'clp' in rasterdir:
            arrowFeature = os.path.join(optArgs['clpgdb'],rastDir+"arw")
        else:
            arrowFeature = os.path.join(fgdb,rastDir +"arw")
        print ("Points for Flow Arrows: {}"\
            .format(os.path.basename(arrowFeature)))
        arcpy.RasterToPoint_conversion(in_raster=rasterdir,
                        out_point_features=arrowFeature,
                        raster_field="VALUE")
        MyField = "Magnitude"
        inRasterList = rastermag+ " " + MyField
        print ("Adding Magnitude to Flow Arrows")
        arcpy.gp.ExtractMultiValuesToPoints_sa(
            arrowFeature,inRasterList,"NONE")

        if modelClips[optArgs['model']] != (0,0,0,0):
          arcpy.env.workspace = optArgs['clpgdb']
          (currPath, baseFile) = os.path.split(rasterdir)
          rastDirclp = os.path.join(currPath,"clp"+baseFile)
          arrowFeatureclp = os.path.join(optArgs['clpgdb'],
                                         "clp"+baseFile+"arw")
          msg = "Clipped Points for Flow Arrows"
          print("{}: {}".format(msg,os.path.basename(arrowFeatureclp)))
          arcpy.RasterToPoint_conversion(in_raster=rastDirclp,
                          out_point_features=arrowFeatureclp,
                          raster_field="VALUE")
          arcpy.env.workspace = optArgs['clpgdb']
          MyField = "Magnitude"
          inRasterList = rastermag+ " " + MyField
          print ("Adding Magnitude to Flow Arrows")
          arcpy.gp.ExtractMultiValuesToPoints_sa(arrowFeatureclp,
                              inRasterList,"NONE")
    return

  if optArgs['terms']:
    termset = optArgs['terms']
    if termset == 'RIGHT|FRONT':
        termset = ['FLOW_RIGHT_FACE', 'FLOW_FRONT_FACE' ]
  getSpatialA()
  layerRange = optArgs['layerStr']
  strPerRange = optArgs['strStr']
  nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc()
  read_data=[]
  shape = (nrows,ncols)
  recLen= nrows*ncols
  shp3d = (nlays,nrows,ncols)
  reclen3d= nlays*nrows*ncols
  print("ThreeD shape and size is (l.r.c) {}*{}*{}={}").format(nlays,nrows,ncols,reclen3d)
    
  csizeMultiplier = int(optArgs['resample'])
  CsizeVal = csizeMultiplier * cellsz1
  cellsize = str(CsizeVal)
  
  cbcHdr=binHdr['CBC']
  cbcUFHdr=binHdr['CBCUF']
  xcbcHdr=binHdr['XCBC']

  layerList = parseRange(layerRange)
  strPerList = parseRange(strPerRange)
  if strPerList:
    maxStrPer =  max(strPerList)
  else:
    maxStrPer = 0

  print ("Binary Filename: {}".format(binfilename))
  binfile=open(binfilename,'rb')
  endOfTime = False
  for i in xrange(npers*15*5):
    #Check root to see if process should be terminated
    if not cmdLine:
      if i%5 == 0:
       root.update()
       print ("checking Button Status...Condition = {}".format(running))    
       if  not running:
         root.destroy()
         exit(7)
    MFhdr1 = []
    MFhdr2 = []

    if form != 'UF':
      MFhdr1 = np.fromfile(binfile,cbcHdr,
                           count=1,sep='')
    else:
      MFhdr1 = np.fromfile(binfile,cbcUFHdr,
                           count=1,sep='')
      
    if MFhdr1.size < 1:
      print ("End of File Encountered")
      return
    sys.stdout.write('.')
    print (MFhdr1["KSTP"][0],MFhdr1["KPER"][0],MFhdr1["TEXT"][0])
    
    kstp = int(MFhdr1["KSTP"][0])
    iper = int(MFhdr1["KPER"][0])
    budget = MFhdr1["TEXT"][0].strip().replace(" ","_")
    cbclays = int(MFhdr1["K"][0])

    if layerList:
      if cbclays < 0 :
        MFhdr2 = np.fromfile(file=binfile,
                     dtype=xcbcHdr,count=1,sep='')
        tottim = int(MFhdr2["TOTIM"][0])/100000.0
        read_data = np.fromfile(binfile,np.int32,recLen).reshape(shape)
        ilayer = read_data[1,1]
        print ("ilayer {}".format(ilayer))
        read_data = np.fromfile(binfile,np.float32,recLen).reshape(shape)
        rastername = budget+"_"+str(ilayer)+"_"+str(tottim)\
               .replace("0.","")
        if not strPerList or iper in strPerList:
          if ilayer in layerList:
            if rasType =='VEC' and budget in termset:
              doFlowVec()
            elif not optArgs['terms'] or optArgs['terms'] == 'ALL' or \
               budget in termset:
              print (budget, termset.upper())
              numPy2Ras(read_data, rastername)
              clipRaster(rastername)
          elif maxStrPer > 0 and iper > maxStrPer:
            endOfTime = True
            print ("EndOfTime in cbcBudgets")
            return
        if endOfTime:
          return
      else:
        if form == 'UF':
          print("Unusual for Modflow data to be read with this format {},{}".format(layerList, cbclays))
          bor = np.fromfile(binfile,np.int32, count=1)
        read_data=np.fromfile(binfile,np.float32,reclen3d).reshape(shp3d)
        for ilayer in range(nlays):
          slice = read_data[ilayer,:,:].reshape(shape)
#          rastername = budget + "_" + str(ilayer+1) + "_" + \
#                 '{:7.5f}'.format(((iper)/100000.0))
          rastername = budget + "_" + str(ilayer+1) + "_" + \
                 '{:7.5f}'.format(((iper)/100000.0)) + \
                 "_" + str(kstp)
#          print ("NEW...",rastername)
          rastername = rastername.replace("_0.","_")
          if not strPerList or iper in strPerList:
            if ilayer+1 in layerList:
              if rasType =='VEC' and budget in termset:
                doFlowVec()
              elif not optArgs['terms'] or optArgs['terms'] == 'ALL' or \
                budget in termset:
     #           print ("DEBUGING {} in {}".format(budget,termset))
                numPy2Ras(slice, rastername)
                clipRaster(rastername)
          elif maxStrPer > 0 and iper > maxStrPer:
            endOfTime = True
            return
        if endOfTime:
          return
  binfile.close()
  return
def setWorkspc(geodb):
#
#   Set base paths for Modflow namefile and ESRI workspace. 
#
  outputPath = r'H:\Documents\ArcGIS'
  if not os.path.exists(outputPath):
    os.makedirs(outputPath)
      
  if geodb == r'H:\Documents\ArcGIS\Default.gdb':
    print ("Default gdb path defined as:{}".format(outputPath))
    gdbfile = "Default.gdb"
  elif geodb != None:
    (temp_path, gdbfile) = os.path.split(geodb)
    outputPath = temp_path
    print ('Requested output path is: {}'.format(temp_path))
    print ('Geodb: {}'.format(gdbfile))
  else:
    print ("Unspecified working path.  Assigning: {}".format(path))
    outputPath =  path
    (outputPath, gdbfile) = os.path.split(outputPath)
    print ('output path: {}'.format(outputPath))
    print ('Geodb: {}'.format(gdbfile))

  workspace = os.path.join(outputPath, gdbfile)
  print ("Workspace has been defined as: {}".format(workspace))
  print ("does workspace exist:")

  if not arcpy.Exists(workspace):
    print ("Workspace does not exist.  Creating New one!")
    (temp_path, gdbfile) = os.path.split(workspace)
    if temp_path == "":
      temp_path = outputPath
    print (temp_path)
    print (gdbfile)
    arcpy.CreateFileGDB_management(temp_path, gdbfile)
    arcpy.env.workspace = os.path.join(temp_path, gdbfile)
  else:
    arcpy.env.workspace = workspace
  print ("output will be written to: {}".format(workspace))
  arcpy.env.overwriteOutput = True
  return workspace

def clearINMEM():
#
#   Clean up In_Memory Features, Tables and Rasters
#
  arcpy.env.workspace = r"IN_MEMORY"
  fcs = arcpy.ListFeatureClasses()
  tabs = arcpy.ListTables()
  rasters = arcpy.ListRasters()
  sys.stdout.flush()

  # for each FeatClass in the list of fcs's, delete it.
  for f in fcs:
    arcpy.Delete_management(f)
    print("Clearing IN_Memory Feature Classes: {}".format(f))
  # for each TableClass in the list of tab's, delete it.
  for t in tabs:
    arcpy.Delete_management(t)
    print("Clearing IN_Memory  Tables: {}".format(t))
  # for each raster, delete it.
  for r in rasters:
    arcpy.Delete_management(r)
    print("Clearing IN_Memory  Rasters: {}".format(r))
  return

def setDISfile():
#
#   Retrieve filename for Modflow Discretation file
#   searching for the Modflow Package Initials DIS in
#   the naemfile
#
  disFilename = getFileName(path + "\\" + namfile, 'DIS')
  disFilename_full = path + "\\" + disFilename
  
  """
  If DIS file doesn't exist from .NAM file
  construct info from BAS and BCF files
  """
  if disFilename.strip() == "":
    basFilename = getFileName(path + "\\" + namfile, 'BAS')
    basFilename_full = path + "\\" + basFilename
    df = []
    getBASdata(basFilename_full)
    bcfFilename = getFileName(path + "\\" + namfile, 'BCF')
    bcfFilename_full = path + "\\" + bcfFilename
    getBCFdata(bcfFilename_full)
    disdf = bcfdf
  else:
    df =[]
    getDISdata(disFilename_full)
  return 

def guiBin(justOptions):
#
#   GUI choices for Modflow Binary processing options
#
  boolStr=('_','X')  
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"
  intro_message = """
  ReadModflowBinary.py is command line driven
  or it can be ran with this GUI

  Choose binary options:"""
  preselected = 0
  while True:
    ##-- Really long assignment statement
    presented_choices = ["{0:<1} {1:<8} {2:<20}"\
                 .format(boolStr[optArgs[value[2]]],
                         label,' '.join(value[1].split()))
      for label, value in sorted(justOptions.iteritems())]
    ##-- End of Really long assignment statement

    reply = ez.choicebox(msg=intro_message,title=title,
               choices=presented_choices,preselect=preselected) 
    try:
      selected = reply.split(" ")
      optArgs[argHelp[selected[1]][2]] \
                = not optArgs[argHelp[selected[1]][2]]
    except:
    # reply.split(" ") throws exception when continue button selected
      TrueOptions = [k for k, v in \
          sorted(argHelp.iteritems()) if v[0] =='option' and
               optArgs[v[2]] and k not in ('uzf','gui')]
    if not reply:
      break
  return(TrueOptions)

def guiModel():
#
#   GUI selection of Model from available choices
#   if not provided on cmd line
#
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"

  while True:
    if not optArgs['model'] :
      modelMsg = """
      Please choose which Modflow model to process
      and identify the location and path of the name file"""
      for k, v in argHelp.iteritems():
        if v[2] == 'model':
          modelChoices =sorted(v[4])
      reply=ez.choicebox(msg=modelMsg,title=title,choices=modelChoices)
    else:
      break
    if reply:
        break
  try:
    selected = reply
    if reply:
      optArgs['model'] = selected
  except:
    pass
#  print ("{} Model selected".format(optArgs['model'])) 
  return (optArgs['model'])

def guiArgVals(justArgs):
#
#   GUI value definitions of
#   optional arguments such as:
#       lay, strPer, res, terms
#   arguments needing path or filenames excluded:
#       gdb, clpgdb, clpbox
#
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"

  intro_message = """
  ReadModflowBinary.py is command line driven
  or it can be ran with this GUI

  Provide arguments for these options:"""
  
  while True:
    ##-- Really long assignment statement      
    presented_choices =["{:<10} {:<15} {:>20} "\
                        .format(label,optArgs[value[2]],
                                ' '.join(value[1].split()) )
      for label, value in sorted(justArgs.iteritems())]
    ##-- End of Really long assignment statement
      
    reply = ez.choicebox(msg=intro_message,title=title,
              choices=presented_choices)
    try:
      selected = reply.split(" ")
      argValsMsg= "{}".format(argHelp[selected[0]][1])
      while True:
        reply = ez.enterbox(msg = argValsMsg)
        if reply:
            break
      if ('-'+selected[0]) in reply:
          reply = reply.strip('-'+selected[0])
      optArgs[argHelp[selected[0]][2]]= reply
    except:
      pass
      #print ("Multiple Argument definition complete")    
    if not reply:
      break
    
  NoneVals = [k for k, v in \
    sorted(argHelp.iteritems()) if v[0] !='option' and
        not optArgs[v[2]]
        and k not in('nam','mod','gdb','clpgdb','clpBox')]    
  return(NoneVals)

def guiMFterms(MFbudTerms):
  boolStr=('_','X')    
#
#   GUI choices for Modflow Binary processing options
#
  title ="Budget Term selection"
  intro_message = "Choose Modflow Binary CellxCell Budget Terms"

  preselected = 0
  while True:
    reply = ez.multchoicebox(msg=intro_message,
                             title=title,choices = MFbudTerms)
    if reply:
      break
  return(reply)

def guiGeoVals(spatialArgs):
#
#   GUI argument value definitions of
#   arguments needing path or filenames
#   for Spatial stuff like geodatabase or points:
#       gdb, clpgdb, clpbox
#
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"

  intro_message = """
  ReadModflowBinary.py is command line driven
  or it can be ran with this GUI

  Provide arguments for these options:"""
  while True:
    #--- Really long assignment statement      
    presented_choices =["{:<10} {:<15} {:>20} "\
                        .format(label,optArgs[value[2]],
                                ' '.join(value[1].split()) )
      for label, value in sorted(spatialArgs.iteritems())]
    #--- End of Really long assignment statement
    reply = ez.choicebox(msg=intro_message,title=title,
              choices=presented_choices)
    try:
      selected = reply.split(" ")
      print ("Select = {}".format(selected[0]))
      argValsMsg= "{}".format(argHelp[selected[0]][1])
      while True:
        dirName=ez.diropenbox(msg='Navigate to geodatabase directory',
                    title='ArcGIS Workspace',
                    default=os.path.dirname((optArgs['geodb'])))
        if dirName:
          break
      if not dirName:
        break
      if '.gdb' not in dirName:
        while True:
          gdbName = ez.enterbox(msg = 'geoDatabase Name for '+argValsMsg)
          if gdbName:
            if '.gdb' not in gdbName:
              gdbName = gdbName+'.gdb'
            break
      else:
        gdbName = ''
      optArgs[argHelp[selected[0]][2]]= os.path.join(dirName,gdbName)
#      print(selected[0],argHelp[selected[0]][2],
#            optArgs[argHelp[selected[0]][2]])
    except:
      print ("Multiple Argument definition complete")    
    if not reply:
      break
  DefaultVals = [k for k, v in \
    sorted(argHelp.iteritems()) if v[0] !='option' \
        and optArgs[v[2]] and ('Default' in optArgs[v[2]]
        or '0,0,0,0' in optArgs[v[2]])
                 and k in('gdb','clpgdb','clpBox')]    
  return(DefaultVals)

def guiArgs(argHelp):
#
#   Begin processing using GUI interface
#   when -gui option provided on Command Line
#
  justOptions ={k: v for k, v in \
        sorted(argHelp.iteritems()) if v[0] =='option'
        and k not in ('uzf')}
  justArgs ={k: v for k, v in argHelp.iteritems()
    if v[0] !='option'
        and k not in('nam','mod','gdb','clpgdb','clpBox')}
  spatialArgs={k: v for k, v in argHelp.iteritems()
             if v[0] !='option'
             and k in('gdb','clpgdb','clpBox')}
  
  #   select Binary data options
  
  TrueOptions = guiBin(justOptions)
  while not TrueOptions:
      TrueOptions =guiBin(justOptions)
  
  #  Choose from an existing model definition
  
  SelectedModel = guiModel()
  
 #  Identify Arguments which are still = None

  NoneVals = guiArgVals(justArgs)

  """
    If lay and/or strPer = None
    all layers or stress periods are processed

    Verify this is what the user wants
  """  
  for arg in NoneVals:
    if arg !='terms':
      text= "Undefined "+arg+"""
              ...  [Cancel] to provide value or range
              ...  [Continue] defaults to all
                  """
      if ez.ccbox(msg=text,title="Please Confirm"):
        pass
      else:
        oneDict={k: v for k, v in argHelp.iteritems()
             if v[0] !='option' and k ==arg}
        secondPass =guiArgVals(oneDict)
    else:
  #
  #   If terms = None all CellxCell budget term rasters will be
  #   produced for the layers and stressperiods defined
  #
      if 'terms' in NoneVals and 'bud' in TrueOptions:
          terms = readCBCterms()
          terms = guiMFterms(terms)
          optArgs['terms']= terms
  #
  #  Identify Arguments which are still = Default or 0,0,0,0
  #          
  DefaultVals = guiGeoVals(spatialArgs)
#  print (" GDB= {} ClipGDB = {}"\
#         .format(optArgs['geodb'],optArgs['clpgdb']))
  for arg in DefaultVals:
      text= "Default values for "+arg+"""
              ...  [Cancel] to provide value
              ...  [Continue] defaults to all
                  """
      if ez.ccbox(msg=text,title="Please Confirm"):
        pass
      else:
        oneDict={k: v for k, v in argHelp.iteritems()
             if v[0] !='option' and k ==arg}
        secondPass =guiGeoVals(oneDict) 
  return

def stopFn():
    """Stop scanning by setting the global flag to False."""
    global running
    running = False
    
def checkExec_env():
    cmdL = False
    a = sys.executable
    m = '\\'
    m = m[0]
    while True:
        b = len(a)
        c = a[(b - 1)]
        if c == m:
            break
        a = a[:(b - 1)]
    if sys.executable == a + 'python.exe':
        cmdL=True
    else:
        print sys.executable
        cmdL=False
    return (cmdL)

#--------------------------------------------------------------------
#
#          Let the processing Begin ... 
#
#--------------------------------------------------------------------
if __name__ == '__main__':
    cmdLine = checkExec_env()
    if cmdLine:
        print('Running in Command line')
  #      pool = multiprocessing.Pool()        
    else:
        print('Running in Python IDLE')
  #  platform = (None, 'mp')[cmdLine]
    
    global form
    global running
    running = True  # Global flag for Terminate Button
    
    form = 'BINARY'
    discDict ={}
    argHelp ={}
    modelOrigins = {
        'C4CDC' :arcpy.Point(763329.000, 437766.000),
        'ECFM'  :arcpy.Point(565465.000, -44448.000),
        'ECFT'  :arcpy.Point(330706.031,1146903.250),
        'ECFTX' :arcpy.Point( 24352.000, 983097.000),
        'LECSR' :arcpy.Point(680961.000, 318790.000),
        'LKBGWM':arcpy.Point(444435.531, 903882.063),
        'NPALM' :arcpy.Point(680961.000, 840454.000),
        'LWCFAS':arcpy.Point(438900.000, -80164.000),
        'LWCSAS':arcpy.Point(292353.000, 456228.000),
        'LWCSIM':arcpy.Point(218436.000, 441788.000),
        'WCFM'  :arcpy.Point( 20665.000, -44448.000)}
    
    model_SR = {
        'C4CDC':2881,'ECFM':2881,'ECFT':2881,'ECFTX':2881,
        'LECSR':2881,'NPALM':2881,'LKBGWM':2881,'LWCFAS':2881,
        'LWCSAS':2881,'LWCSIM':2881,'WCFM':2881}
    
    model_choices= [
        key for key,val in modelOrigins.iteritems()]
    
    modelClips ={
        'C4CDC':(0,0,0,0),
        'ECFM':(0,0,0,0),
        'ECFT':(0,0,0,0),
        'ECFTX':(0,0,0,0),
        'LECSR':(0,0,0,0),
        'NPALM':(0,0,0,0),
        'LKBGWM':(0,0,0,0),
        'LWCFAS':(0,0,0,0),
        'LWCSAS':(0,0,0,0),
        'LWCSIM':(0,0,0,0),
        'WCFM':(215080, 428340, 587064, 985667)}

    binHdr={
        'HEAD':np.dtype([
            ("KSTP",  "<i4"),
            ("KPER",  "<i4"),
            ("PERTIM", "<f4"),
            ("TOTIM",  "<f4"),
            ("TEXT",  "S16"),
            ("NC",   "<i4"),
            ("NR",   "<i4"),
            ("K",    "<i4")]),
        'CONC':np.dtype([
            ("KSTP",  "<i4"),
            ("KPER",  "<i4"),
            ("PERTIM", "<f4"),
            ("TOTIM",  "<f4"),
            ("TEXT",  "S16"),
            ("NC",   "<i4"),
            ("NR",   "<i4"),
            ("K",    "<i4")]),
        'CBC':np.dtype([
            ("KSTP",  "<i4"),
            ("KPER",  "<i4"),
            ("TEXT",  "S16"),
            ("NC",   "<i4"),
            ("NR",   "<i4"),
            ("K",    "<i4")]),
        'CBCUF':np.dtype([
            ("BOR",  "<i4"),
            ("KSTP",  "<i4"),
            ("KPER",  "<i4"),
            ("TEXT",  "S16"),
            ("NC",   "<i4"),
            ("NR",   "<i4"),
            ("K",    "<i4"),
            ("EOR",  "<i4")]),
        'XCBC':np.dtype([
            ("IMETH",  "<i4"),
            ("DELT",  "<f4"),
            ("PERTIM", "<f4"),
            ("TOTIM",  "<f4")])
        }

    parserArgs,argHelp = getArgsFromParser()
    """
      parserArgs is a Namespace and
      optArgs is a dictionary assigned to parserArgs
      which can be accessed in guiArgs and throughout the program
      
      parserArgs.model is == optArgs['model']
    """

    optArgs = vars(parserArgs)

    for k in optArgs.iteritems():
      label, value = k
      print ("{:<15} {:>6}".format(label, value))

    if not optArgs['namefile']:
      optArgs['gui'] = True
    #
    #   GUI to select Namefile if not provided on command line
    #        
      title ="Read Modflow Bianry Produces ArcGIS Rasters and Features"
      namMsg = """
      Please locate and select a Modflow name file
      which will properly identify the model results to process"""
      reply = None
      while True:
        if not optArgs['namefile']:
          ftypes = ["*.nam", ["*.txt","*.name","Non Standard Namefiles"]]
          reply = ez.fileopenbox(msg=namMsg,title=title,
                             default='*', filetypes=ftypes)
        else:
          break
        if reply:
          break
      if reply:
        optArgs['namefile'] = reply
      print ("{} has been selected as the Namefile for {} model."\
             .format(optArgs['namefile'],optArgs['model']))
    if optArgs['namefile']:
        (path, namfile) = os.path.split(optArgs['namefile'])
        if path == '':
          print ("""Explicit path missing.  
                Using default path for testing""")
          path = 'H:\\'
        setDISfile()
    else:
        print ("""Unable to process Binary data without file location
        details.
        nam/namfile argument is required:
            -nam NAMEFILE,
            --namfile=NAMEFILE  Read data from .NAM FILE""")
        exit()
        
    if optArgs['gui']:
    #
    #  GUI interface option selection
    #  "if not 'PROMPT' in os.environ" indicates
    #   double click from explorer
    #        
      guiArgs(argHelp)
    runString = r'C:\Python27\ArcGIS10.3\python.exe \\ad.sfwmd.gov\dfsroot\data\wsd\SUP\devel\source\Python\ReadModflowBinary\ReadModflowBinary.py'


    for arg,val in optArgs.iteritems():
        if val:
            for key, value in argHelp.iteritems():
                if value[2] == arg:
                    if value[2] == 'gui':
                        pass
                    elif len(value) < 4 :
                      runString += ' -'+key
                    elif value[2] == 'terms':
                      runString += ' -terms '
                      if type(val) is list or type(val) is tuple:
                          for trm in val:
                            Sval = '|'.join(map(str,val))
                          runString += '"'+Sval+'"'
                      else:
                          runString += '"'+val.strip('\'')+'"'
                    elif value[3] != val:
                      runString += ' -'+key + ' ' + str(val)
                        
    print ("""Command line execution string:
    {} 
    """.format(runString))
    if optArgs['model']:
      SRname= arcpy.SpatialReference(model_SR[optArgs['model']]).name
 #     print ("Assigned Spatial Reference: {}".format(SRname))
      
    if optArgs['geodb']:
      pass
    else:
      optArgs['geodb'] = r'H:\Documents\ArcGIS\Default.gdb'
    arcpy.env.workspace = setWorkspc(optArgs['geodb'])
    
    if optArgs['clpgdb']:
      print ("Clip Workspace = {}".format(optArgs['clpgdb']))
    else:
      optArgs['clpgdb']=optArgs['geodb']
      print ("No Clip Workspace defined...")
      print("Using Primary Workspace for Clipped Raster Storage")
      
    arcpy.env.workspace = setWorkspc(optArgs['clpgdb'])

    if optArgs['clipBox']:
    #
    #  Define Clipping Extents if needed
    #
      if not arcpy.Exists(optArgs['clipBox']):
        msg = "Did Not Find shapefile for Clip Extents:"
        print ("{} {}".format(msg,optArgs['clipBox']))
        if modelClips[optArgs['model']] == (0,0,0,0):
          print ("No clip extents")
        else:
          msg= "Default clip extents are"
          print("{}: {} for {}"\
                .format(msg,modelClips[optArgs['model']],
                        optArgs['model'] ))
      else:
        print ("{} has been found".format(optArgs['clipBox']))
    if optArgs['gui']:
      root = Tk()
      root["bg"] = "white"
      root.title("Click Button to Terminate App")
      root.geometry("250x40")
      app = Frame(root)
      message=Label(app,text="Terminate Button is not Immediate")
      message.pack()
      stop = Button(app, text="Terminate", bg="yellow",command=stopFn)
      stop.place(relx=.5,rely=.5,anchor=CENTER)
      stop.pack()
      app.pack()


      
    if optArgs['heads']:
    #
    #  Process binary Heads file:
    #        
      ocFilename = getFileName(os.path.join(path, namfile), 'OC')
      ocFilename_full = os.path.join(path, ocFilename)
      print ("Output Control filename: {}".format(ocFilename))

      if (optArgs['model'] in ['C4CDC','NPALM']):
        HeadsUnit = getUnitNum(ocFilename_full,1,3)
      else:
        HeadsUnit = getUnitNum(ocFilename_full,1,0)

      headsfile = getFileByNum(os.path.join(path,namfile),HeadsUnit)
      headsfile = os.path.join(path,headsfile)
      print ("heads binary filename: {}".format(headsfile))
      
      readBinHead(headsfile,'HEAD')

    if optArgs['zeta']:
    #
    #  Process SWI Zeta file:
    #        
      swiFilename = getFileName(os.path.join(path,namfile), 'SWI2')
      swiFilename_full = os.path.join(path,swiFilename)
      zetaUnit = getUnitNum(swiFilename_full,1,4)
      zetafilename = getFileByNum(os.path.join(path,namfile), zetaUnit)
      zetafilename = os.path.join(path,zetafilename)
      print ("....attempting to process zeta binary file")
      print (zetafilename)
      
      readBinHead(zetafilename,'HEAD')

    if optArgs['conc']:
    #
    #  Process binary TDS concentrations
    #
      concfile = os.path.join(path,'MT3D001.UCN')
      print ("....attempting to process MT3D binary file")
      if not os.path.exists(concfile):
        print ("Modflow Concentration file does not exist")
        exit(999)
        
      readBinHead(concfile,'CONC')


    if optArgs['uzfcbc']:
    #
    #  Process binary UZF CellxCell Budgets
    #
      uzfFilename = getFileName(os.path.join(path,namfile), 'UZF')
      uzfFilename_full = os.path.join(path,uzfFilename)
      uzfUnit = getUnitNum(uzfFilename_full,1,6)
      uzfcbcfilename = getFileByNum(os.path.join(path,namfile), uzfUnit)
      uzfcbcfilename = os.path.join(path,uzfcbcfilename)
      print ("CellxCell Flow filename: {}".format(uzfcbcfilename))

      readBinCBC(uzfcbcfilename,None)

    if optArgs['cbc']:
    #
    #  Setup and process binary LPF Cell by cell Budgets:
    #
      cbcfilename=identBudFile()
      readBinCBC(cbcfilename,None)

    if optArgs['vector']:
    #
    #  Setup and process binary LPF CellbyCell and Create Flow Vectors:
    #
      cbcfilename=identBudFile()
      if optArgs['terms'] != 'RIGHT|FRONT':
        optArgs['terms'] = 'RIGHT|FRONT'
        print ("""Overriding terms option for flow vectors: 
           required terms are -- 'RIGHT|FRONT' 
           indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE """)
      readBinCBC(cbcfilename,'VEC')

    clearINMEM()
    if not cmdLine:
      root.destroy()
    arcpy.CheckInExtension("Spatial")
    print ("...finished")

