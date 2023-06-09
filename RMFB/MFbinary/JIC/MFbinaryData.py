"""
..module::MFbinaryData
  ::synopsis: Read Modflow Binary and setup_guiStuff.py uses:
  :           import MFbinary.MFbinaryData as mf function definitions
  :           specifically reading and manipulating Modflow input and
  :           output files
  ::created: 10-23-2019
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>
  ::modified: readBinCBC - added units multiplier
  ::modified: magDirFunc - corrected bug with flow vectors, providing corrected orientaton
  ::modified: readBinHead - use strPerList and seek to next stress period

"""
import numpy as np
import pandas as pd
import os
import sys
from sys import exit
if sys.version_info[0] == 3:
    # for Python3
    from tkinter import *   ## notice lowercase 't' in tkinter here
    from tkinter import Tk   ## notice lowercase 't' in tkinter here
else:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter

import RMB.MFgis.MFgis as MFgis
try:
    from osgeo import gdal #, gdalconst, osr, ogr
except ImportError:
    print("""GDAL libraries are not available.
          Attempting to continue with AcrGIS libraries)""")
    import arcpy as arcpy

global form

form = 'BINARY'

def noPath (file):
    return(os.path.basename(file))

def binHdr(hdrType):
    AllBinHdr={'HEAD':np.dtype([("KSTP","<i4"),("KPER","<i4"),("PERTIM","<f4"),
                                ("TOTIM","<f4"),("TEXT","S16"),("NC","<i4"),
                                ("NR","<i4"),("K","<i4")]),
               'CONC':np.dtype([("KSTP","<i4"),("KPER","<i4"),("PERTIM","<f4"),
                                ("TOTIM","<f4"),("TEXT","S16"),("NC","<i4"),
                                ("NR","<i4"),("K","<i4")]),
               'CBC':np.dtype([("KSTP","<i4"),("KPER","<i4"),("TEXT","S16"),
                               ("NC","<i4"),("NR","<i4"),("K","<i4")]),
               'CBCUF':np.dtype([("BOR","<i4"),
                                 ("KSTP","<i4"),("KPER","<i4"),("TEXT","S16"),
                                 ("NC","<i4"),("NR","<i4"),("K","<i4"),
                                 ("EOR","<i4")]),
               'XCBC':np.dtype([("IMETH","<i4"),("DELT","<f4"),("PERTIM","<f4"),
                                ("TOTIM","<f4")])}
    return(AllBinHdr[hdrType])

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
        #print (sys.executable)
        cmdL=False
    return (cmdL)

def stopFn():
    """Stop scanning by setting the global flag to False."""
    global running
    running = False

global makeTerminateBtn
def makeTerminateBtn():
    global root
    global running
    root = Tk()
    root["bg"] = "white"
    root.title("Click Button to Terminate App")
    root.geometry("250x40")
    app = Frame(root)
    message=Label(app,text="Termination will follow export of current Raster")
    message.pack()
    stop = Button(app, text="Terminate", bg="yellow",command=stopFn)
    stop.place(relx=.5,rely=.5,anchor=CENTER)
    stop.pack()
    app.pack()
    running = True  # Global flag for Terminate Button
    return

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

def FileByInitials(sourcefile,pkgInitials):
#
#   Read Modflow Namefile searching for package initials
#   and return associated filename
#
  binlist=[]
  header = ['Initials', 'unitnum', 'filename', 'status']
  binlist.append(header)
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

def getUnitNum(file, row_num, item_num):
#
#    Open & read Modflow Output Control file assign each line read to row[].
#    Parse selected row_num and assign parsed item_num to unitnum.
#
#    If item_num == 0 use last item in the row
#
  row=[]
  try:
    f = open(file,'r')
  except IOError:
    print ('IO Error:',IOError)
    print('opening',file)
  else:
    with f:
      for line in f.readlines(1000):
      #  print(line)
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

def getSP_OC(file, spMax, nlays):
#
#    Open & read Modflow Output Control file assign each line read to row[].
#    Parse data and retuen list of Stress Periods identified as possible output periods.
#
  row=[]
  OCsp =[]
  try:
    f = open(file,'r')
  except IOError:
    print ('IO Error:',IOError)
    print('opening',file)
  else:
    with f:
      lnum = 1
      line=''
      while line.startswith('#'):
        line = f.readline()
        lnum = lnum + 1
      data = pd.read_table(file, skiprows=lnum, header=None, delim_whitespace=True)   
      # print("""
      #       Reading {} 
      #       To identify CellXCell output stress periods
      #       spMax ={}""".format( file,spMax))
      dataF=data.iloc[0:spMax*(nlays+1):nlays+1,]
# Works ok if everyone format OC like I do
#      OCsp= dataF.loc[(dataF[3]==5),[5]]  
   # but not everyone is like me   
#      dataF: column [3] as 4th column indicates:
#        no-output=0, output =1, sum=4, or sum-and-output=5
      TorF = (dataF[3]==5).tolist()
      nums = list(range(1,spMax+1))
     # print(nums)
      OCsp=[i for idx, i in enumerate(nums) if TorF[idx]]
      if (len(OCsp)<1):
          OCsp = nums
      #print(OCsp)
  return OCsp
      
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
      if len(line.strip())> 0:
        if not line.startswith('#'):
          binlist.append(line.split()[0:4])
        #  print(line.split()[0:4])
  f.close()
  pd.set_option("display.max_rows", None)
  pd.set_option("display.max_columns", None)

  df = pd.DataFrame(binlist, columns = header)
  df= df[1:]
  # KEVIN Check here
  #df['unitnum'] = df.unitnum.astype(str).astype('int')
  df['unitnum'] = pd.to_numeric(df['unitnum'])
  fnumber = int(fnumber)
  #df.astype({'unitnum': 'int'}).dtypes

 # print(fnumber)
  if fnumber not in df.unitnum.values:
      print( ':::Unit number ',fnumber,type(fnumber),' Not found in',df.unitnum.values)
      print(df.unitnum)
      print("If using -tds option it's likely no TDS was output")
      exit(99)
 
 # newdf = df.loc[df['unitnum'] == str(fnumber)]
  newdf = df.loc[df['unitnum'] == fnumber]
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
#   Read Modflow BCF whenever DIS file is not available
#   to populate the discretization dictionary: discDict
#
  global discDict
  row=[]
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
  with open(file, 'r') as f:
    for line in f.readlines(1024):
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
  return (discDict)

def setDISfile(path, namfile):
#
#   Retrieve filename for Modflow Discretation file
#   searching for the Modflow Package Initials DIS in
#   the naemfile
#
  disFilename = FileByInitials(path + "\\" + namfile, 'DIS')
  disFilename_full = path + "\\" + disFilename

  """
  If DIS file doesn't exist from .NAM file
  construct info from BAS and BCF files
  """
  if disFilename.strip() == "":
    print("no DIS file")
    basFilename = FileByInitials(path + "\\" + namfile, 'BAS')
    basFilename_full = path + "\\" + basFilename
    getBASdata(basFilename_full)
    bcfFilename = FileByInitials(path + "\\" + namfile, 'BCF')
    bcfFilename_full = path + "\\" + bcfFilename
    getBCFdata(bcfFilename_full)
  else:
    discDict = getDISdata(disFilename_full)
  return (discDict)

def modelDisc():
#
#   Deconstruct the discDit returning
#   Modflow layer, row, column,stress periods and cell sizes
#
  global discDict
  nlays = int(discDict['layer'])
  nrows = int(discDict['nrows'])
  ncols = int(discDict['ncols'])
  npers = int(discDict['nperiod'])
  cellsz1 = float(discDict['cellsize1'])
  cellsz2 = float(discDict['cellsize2'])
  #print('DIS file says npers = ',npers)
  return nlays,nrows,ncols,npers,cellsz1,cellsz2

def identBudFile(path,namfile):
#
#   Determine the filename for the CellxCell budget file
#   based on Namefile Package Initials
#
  cbcPkgFilename = FileByInitials(os.path.join(path,namfile), 'LPF')
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = FileByInitials(os.path.join(path,namfile), 'BCF6')
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = FileByInitials(os.path.join(path,namfile), 'BCF')
    # BCF uses the older 'UNFORMATTED' FORTRAN binary output
  if cbcPkgFilename.strip() == "":
    cbcPkgFilename = FileByInitials(os.path.join(path,namfile), 'UPW')
  if cbcPkgFilename.strip() == "":
    print(" No supported flow Packages (BCF,BCF6,LPF or UPW) found in NAM file")
    exit(86)
  cbcPkgFullName = os.path.join(path,cbcPkgFilename)
  # print(cbcPkgFullName)

  cbcUnit = getUnitNum(cbcPkgFullName,1,1)

  if int(cbcUnit) == 0:
    cbcUnit = getUnitNum(cbcPkgFullName,1,2)
  cbcFilename = getFileByNum(os.path.join(path,namfile), cbcUnit)
  binfilename = os.path.join(path,cbcFilename)
  #print ("CellxCell Flow filename {} on unit {}".format(binfilename,cbcUnit))
  return(binfilename)

def readBinHead(binfilename,binType,optArgs):

#   Read Modflow 2D Binary file such as the HEADS and CONC
#       Each non-Header Record is a layer
#           read as a 2D NumPy array (nrows,ncols)
#
# KAR-2022-05  Recent modification has code seek between stress periods to next required.
  RED     = "\033[1;31m"  
  BLUE    = "\033[1;34m"
  RESET   = "\033[0;0m"    
  if optArgs['gui']:
      makeTerminateBtn()

  global running
  running = True  # Global flag for Terminate Button

  layerRange = optArgs['layerStr']
  strPerRange = optArgs['strStr']
  dataRead=[]
  nlays,nrows,ncols,npers,cellsz1,cellsz2=modelDisc()
  ws1 = optArgs['geodb']

  Hdr=binHdr(binType)
  knt= int(nrows)*int(ncols)
  shape = (nrows,ncols)
  if layerRange: layerList = parseRange(layerRange)
  else: layerList = parseRange('1-'+str(nlays))
  if strPerRange:
      strPerList = parseRange(strPerRange)
      maxStrPer =  max(strPerList)
  else:
      strPerList = None
      maxStrPer = npers + 1
  try:
      binfile=open(binfilename,'rb')
  except:
      print(RED,"binary heads file {} does not exist".format(binfilename),RESET)
      exit(86)
  endOfTime = False

  # try:
  #     perRange = xrange(int(npers*nlays))   # for Python 2.7
  # except:
  #     perRange = range(int(npers*nlays))    # for Python 3.6
  if strPerList: kper = min(strPerList)
  else: 
      strPerList=[]
      print(RED,'No Stress Periods selected for processing!',RESET)
      kper = 0
  #kper = 0.0
  k=min(layerList)
  for SPval in strPerList:
      
    #Check root to see if process should be terminated
   if optArgs['gui']:
       root.update()
       if not running:
         root.destroy()
         exit(7)
   MFhdr  = []
   seek2 = (SPval-1)*nlays*(44+(knt*4))
   if (k<=min(layerList) or binfile.tell() <= seek2) :
      if not optArgs['quiet']:print('Seeking...',SPval,seek2)
      fpAt=binfile.seek(seek2,0)
   for doLay in parseRange('1-'+str(nlays)): 
    #print("Doing layer:",doLay,MFhdr)      
    MFhdr  = np.fromfile(binfile,Hdr,count=1,sep='')
    if not MFhdr:
        print(binfilename)
#        root.destroy()
        exit(99)
    kper   = MFhdr['KPER'][0]
    totim  = MFhdr['TOTIM'][0]
    k      = MFhdr['K'][0]
    #print(MFhdr)

    heads = MFhdr["TEXT"][0].strip().replace(b" ",b"_").decode("utf-8")
        
    dataRead = np.fromfile(file=binfile, dtype=np.float32,
                count=knt, sep='').reshape(shape)

    if binType == 'CONC':
        kper = int(totim)
      #  TDS values stored as kg/m^3 multiply by 1000 for mg/L
      #  dataRead = dataRead * 1000.0  
    # build rastername string
    rastername = binType + '{:7.5f}'.format(((kper)/100000.0))+"_"+str(k)
    rastername = rastername.replace("0.","_")
    rastername = os.path.join(ws1,rastername)

    if layerList != [0] or strPerList != [0]:
      if k in layerList:
        if not strPerList or kper in strPerList:
         # if optArgs['quiet']: print('')
         #  print(min(dataRead))
         #
         #  set dataRead min vals that are extremely small to a somewhat small number
          dataRead[np.isnan(dataRead)]= -998
          dataRead[dataRead< -999] = -999
          MFgis.numPy2Ras(dataRead, rastername,optArgs,discDict)
          MFgis.clipRaster(rastername, optArgs)
        elif kper % 100 == 0 and k ==1: 
              if optArgs['gui']: print ('Scan past Stress Period=',kper,'Tot Time',totim,'lay=',k,heads)                     
        elif kper > maxStrPer:
          print("EndOfTime", kper, maxStrPer)
          endOfTime = True
          if not optArgs['quiet']:
              if optArgs['gui']: print ("EndofTime reached: SP={} KPER= {} > MaxSP = {}"\
              .format(strPerList,kper, maxStrPer))
       
    if endOfTime:
      if optArgs['gui']: root.destroy()
      return
  binfile.close()
  if optArgs['gui']: root.destroy()
  return

def readCBCterms(path,namfile,optArgs):
#
#   Read CellxCell Budget terms to populate GUI selection list
#
  binfilename=identBudFile(path,namfile)
  nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc()
  dataRead=[]
  termlist=[]
  shape = (nrows,ncols)
  recLen= nrows*ncols
  global CBCbytesPer
  CBCbytesPer=0
  shp3d = (nlays,nrows,ncols)
  reclen3d= nlays*nrows*ncols
  firstPer = 0
  iper = 0
  cbcHdr=binHdr('CBC')
  cbcUFHdr=binHdr('CBCUF')
  xcbcHdr=binHdr('XCBC')
  binfile=open(binfilename,'rb')
  if form == 'UF':
      cbcHdr=cbcUFHdr
  else:
      cbcHdr = cbcHdr
  if not optArgs['quiet']: print('Budget terms discovered in binary file:')

  while iper == firstPer:
    MFhdr1 = []
    MFhdr2 = []
    MFhdr1 = np.fromfile(binfile,cbcHdr,count=1,sep='')
    if MFhdr1.size < 1:
      print ("End of File Encountered")
      return(termlist)
    if firstPer == 0:
      firstPer = int(MFhdr1["KPER"][0])
    iper = int(MFhdr1["KPER"][0])
    try:
        budget = MFhdr1["TEXT"][0].strip().replace(b" ",b"_").decode("utf-8")
    except:
        print('CBC Budget output file format is inconsistent with data expected' )   
        if optArgs['gui']: root.destroy()
        exit(1313)
    if not optArgs['quiet']: print("{} {}".format(iper,budget))
    
    cbclays = int(MFhdr1["K"][0])
    if cbclays < 0 :
        # Compact Cell by cell flow file
        MFhdr2 = np.fromfile(binfile,
                     dtype=xcbcHdr,count=1)
        dataRead = np.fromfile(binfile,np.int32,recLen).reshape(shape)
        dataRead = np.fromfile(binfile,np.float32,recLen).reshape(shape)
    else:
        if form == 'UF':
          bor = np.fromfile(binfile,np.int32,count=1) # read dummy variable as begining of record
        dataRead = np.fromfile(binfile,np.float32,
                                count=reclen3d).reshape(shp3d)
        if form == 'UF':
          eor = np.fromfile(binfile,np.int32,count=1) # read dummy variable as end of record
  #  dataRead[dataRead== -1000000e+030] = -999.9999
          
    if iper == firstPer:
        termlist.append(budget)
        CBCbytesPer=binfile.tell()
  binfile.close()
  return (termlist)

def magDirFunc(rFaceSlice, fFaceSlice):
#
#   x = np.array([-1, +1, +1, -1])     x represents Right Face (negative flow is to the East)    
#   y = np.array([-1, -1, +1, +1])     y represents Front Face (negative flow is to the South)
#   tmpdirArray=np.arctan2(y, x) * 180 / np.pi
#   tmpdirArray([-135.,  -45.,   45.,  135.])    compass directions [SE,SW,NW,NE]  where 0 degrees represent due West
#  Negative results for degrees are adjusted to range from 180 thru 360
#   dirArray = np.where(tmpdirArray > 0.0,tmpdirArray,(tmpdirArray+360.0))   
#   dirArray ([225, 315, 45, 135])
#
# Symbology in ArcMap should have template arrow pointing East 
#    with Advanced Symbology options type set for Dir as Geographic 
#
  tmpdirArray = np.arctan2(fFaceSlice,rFaceSlice)*180 / np.pi
  dirArray = np.where(tmpdirArray > 0.0,tmpdirArray,(tmpdirArray+360.0))
  magArray = np.power((np.power(fFaceSlice,2)+np.power(rFaceSlice,2)),.5)

  return magArray, dirArray

def readBinCBC(binfilename,rasType,optArgs,OCsp):
  form = 'BINARY'
  cmdLine=checkExec_env()

  if optArgs['gui']: makeTerminateBtn()
#
#   Reads the Modflow Binary CellxCell Budget file
#   as NumPy arrays for selected TERMS to be made into rasters
#
# KAR-2022-05  Recent modification has code seek between stress periods to next required.
#
  def doFlowVec(rFaceSlice):
  #  Processes 2 budget Terms: 'FLOW_RIGHT_FACE' and 'FLOW_FRONT_FACE' to
  #  produce features (points) which can be symbolized as arrows in ArcMap
  #	ArcMap Template Arrow Symbol needs to be rotated to point East with Geographic rotation
  #
  #	negative FLOW_RIGHT_FACE is flow to the East
  #
  # The optional Resampling argument produces features representing an average of X by X cells.
  #
    import numpy as np
    if not optArgs['noArc']: outDir = optArgs['geodb']
    if not optArgs['noArc']: outDirClp = optArgs['clpgdb']
    if  optArgs['noArc']: outDir = optArgs['rasFolder']
    if  optArgs['noArc']: outDirClp = optArgs['rasFolder']


    if budget == 'FLOW_FRONT_FACE':
      fFaceSlice = slice
      (magArray, dirArray) = magDirFunc(rFaceSlice, fFaceSlice)

      if  optArgs['noArc']: print ("Raster & Shapefile output location: {}".format(outDir))
      if  not optArgs['noArc']: print ("Raster & Feature Class output location: {} \nClipped: {}".format(outDir,outDirClp))

      rasDir = "LAY0"+str(ilayer+1)+"DIR_"+'{:7.5f}'.format(((iper)/100000.0))
      rasDir = rasDir.replace("_0.","_")
      rasMag = rasDir.replace("DIR_","MAG_")

      rasDirX= rasDir.replace("DIR_","DIRX_")
      rasMagX= rasMag.replace("MAG_","MAGX_")

      MFgis.numPy2Ras(dirArray, rasDir, optArgs, discDict)
      MFgis.numPy2Ras(magArray, rasMag, optArgs, discDict)


      rasDirFile     = os.path.join(outDir,rasDir)
      rasMagFile     = os.path.join(outDir,rasMag)

      arwFeat        = os.path.join(outDir,rasDir+'arw')
      rasDirXFile    = os.path.join(outDir,rasDirX)
      rasMagXFile    = os.path.join(outDir,rasMagX)
      arwFeatX       = os.path.join(outDir,rasDirX+"arw")
      clprasDirFile  = os.path.join(outDirClp,'clp'+rasDir)
      clprasMagFile  = os.path.join(outDirClp,'clp'+rasMag)
      clparwFeat     = os.path.join(outDirClp,'clp'+rasDir+'arw')
      clprasDirXFile = os.path.join(outDirClp,'clp'+rasDirX)
      clprasMagXFile = os.path.join(outDirClp,'clp'+rasMagX)
      clparwFeatX    = os.path.join(outDirClp,'clp'+rasDirX+'arw')

      print("{} \t:Points for Flow Arrows".format(noPath(arwFeat)))
      MFgis.TwoRas2OnePnt(rasDirFile,rasMagFile,arwFeat,optArgs,
                          "VALUE","Magnitude",1)

      if MFgis.modelClips(optArgs['model']) != (0,0,0,0):
        MFgis.clipRaster(rasDir, optArgs)
        MFgis.clipRaster(rasMag, optArgs)
        print("{} \t:Clipped Points for Flow Arrows".format(noPath(clparwFeat)))
        MFgis.TwoRas2OnePnt(clprasDirFile,clprasMagFile,clparwFeat,optArgs,
                            "VALUE","Magnitude",1)

      if csizeMultiplier > 1:
        rasFFMag= rasDir.replace("DIR_","FFMAG_")
        rasRFMag= rasDir.replace("DIR_","RFMAG_")
        rasFFMagX= rasDir.replace("DIR_","FFMAGX_")
        rasRFMagX= rasDir.replace("DIR_","RFMAGX_")

        rasFFMagFile   = os.path.join(outDir,rasFFMag)
        rasRFMagFile   = os.path.join(outDir,rasRFMag)   
        rasFFMagXFile   = os.path.join(outDir,rasFFMagX)
        rasRFMagXFile   = os.path.join(outDir,rasRFMagX)     
        
        MFgis.numPy2Ras(fFaceSlice, rasFFMag, optArgs, discDict)
        MFgis.numPy2Ras(rFaceSlice, rasRFMag, optArgs, discDict)        
        print("{} \t:Resampled Raster".format(noPath(rasDirXFile)))
        print("{} \t:Resampled Raster".format(noPath(rasMagXFile)))
        if  optArgs['noArc']:
          #  Look into using  reshape and sum with numpy to resample
          #    a_small = a.reshape(2160, 2, 4320, 2).sum(axis=(1, 3))
           gdal.Warp(rasFFMagXFile+'.tif', rasFFMagFile+'.tif',
                     outputType=gdal.GDT_Float32,xRes=cellsize, yRes=cellsize, 
                     resampleAlg = gdal.GRA_Average)
           gdal.Warp(rasRFMagXFile+'.tif', rasRFMagFile+'.tif',
                     outputType=gdal.GDT_Float32,xRes=cellsize, yRes=cellsize,
                     resampleAlg = gdal.GRA_Average)
           fFXras = MFgis.rasFile2array(rasFFMagXFile+'.tif')
           rFXras = MFgis.rasFile2array(rasRFMagXFile+'.tif')
           (magArray, dirArray) = magDirFunc(rFXras, fFXras)
           MFgis.numPy2Ras(dirArray, rasDirX, optArgs, discDict)
           MFgis.numPy2Ras(magArray, rasMagX, optArgs, discDict)           
        else:
          # Look into chaging Resample_management to aggregate
          # arcpy.gp.Aggregate_sa(rasMag, rasMagX, csizeMultiplier, "SUM", "EXPAND", "DATA")

          arcpy.Resample_management(rasFFMag, rasFFMagX, cellsize, "BILINEAR")
          arcpy.Resample_management(rasRFMag, rasRFMagX, cellsize, "BILINEAR")
          fFXras = arcpy.RasterToNumPyArray(rasFFMagX,nodata_to_value=0)
          rFXras = arcpy.RasterToNumPyArray(rasRFMagX,nodata_to_value=0)
          (magArray, dirArray) = magDirFunc(rFXras, fFXras)
          MFgis.numPy2Ras(dirArray, rasDirX, optArgs, discDict)
          MFgis.numPy2Ras(magArray, rasMagX, optArgs, discDict)     

        print("{} \t:Points for Resampled Flow Arrows".format(noPath(arwFeatX)))
        #  MFgis.TwoRas2OnePnt will need to be editted to remove multiplier
        #  if method is practical
        MFgis.TwoRas2OnePnt(rasDirXFile,rasMagXFile,arwFeatX,optArgs,
                              "VALUE","Magnitude",csizeMultiplier)

        if MFgis.modelClips(optArgs['model']) != (0,0,0,0):
          MFgis.clipRaster(rasDirX, optArgs)
          MFgis.clipRaster(rasMagX, optArgs)
          print("{} \t:Clipped Points for Resampled Flow Arrows".format(noPath(clparwFeatX)))
          MFgis.TwoRas2OnePnt(clprasDirXFile,clprasMagXFile,clparwFeatX,optArgs,
                              "VALUE","Magnitude",csizeMultiplier)
    return

  if optArgs['terms']:
    termset = optArgs['terms']
    if termset == 'RIGHT|FRONT': termset = ['FLOW_RIGHT_FACE', 'FLOW_FRONT_FACE' ]
    if termset == 'FACE': termset = ['FLOW_RIGHT_FACE', 'FLOW_FRONT_FACE', 'FLOW_LOWER_FACE' ]
    if termset == 'WELL': termset = ['WELLS' ]
  layerRange = optArgs['layerStr']
  strPerRange = optArgs['strStr']
  nlays,nrows,ncols,npers,cellsz1,cellsz1= modelDisc()
  dataRead=[]
  shape = (nrows,ncols)
  recLen= nrows*ncols
  shp3d = (nlays,nrows,ncols)
  reclen3d= nlays*nrows*ncols
  if not optArgs['quiet']: 
      print("ThreeD shape and size is (l.r.c) {0}*{1}*{2}={3}".format(nlays,nrows,ncols,reclen3d))

  csizeMultiplier = int(optArgs['resample'])
  CsizeVal = csizeMultiplier * cellsz1
  cellsize = str(CsizeVal)
  if (optArgs['units'] == 'cfd'): rasMulti = 1.0
  if (optArgs['units'] == 'mgd'): rasMulti = 7.480519/1000000.0

  intervalTxt = MFgis.modelStrPeriodInterval(optArgs['model'])
  interval = 1.0
  if intervalTxt == 'Monthly': interval = 30.4
  if (optArgs['units'] == 'inPerSP'): rasMulti = (interval*12.0)/(cellsz1*cellsz1)
  if (optArgs['units'] == 'inPerDay'): rasMulti = (12.0)/(cellsz1*cellsz1)
  if (optArgs['units'] == 'inPerYr'): rasMulti = (365*12.0)/(cellsz1*cellsz1)
  cbcHdr=binHdr('CBC')
  xcbcHdr=binHdr('XCBC')

  if layerRange: layerList = parseRange(layerRange)
  else: layerList = parseRange('1-'+str(nlays))
  strPerList = parseRange(strPerRange)
  if strPerList: maxStrPer =  max(strPerList)
  else: 
      maxStrPer = npers
      strPerList = parseRange('1-'+str(npers))
  

  print ("Processing Cell by Cell Budget Binary Filename: {}".format(binfilename))
  binfile=open(binfilename,'rb')
     
  if optArgs['quiet']: print('')
      
  i = 0
  toDoList = list(filter(lambda SP: SP <=max(strPerList), OCsp))
  for wantedSP in strPerList:
    try:
      indx = toDoList.index(wantedSP) 
    # Seek to stress period
    # Even if the pointer is already there
    # Since last loop would have Read the STORAGE MFhdr last stress period
    # and now requires pointer to back the file up a step
      seek2 = (indx)*CBCbytesPer
      i = i + 1  
      if not optArgs['quiet']: print('Seeking...',wantedSP)
      fpAt=binfile.seek(seek2,0)
    #Check root to see if process should be terminated
      if optArgs['gui']:
         if i%5 == 0:
          root.update()
          if not optArgs['quiet']:
              print ("checking Button Status...Condition = {}".format(running))
          else:
              pass
              #print(".",end='')
          if not running:
            root.destroy()
            exit(7)
            
      iper = wantedSP
      kstp = 0
      while iper == wantedSP:  
                      
          MFhdr1 = []
          MFhdr2 = []
        
          MFhdr1 = np.fromfile(binfile,cbcHdr, count=1,sep='')
    
          if MFhdr1.size < 1:
            RED     = "\033[1;31m"  
            RESET   = "\033[0;0m"

            print (RED,"End of File Encountered",RESET)
            if optArgs['gui']: root.destroy()
            return
    
          kstp = int(MFhdr1["KSTP"][0])
          iper = int(MFhdr1["KPER"][0])
          try:
              budget = MFhdr1["TEXT"][0].strip().replace(b" ",b"_").decode("utf-8")
          except:
               print('CBC Budget output file format is inconsistent with data expected' )   
               if optArgs['gui']: root.destroy()
               exit(1313)   

          # if not optArgs['quiet']:
          #      print("{} {} {}".format(kstp,iper,budget))
          # elif budget == 'STORAGE': 
          #      pass
    
          cbclays = int(MFhdr1["K"][0])
          if layerList:
             if cbclays < 0 :  # Compressed Binary
               MFhdr2 = np.fromfile(file=binfile,dtype=xcbcHdr,count=1,sep='')
               tottim = int(MFhdr2["TOTIM"][0])/100000.0
               dataRead = np.fromfile(binfile,np.int32,recLen).reshape(shape)
               ilayer = dataRead[1,1]
               dataRead = np.fromfile(binfile,np.float32,recLen).reshape(shape)
               #dataRead[dataRead== -1000000e+030] = -999.9999
              # print(np.min(dataRead))
    
               if budget == 'FLOW_RIGHT_FACE': rFaceSlices=dataRead
               #rastername = budget+"_"+str(ilayer)+"_"+str(tottim).replace("0.","")
               rastername = budget + "_" + str(ilayer+1) + "_" + \
                        '{:7.5f}'.format(((iper)/100000.0)) +  "_" + str(kstp)
               rastername = rastername.replace("_0.","_")
               if not strPerList or iper in strPerList:
                 if ilayer in layerList:
                   if rasType =='VEC' and budget =='FLOW_FRONT_FACE':
                     rFaceSlice = rFaceSlices[ilayer,:,:].reshape(shape)
                     doFlowVec(rFaceSlice)
                   elif rasType =='VEC' and budget == 'FLOW_RIGHT_FACE':
                         pass
                   elif not optArgs['terms'] or optArgs['terms'] == 'ALL' or budget in termset:
                     MFgis.numPy2Ras(dataRead, rastername, optArgs,discDict,rasMulti)
                     MFgis.clipRaster(rastername, optArgs)     
                 elif maxStrPer > 0 and iper > maxStrPer:
                   if optArgs['gui']: root.destroy()
                   return
             else:
               dataRead=np.fromfile(binfile,np.float32,reclen3d).reshape(shp3d)
    
          #  dataRead[dataRead== -1000000e+030] = -999.9999        
          #  print(np.min(dataRead))
            
               if budget == 'FLOW_RIGHT_FACE': rFaceSlices=dataRead
               for ilayer in range(nlays):
                 #Check root to see if process should be terminated
                 if optArgs['gui']:
                     root.update()
                     if not running:
                       root.destroy()
                       exit(7)
                 slice = dataRead[ilayer,:,:].reshape(shape)
                 rastername = budget + "_" + str(ilayer+1) + "_" + \
                        '{:7.5f}'.format(((iper)/100000.0)) +  "_" + str(kstp)
                 rastername = rastername.replace("_0.","_")
                 if not strPerList or iper in strPerList:
                   if ilayer+1 in layerList:
                     if rasType =='VEC' and budget =='FLOW_FRONT_FACE':
                         rFaceSlice = rFaceSlices[ilayer,:,:].reshape(shape)
                         doFlowVec(rFaceSlice)
                     elif rasType =='VEC' and budget == 'FLOW_RIGHT_FACE':
                         pass
                     elif not optArgs['terms'] or optArgs['terms'] == 'ALL' or budget in termset:
                       MFgis.numPy2Ras(slice, rastername, optArgs,discDict,rasMulti)
                       MFgis.clipRaster(rastername, optArgs)
                 elif maxStrPer > 0 and iper > maxStrPer:
                   if optArgs['gui']: root.destroy()
                   return
          else:
              pass
    except:
      print('Stress period:', wantedSP,' Not present in cell by cell budgets')
  binfile.close()
  if optArgs['gui']: root.destroy()
  return

