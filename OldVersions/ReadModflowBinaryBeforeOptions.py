"""
..module:: ReadBinary
    :platform: Windows
    :synopsis: Read Modflow Binary files and create ArcGIS rasters
    :notes: Added to subVersion Repository
    ::create: 13-Sep-2013
    ::modified: 01-Jan-2016
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""

# (library_name, shorthand)
import sys
import easygui as ez
named_libs = [('numpy', 'np'),
              ('pandas', 'pd')]
for (name, short) in named_libs:
    try:
        lib = __import__(name)
    except:
        print sys.exc_info()
    else:
        globals()[short] = lib
libnames = ['os', 'arcpy', 're','argparse','textwrap']
for libname in libnames:
    try:
        lib = __import__(libname)
    except:
        print sys.exc_info()
    else:
        globals()[libname] = lib

import numpy as np
import pandas as pd
import os
import arcpy
import re
import argparse
import textwrap

global SR
global modelOrigins
global primaryWrkSpace
global clipWrkSpace
global dfDict
# set default spatial Reference
SR = arcpy.SpatialReference(2881)
print "Default spatial reference"
print SR.name
dfDict ={}
model_SR = {
        'C4CDC':2881,'ECFM':2881,'ECFT':2881,'ECFTX':2881,
        'LECSR':2881,'NPALM':2881,'LKBGWM':2881,'LWCFAS':2881,
        'LWCSAS':2881,'LWCSIM':2881,'WCFM':2881}
modelOrigins = {
        'C4CDC' :arcpy.Point(763329.000, 437766.000),
        'ECFM'  :arcpy.Point(565465.000, -44448.000),
        'ECFT'  :arcpy.Point(330706.031,1146903.250),
        'ECFTX' :arcpy.Point( 24352.000, 983097.000),
        'LECSR' :arcpy.Point(680961.000, 318790.000),
        'LKBGWM':arcpy.Point(444435.531, 903882.063),
        'NPALM' :arcpy.Point(680961.000, 839750.000),
        'LWCFAS':arcpy.Point(438900.000, -80164.000),
        'LWCSAS':arcpy.Point(292353.000, 456228.000),
        'LWCSIM':arcpy.Point(218436.000, 441788.000),
        'WCFM'  :arcpy.Point( 20665.000, -44448.000)}
model_choices= list(key for key,val in modelOrigins.iteritems())

# clip      = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin, ExtObj.XMax, ExtObj.YMax)
modelClips ={
        'C4CDC':(0,0,0,0),
        'ECFM':(0,0,0,0),
        'ECFT':(0,0,0,0),
        'ECFTX':(0,0,0,0),
        'LECSR':(0,0,0,0),
        'NPALM':(780652,840449,968193,1016489),
        'LKBGWM':(0,0,0,0),
        'LWCFAS':(0,0,0,0),
        'LWCSAS':(0,0,0,0),
        'LWCSIM':(0,0,0,0),
        'WCFM':(215080, 428340, 587064, 985667)}

def getOptions():
    """
    Example arguments and brief description:

     -geo ECFMdebugging.gdb
     -nam \\WHQBLD01P\fdrive\wsmod2\ECFM\ECFM_models\transient\SEAWAT_Month\ECFMFPL\ecfm_tr.nam
     -lay 1 -bin -str 15
or
     -mod WCFM --binheads --layers 1
     --stress 1,200,275 --namfile M:\wcfm.nam
     --geodatabase  g:\PythonTools\WCFM\WCFMNoClp.gdb
     -clp  g:\PythonTools\WCFM\WCFMclp.gdb
or
     -geo ECFMper.gdb -lay 1 -bin -str 138
          ^           ^    ^      ^
          |           |    |      | Output
          `-geodabase |    |      `-period = 138
                      |    `-Read Binary Heads
                      `-Output  layer = 1
"""

    parser = argparse.ArgumentParser(prog='ReadBinary',
                    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-bin", "--binheads",
                    action="store_true",
                    dest="heads",
                    help="Process binary heads file.")
    parser.add_argument("-swi", "--swiZeta",
                    action="store_true",
                    dest="zeta",
                    help="Process binary zetas file.")
    parser.add_argument("-con", "--concentrations",
                    action="store_true",
                    dest="conc",
                    help="Process binary MT3D file.")
    parser.add_argument("-bud", "--budgets",
                    action="store_true",
                    dest="cbc",
                    help="Process binary cellbcell budgets")
    parser.add_argument("-vec", "--vectors",
                    action="store_true",
                    dest="vector",
                    help="Process binary flow budgets for flow vectors")
    parser.add_argument("-vecbcf", "--vectorsbcf",
                    action="store_true",
                    dest="vectorbcf",
                    help="Process binary flow budgets for flow vectors")
    parser.add_argument("-res", "--resample",
                    type=str,
                    dest="resample",
                    default="1",
                    help="resample=5 for 5x5; default=no resampling:[1x1]")
    parser.add_argument("-multi", "--multiplier",
                    type=float,
                    dest="multiplier",
                    nargs='?',
                    const="1.0",
                    help="multiplier=7.48 for gal/Stress Period; default=no conversion")
    parser.add_argument("-uzf", "--uzfbudgets",
                    action="store_true",
                    dest="uzfcbc",
                    help="Process binary uzf cellbycell budgets.")
    parser.add_argument("-mod",
                    dest="model",
                    choices=model_choices,
                    default='ECFM',
                    help="Model defines Raster Lower Left Origin")
    parser.add_argument("-nam", "--namfile",
                    dest="namefile",
                    help="Assign .NAM FILE")
    parser.add_argument("-geo", "--geodatabase",
                    dest="geodb",
                    default = 'Default.gdb',
                    help="Save rasters in GeoDatabase.")
    parser.add_argument("-ext", "--extents",
                    dest="extShp",
                    default = 'Default.shp',
                    help="Clip rasters to extent.")
    parser.add_argument("-clp","--clipgdb",
                    dest="clpgdb",
                    help="Separate Geodatabase for Clipped Rasters")
    parser.add_argument("-str","--stress",
                    type=str,
                    dest="stressStr",
                    help=textwrap.dedent("""\
                    One stress period: '-str 218'  or
                    multiple stress periods: '-str 1-12,218,288'
                    Omit option [-str] for all layers
                    Use '-str 0' for none (option testing)"""))
    parser.add_argument("-lay", "--layers",
                    dest="layerStr",
                    type=str,
                    help= textwrap.dedent("""\
                    Single layer '-lay 1' or
                    multiple layers '-lay 1,3-4,7'
                    Use '-lay 0' for no rasters.
                    Omit option [-lay] for all layers"""))
    parser.add_argument("-terms",
                    type=str,
                    dest="terms",
                    help=textwrap.dedent("""\
                    Process binary cellbycell budgets.
                        -- 'FLOW' indicates processing Right, Front and Lower face flow
                        -- 'RIGHT|FRONT' indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE
                        --  No parameters indicates all budget terms"""))

    args = parser.parse_args()
    return args

def parse_range(astr):
    result=set()
    if astr != None:
        for part in astr.split(','):
            x=part.split('-')
            result.update(range(int(x[0]),int(x[-1])+1))
    return sorted(result)

def get_SpatialA():
# Check out the ArcGIS Spatial Analyst
#  extension license
    availability = arcpy.CheckExtension("Spatial")
    if availability == "Available":
        print "Check availability of SA"
        arcpy.CheckOutExtension("Spatial")
        print("SA Ext checked out")
    else:
        print("%s extension is not available (%s)"%("Spatial Analyst Extension",availability))
        print("Please ask someone who has it checked out but not using to turn off the extension")
        exit()


def get_unitnumber(file, row_num, item_num):
    """Open and read the Modflow Output Control file
       assign each line read to row[].

       Parse selected row_num and assign
       parsed item_num to unitnum.

       If item_num == 0 use last time in the row
    """
    row=[]
    with open(file, 'r') as f:
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

def get_filename(sourcefile,ftype_inits):
    binlist=[]
    header = ['Initials', 'unitnum', 'filename', 'status']
    binlist.append(header)
    print ("NameFile: \t %s" % sourcefile)
    with open(sourcefile, 'r') as f:
        for line in f.readlines()[1:]:
            if (not line.startswith('#') ):
               if len(line) >1:
                 binlist.append(line.split()[0:4])
    f.close()

    df = pd.DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
    newdf = df[df['Initials'] == ftype_inits]
    _unitnum = newdf['unitnum']
    _filename = newdf['filename']

    theval = str(_filename.values)
    outval = theval.lstrip("['")
    outval = outval.rstrip("']")
    filename = outval
    del df, newdf, _unitnum, _filename
    return filename

def get_filebyNumber(sourcefile,fnumber):
    binlist=[]
    header = ['Initials', 'unitnum', 'filename', 'status']
    binlist.append(header)

    with open(sourcefile, 'r') as f:
        for line in f.readlines()[1:]:
            if not line.startswith('#'):
                binlist.append(line.split()[0:4])
    f.close()

    df = pd.DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
    newdf = df[df['unitnum'] == fnumber]
    _unitnum = newdf['unitnum']
    _filename = newdf['filename']
    theval = str(_filename.values)
    outval = theval.lstrip("['")
    outval = outval.rstrip("']")
    filename = outval

    del df, newdf, _unitnum, _filename
    return filename

def get_bas_df(file):
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
    
    dfDict['layer']=layer
    dfDict['nrows']=nrows
    dfDict['ncols']=ncols
    dfDict['nperiod']=nper
    del row
    return dfDict

def get_bcf_df(file):
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

    dfDict['cellsize1']= cellsize1
    dfDict['cellsize2']= cellsize2
    
    return dfDict

def get_dis_df(file):
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

    dfDict = {'layer':layer,
              'nrows':nrows,
              'ncols': ncols,
              'nperiod': nper,
              'cellsize1': cellsize1,
              'cellsize2': cellsize2}
    
    return dfDict

def modelDisc(dfDict):
    nlays = int(dfDict['layer'])
    nrows = int(dfDict['nrows'])
    ncols = int(dfDict['ncols'])
    npers = int(dfDict['nperiod'])
    cellsz1 = float(dfDict['cellsize1'])
    cellsz2 = float(dfDict['cellsize2'])
    return nlays,nrows,ncols,npers,cellsz1,cellsz2

def setHeader(binaryType):
    if binaryType == 'HEADS':
        headertypes= np.dtype([
            ("KSTP",   "<i4"),
            ("KPER",   "<i4"),
            ("PERTIM", "<f4"),
            ("TOTIM",  "<f4"),
            ("TEXT",   "S16"),
            ("NC",     "<i4"),
            ("NR",     "<i4"),
            ("K",      "<i4")])
    elif binaryType == 'CBC':
        headertypes= np.dtype([
            ("KSTP",   "<i4"),
            ("KPER",   "<i4"),
            ("TEXT",   "S16"),
            ("NC",     "<i4"),
            ("NR",     "<i4"),
            ("K",      "<i4")])
    elif binaryType == 'CBCUF':
        headertypes= np.dtype([
            ("BOR",    "<i4"),
            ("KSTP",   "<i4"),
            ("KPER",   "<i4"),
            ("TEXT",   "S16"),
            ("NC",     "<i4"),
            ("NR",     "<i4"),
            ("K",      "<i4"),
            ("EOR",    "<i4")])
    elif binaryType == 'XCBC':
        headertypes = np.dtype([
            ("IMETH",  "<i4"),
            ("DELT",   "<f4"),
            ("PERTIM", "<f4"),
            ("TOTIM",  "<f4")])
    else:
        print ("undefined headertype: {}".format(binaryType))
        exit()
    return headertypes

def numpytoras(inarr, rasname, llorig, SR):
    dfval=[]
    dfattrib=[]
    cellsz1 = float(dfDict['cellsize1'])
    cellsz2 = float(dfDict['cellsize2'])
    print ""
    print ("Raster: {}".format(rasname))
    ras = arcpy.NumPyArrayToRaster(inarr,llorig,cellsz1,cellsz2,999)
    arcpy.DefineProjection_management(ras, SR)
    ras.save(arcpy.env.workspace +"\\" + rasname)
    del inarr, ras

def clipRaster(ClipRectangle,defClip,rastername,ws1,ws2):
    if ClipRectangle != 'Default.shp':
        desc = arcpy.Describe(ClipRectangle)
        ExtObj    = desc.extent
        clip      = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin, ExtObj.XMax, ExtObj.YMax)
    else:
        clip      = "%d %d %d %d" % (defClip[0],defClip[1],defClip[2],defClip[3])
    clpRaster = "clp" +rastername
    InRastername = ws1 + "//" + rastername
#    print (rastername)
    if defClip != (0,0,0,0):
        arcpy.env.workspace = ws2
        arcpy.gp.ExtractByRectangle_sa(InRastername,clip,clpRaster,"INSIDE")
        print ("Clipped Raster: {}".format(clpRaster))
        arcpy.env.workspace = ws1
    else:
        print ("Clip Extent is undefined.  Not producing {}".format(clpRaster))
    return

def MagDirFunc(rFaceSlice, fFaceSlice):
    """ Calculate Four-Quadrant Inverse Tangent and convert radians to degrees
        Negative results for degrees are adjusted to reflect range from 180 thru 360 """

    tmpdirSlice = np.arctan2(fFaceSlice,rFaceSlice)*180 / np.pi
    dirSlice = np.where(tmpdirSlice > 0.0, tmpdirSlice, (tmpdirSlice+360.0))
    magSlice = np.power((np.power(fFaceSlice,2)+np.power(rFaceSlice,2)),.5)
    return magSlice, dirSlice

def read_headfile(binfilename,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2):
    get_SpatialA()
    read_data=[]
    nlays,nrows,ncols,npers,cellsz1,cellsz2=modelDisc(dfDict)
    
    headertypes=setHeader('HEADS')
    knt= int(nrows)*int(ncols)
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    maxStressPeriod =  max(strPerList)
    binfile=open(binfilename,'rb')
    endOfTime = False

    for strPerByLay in xrange(int(npers*nlays)):
        MFheadRec    = []
        MFheadRec    = np.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
        kper         = MFheadRec["KPER"][0]
        k            = MFheadRec["K"][0]
        read_data = np.fromfile(file=binfile, dtype=np.float32, count=knt, sep='').reshape(shape)
        rastername = "HEAD" + '{:7.5f}'.format(((kper)/100000.0)) + "_" + str(k)
        rastername = rastername.replace("0.","_")
        if layerList != [0] or strPerList != [0]:
            if k in layerList:
                if not strPerList or kper in strPerList:
                    numpytoras(read_data, rastername, llorigin,SR)
                    clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                elif kper > maxStressPeriod:
                    endOfTime = True
#                    print "EndofTime= SP="+str(strPerList)+" kper=" + str(kper) + " > Maxts = " + str(maxStressPeriod)
                    print ("EndofTime reached: SP={} KPER= {} > MaxSP = {}".format(strPerList,kper, maxStressPeriod))
        if endOfTime:
            exit()
    binfile.close()
    del read_data, MFheadRec, headertypes

def read_concfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2):
    get_SpatialA()

    read_data=[]
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(dfDict)

# Modflow Binary Heads and Concentration share the same file structure
    headertypes=setHeader('HEADS')
    knt= nrows*ncols
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    maxStressPeriod =  max(strPerList)

    binfile=open(binfilename,'rb')
    for i in xrange(npers):
        for l in range(0,nlays):
            MFheadRec    = []
            MFheadRec    = np.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
            totim        = MFheadRec["TOTIM"][0]
            k            = MFheadRec["K"][0]

            read_data = np.fromfile(file=binfile, dtype=np.float32, count=knt, sep='').reshape(shape)

            rastername = "CONC" + '{:7.5f}'.format(((totim)/100000.0)) + "_" + str(l+1)
            rastername = rastername.replace("0.","_")
            if layerList != [0] or strPerList != [0]:
                if not layerList or k in layerList:
                    if not strPerList or totim in strPerList:
                        numpytoras(read_data, rastername,llorigin,SR)
                        clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)

                    if strPerList and totim > maxStressPeriod:
                        pass
                        return
    binfile.close()
    del read_data, MFheadRec, headertypes

def read_cbcfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2,terms,form,factor):
    get_SpatialA()
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(dfDict)
    read_data=[]
    shape = (nrows,ncols)
    reclength= nrows*ncols
    shape3d = (nlays,nrows,ncols)
    reclen3d= nlays*nrows*ncols

    cbcheadertypes=setHeader('CBC')
    cbcUFheadtypes=setHeader('CBCUF')
    compactHeader=setHeader('XCBC')

    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    if strPerList:
        maxStressPeriod =  max(strPerList)
    else:
        maxStressPeriod = 0
    if terms:
        termset = re.compile(terms)

    print ("Binary Filename: {}".format(binfilename))
    binfile=open(binfilename,'rb')
    endOfTime = False
    for i in xrange(npers*15):
        MFheadRec1 = []
        MFheadRec2 = []

        if form != 'UF':
            MFheadRec1 = np.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')
        else:
            MFheadRec1 = np.fromfile(file=binfile,dtype=cbcUFheadtypes,count=1,sep='')
        if MFheadRec1.size < 1:
            print ("End of File Encountered")
            exit()

        iper = int(MFheadRec1["KPER"][0])
        budget = MFheadRec1["TEXT"][0].strip().replace(" ","_")
        cbclays = int(MFheadRec1["K"][0])
        if layerList and strPerList :
            if cbclays < 0 :
                # Compact Cell by cell flow file
                MFheadRec2 = np.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
                tottim = int(MFheadRec2["TOTIM"][0])/100000.0
                read_data = np.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)
                ilayer = read_data[1,1]
                print ("ilayer {}".format(ilayer))
                read_data = np.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)
                rastername = budget + "_" + str(ilayer) + "_" + str(tottim).replace("0.","")
 #               print (rastername)
                if not strPerList or iper in strPerList:
                    if ilayer in layerList:
                        if not terms or terms == 'ALL' or termset.search(budget):
                            print (budget)
                            numpytoras(read_data, rastername, llorigin,SR)
                            clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                    elif maxStressPeriod > 0 and iper > maxStressPeriod:
                        endOfTime = True
                        print ("EndOfTime in cbcBudbets")
                        return
                if endOfTime:
                    return
            else:
                if form == 'UF':
                    bor = np.fromfile(file=binfile, dtype=np.int32, count=1, sep='')
                    if len(bor):
                        pass
                read_data = np.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)

                for ilayer in range(nlays):
                    slice = read_data[ilayer,:,:].reshape(shape)
                    rastername = budget + "_" + str(ilayer+1) + "_" + '{:7.5f}'.format(((iper)/100000.0))
                    rastername = rastername.replace("_0.","_")

                    if not strPerList or iper in strPerList:
                        if ilayer+1 in layerList:
                            if not terms or terms == 'ALL' or termset.search(budget):
                                numpytoras(slice, rastername, llorigin,SR)
                                clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                    elif maxStressPeriod > 0 and iper > maxStressPeriod:
                        endOfTime = True
                        return
                if endOfTime:
                    return
    binfile.close()
#   clean-up
    del read_data, MFheadRec1, MFheadRec2, cbcheadertypes, compactHeader

def read_cbcVectors(binfilename,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2,terms,cellsize,form,factor):
    get_SpatialA()
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(dfDict)
    MFheadRec2 = []
    csizeMultiplier = int(cellsize)
    CsizeVal = csizeMultiplier * cellsz1
    cellsize = str(CsizeVal)
    print ("Resampling factor: {}x{} cells".format(csizeMultiplier,csizeMultiplier))

    read_data=[]
    shape = (nrows,ncols)
    reclength= nrows*ncols
    shape3d = (nlays,nrows,ncols)
    reclen3d= nlays*nrows*ncols
    cbcheadertypes=setHeader('CBC')
    print ("FORM-{}".format(form))
    cbcheadertypes=setHeader('CBC')
    cbcUFheadtypes=setHeader('CBCUF')
    compactHeader=setHeader('XCBC')

    def doFlowVec(factor):
        global rFaceSlice
        if budget == 'FLOW_RIGHT_FACE':
            rFaceSlice = slice
        if budget == 'FLOW_FRONT_FACE':
            fFaceSlice = slice
            (magSlice, dirSlice) = MagDirFunc(rFaceSlice, fFaceSlice)
            rasterdir = "LAY0" + str(ilayer+1) + "DIR_" + '{:7.5f}'.format(((iper)/100000.0))
            rasterdir = rasterdir.replace("_0.","_")
            rastermag = rasterdir.replace("DIR_","MAG_")
 #           print (rasterdir)
 #           print (rastermag)
            numpytoras(dirSlice, rasterdir,llorigin,SR)
            numpytoras(magSlice, rastermag,llorigin,SR)
            if defClip != (0,0,0,0):
                clipRaster(ClipRectangle,defClip,rasterdir,ws1,ws2)
                clipRaster(ClipRectangle,defClip,rastermag,ws1,ws2)

            if csizeMultiplier > 1:

                print ("Resampling rasters ...")
                rasterdirResamp="LAY0" + str(ilayer+1) + "DIRX_" + '{:7.5f}'.format(((iper)/100000.0))
                rasterdirResamp = rasterdirResamp.replace("_0.","_")
                rastermagResamp = rasterdirResamp.replace("DIRX_","MAGX_")
                arcpy.Resample_management(rasterdir, rasterdirResamp, cellsize, "BILINEAR")
                arcpy.Resample_management(rastermag, rastermagResamp, cellsize, "BILINEAR")
                if defClip != (0,0,0,0):
                    clipRaster(ClipRectangle,defClip,rasterdirResamp,ws1,ws2)
                    clipRaster(ClipRectangle,defClip,rastermagResamp,ws1,ws2)

                rastDirX = arcpy.env.workspace + "\\" + rasterdirResamp
                arrowFeatureX = arcpy.env.workspace +"\\" + rasterdirResamp + "arw"
                inMemFCX = arrowFeatureX

                print ("Points for Flow Arrows: {}".format(os.path.basename((arrowFeatureX))))

                arcpy.RasterToPoint_conversion(in_raster=rastDirX,out_point_features=inMemFCX,raster_field="VALUE")
                inRasterListX = rastermagResamp+ " Magnitude"
                print ("Extracting Flow Magnitudes to Points")

                arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCX,inRasterListX,"NONE")
                express = "!Magnitude! * "  + str(csizeMultiplier) + " * " + str(csizeMultiplier)
                arcpy.CalculateField_management(in_table=inMemFCX,field="Magnitude",
                                                expression=express,expression_type="PYTHON_9.3",code_block="#")

                if defClip != (0,0,0,0):
                    arcpy.env.workspace = ws2
                    rastDirXclp = arcpy.env.workspace + "\\clp" + rasterdirResamp
                    arrowFeatureXclp = arcpy.env.workspace +"\\clp" + rasterdirResamp + "arw"
                    inMemFCXclp = arrowFeatureXclp
                    print ("Clipped Points for Flow Arrows: {}".format(os.path.basename((arrowFeatureXclp))))
                    arcpy.RasterToPoint_conversion(in_raster=rastDirXclp,out_point_features=inMemFCXclp,raster_field="VALUE")
                    inRasterListXclp = "clp"+rastermagResamp+ " Magnitude"
                    arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCXclp,inRasterListXclp,"NONE")
                    arcpy.CalculateField_management(in_table=inMemFCXclp,field="Magnitude",
                                                            expression=express,expression_type="PYTHON_9.3",code_block="#")
                    arcpy.env.workspace = ws1
            else:
                print ("No resampling")

                rastDir = arcpy.env.workspace +"\\" + rasterdir
                arrowFeature = arcpy.env.workspace +"\\" + rasterdir + "arw"
                inMemFC = arrowFeature
                print ("Points for Flow Arrows: {}".format(os.path.basename(arrowFeature)))
                arcpy.RasterToPoint_conversion(in_raster=rastDir,out_point_features=inMemFC,raster_field="VALUE")
                MyField = "Magnitude"
                inRasterList = rastermag+ " " + MyField
                print ("Adding Magnitude to Flow Arrows")
                arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFC,inRasterList,"NONE")

                if defClip != (0,0,0,0):
                    arcpy.env.workspace = ws2
                    rastDirclp = arcpy.env.workspace +"\\clp" + rasterdir
                    arrowFeatureclp = arcpy.env.workspace +"\\clp" + rasterdir + "arw"
                    inMemFCclp = arrowFeatureclp
                    print ("Clipped Points for Flow Arrows: {}".format(os.path.basename(arrowFeatureclp)))
                    arcpy.RasterToPoint_conversion(in_raster=rastDirclp,out_point_features=inMemFCclp,raster_field="VALUE")
                    arcpy.env.workspace = ws1
                    MyField = "Magnitude"
                    inRasterList = rastermag+ " " + MyField
                    print ("Adding Magnitude to Flow Arrows")
                    arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCclp,inRasterList,"NONE")
        return

    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    if strPerList != []:
        maxStressPeriod =  max(strPerList)
    else:
        maxStressPeriod = 0
    if terms:
        termset = re.compile(terms)

    print ("Binary filename: {}".format(binfilename))
    binfile=open(binfilename,'rb')
    endOfTime = False
    dot = '.'
    for i in xrange(npers*20):
        if form != 'UF':
            MFheadRec1 = np.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')
        else:
            MFheadRec1 = np.fromfile(file=binfile,dtype=cbcUFheadtypes,count=1,sep='')
#        print (MFheadRec1)
        sys.stdout.write('.')
        if MFheadRec1.size < 1:
            print ("End of File Encountered")
            exit()

        iper = int(MFheadRec1["KPER"][0])
        budget = MFheadRec1["TEXT"][0].strip().replace(" ","_")

        cbclays = int(MFheadRec1["K"][0])

        if cbclays < 0 and layerList != [0] and strPerList != [0]:
            print ("Working with Compact Headers")
            MFheadRec2 = np.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
#            print (MFheadRec2)

            read_data = np.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)

            ilayer = read_data[1,1]
            #print "ilayer", ilayer
            read_data = np.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)

            if strPerList == [] or iper in strPerList:
                if ilayer in layerList:
                    if termset.search(budget):
                        doFlowVec(factor)
            elif maxStressPeriod > 0 and iper > maxStressPeriod:
                endOfTime = True
                return
            if endOfTime:
                return
        elif layerList != [0] and strPerList != [0]:
            if form == 'UF':
                bor = np.fromfile(file=binfile, dtype=np.int32, count=1, sep='')
                if len(bor):
                    pass
            read_data = np.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            if form == 'UF':
                eor = np.fromfile(file=binfile, dtype=np.int32, count=1, sep='')
                if len(eor):
                    pass
            for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)
                if strPerList == [] or iper in strPerList:
                    if ilayer+1 in layerList:
                        if termset.search(budget):
                            doFlowVec(factor)
                elif iper > maxStressPeriod:
                    endOfTime = True
                    return
            if endOfTime:
                return

    binfile.close()
    #clean-up
    del read_data, cbcheadertypes

def define_workspace(geodb):
    """Set base paths for Modflow namefile and ESRI workspace. """
    out_folder_path = "H:\\Documents\\ArcGIS"
    if geodb == "Default.gdb":
        print ("Default geodatabase path defined as {}".format(out_folder_path))
    elif geodb != None:
        (temp_path, gdbfile) = os.path.split(geodb)
        out_folder_path = temp_path
        print ('Requested output path is: {}'.format(temp_path))
        print ('Geodb: {}'.format(gdbfile))
    else:
        print ("Unspecified working path.  Assigning: {}".format(path))
        out_folder_path =  path
        (out_folder_path, gdbfile) = os.path.split(out_folder_path)
        print ('output path: {}'.format(out_folder_path))
        print ('Geodb: {}'.format(gdbfile))
    workspace = os.path.join(out_folder_path, gdbfile)
    print ("Workspace has been defined as: {}".format(workspace))
    print ("does workspace exist:")
    print (arcpy.Exists(workspace))

    if not arcpy.Exists(workspace):
        print ("Workspace does not exist.  Creating New one!")
        (temp_path, gdbfile) = os.path.split(workspace)
        if temp_path == "":
            temp_path = out_folder_path
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

  arcpy.env.workspace = r"IN_MEMORY"
  fcs = arcpy.ListFeatureClasses()
  tabs = arcpy.ListTables()
  rasters = arcpy.ListRasters()

  ### for each FeatClass in the list of fcs's, delete it.
  for f in fcs:
    arcpy.Delete_management(f)
    arcpy.AddMessage("deleted Feature Classes: " + f)
  ### for each TableClass in the list of tab's, delete it.
  for t in tabs:
    arcpy.Delete_management(t)
    arcpy.AddMessage("deleted Tables: " + t)
  ### for each raster, delete it.
  for r in rasters:
    arcpy.Delete_management(r)
    arcpy.AddMessage("deleted Rasters: "+r)

def define_disfile():
    disFilename = get_filename(path + "\\" + namfile, 'DIS')
    disFilename_full = path + "\\" + disFilename
# If DIS file doesn't exist from .NAM file construct info from BAS and BCF files
    if disFilename.strip() == "":
        basFilename = get_filename(path + "\\" + namfile, 'BAS')
        print ("new {}".format(basFilename))
        basFilename_full = path + "\\" + basFilename
        df = []
        dfDict = get_bas_df(basFilename_full)
        print (basdf)
        bcfFilename = get_filename(path + "\\" + namfile, 'BCF')
        print ("new {}".format(bcfFilename))
        bcfFilename_full = path + "\\" + bcfFilename
        dfDict = get_bcf_df(bcfFilename_full)
        disdf = bcfdf
    else:
        df =[]
        dfDict = get_dis_df(disFilename_full)
    return dfDict

#--------------------------------------------------------------------
#
#   Let the processing Begin..............
#
#--------------------------------------------------------------------

options = getOptions()
option_dict = vars(options)

for k in option_dict.iteritems():
    label, value = k
    print ("{:<15} {:>6}".format(label, value))

llorigin = modelOrigins[options.model]
defClip = modelClips[options.model]
SR = arcpy.SpatialReference(model_SR[options.model])
print ("Assigned Spatial Reference: {}".format(SR.name))

multiplier = options.multiplier

if options.namefile:
    (path, namfile) = os.path.split(options.namefile)
    if path == '':
        print ('''Explicit path missing.  
                  Using default path for testing''')
        path = '\\\\WHQBLD01P\\fdrive\\wsmod2\\ECFM\\ECFM_models\\transient\\SEAWAT_Month\\ECFMPER'
else:
    print ("""Unable to process Binary data without file location details.
            nam/namfile argument is required:
               -nam NAMEFILE,  --namfile=NAMEFILE   Read data from .NAM FILE""")
    exit()

#--------------------------------------------------------------------
#   Assign Modflow NAM file
#--------------------------------------------------------------------
if options.namefile:
    (nampath, namfile) = os.path.split(options.namefile)

primaryWrkSpace=define_workspace(options.geodb)
ws1 = primaryWrkSpace
dfDict = define_disfile()

#
#   Setup and process binary Heads file:
#

if options.extShp:
    ClipRectangle = options.extShp
    if not arcpy.Exists(ClipRectangle):
        print ("Did Not Find shapefile for Clip Extents: {}".format(ClipRectangle))
        if modelClips[options.model] == (0,0,0,0):
            print ("No clip extents")
        else:
            print ("Default clip extents are: %s for %s" % (str(modelClips[options.model]),str(options.model)))
    else:
        print ("{} has been found".format(ClipRectangle))
    if options.clpgdb:
        clipWrkSpace=define_workspace(options.clpgdb)

        print ("Clip Workspace = {}".format(clipWrkSpace))
    else:
        clipWrkSpace = primaryWrkSpace
        print ("No Clip Workspace defined...Using Primary Workspace for Clipped Raster Storage")

    ws2 = clipWrkSpace
    arcpy.env.workspace = primaryWrkSpace

if options.heads:
    ocFilename = get_filename(path + "\\" + namfile, 'OC')
    ocFilename_full = path + "\\" + ocFilename
    print ("Output Control filename: {}".format(ocFilename))

    if (options.model == 'ECFM'):
       HeadsUnit = get_unitnumber(ocFilename_full,1,0)
    elif (options.model == 'C4CDC'):
       HeadsUnit = get_unitnumber(ocFilename_full,1,3)
    elif (options.model == 'NPALM'):
       HeadsUnit = get_unitnumber(ocFilename_full,1,3)
    else:
       HeadsUnit = get_unitnumber(ocFilename_full,1,0)

#    print ("Heads file unit number %i" % int(HeadsUnit))
    headsfile = get_filebyNumber(path + "\\" + namfile,HeadsUnit)
    headsfile = path + "\\" + headsfile
    print ("heads binary filename: {}".format(headsfile))
    read_headfile(headsfile,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)
if options.zeta:
    swiFilename = get_filename(path + "\\" + namfile, 'SWI2')
    swiFilename_full = path + "\\" + swiFilename
    zetaUnit = get_unitnumber(swiFilename_full,1,4)

#    print "SWI Zeta file unit number %i" % int(zetaUnit)

    zetafilename = get_filebyNumber(path + "\\" + namfile, zetaUnit)
    zetafilename = path + "\\" + zetafilename

    print ("....attempting to process zeta binary file")
    print (zetafilename)

    read_headfile(zetafilename,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)

#
#   Setup and process binary Cell by cell Budgets:
#
if options.conc:
    concfile = path + "\\MT3D001.UCN"
    print ("....attempting to process MT3D binary file")

    if not os.path.exists(concfile):
        print ("Modflow Concentration file does not exist")
        exit(1)
    else:
        print ("Modflow Concentration file exists")
    read_concfile(concfile,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)

if options.uzfcbc:
    uzfFilename = get_filename(path + "\\" + namfile, 'UZF')
    uzfFilename_full = path + "\\" + uzfFilename
    uzfUnit = get_unitnumber(uzfFilename_full,1,6)
#    print "CellxCell Flow file unit number %i" % int(uzfUnit)
    uzfcbcfilename = get_filebyNumber(path + "\\" + namfile, uzfUnit)
    uzfcbcfilename = path + "\\" + uzfcbcfilename
    print ("CellxCell Flow filename: {}".format(uzfcbcfilename))

    read_cbcfile(uzfcbcfilename,disdf,options.layerStr,options.stressStr,llorigin,SR)

#
#   Setup and process binary LPF Cell by cell Budgets:
#

if options.cbc:
    form = 'BINARY'
    cbcFilename = get_filename(path + "\\" + namfile, 'LPF')
    if cbcFilename.strip() == "":
        cbcFilename = get_filename(path + "\\" + namfile, 'BCF')
        form='UF'
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = get_unitnumber(cbcFilename_full,1,1)
    if int(cbcUnit) == 0:
        cbcUnit = get_unitnumber(cbcFilename_full,1,2)
    cbcfilename = get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print ("CellxCell Flow filename {} on unit {}".format(cbcfilename,cbcUnit))
    read_cbcfile(cbcfilename,disdf,options.layerStr,options.stressStr,llorigin,
                 SR,ClipRectangle,defClip,ws1,ws2,options.terms,form,multiplier)

if options.resample:
    cellsize = options.resample
else:
    cellsize = '1'

if options.vector:
    form = 'BINARY'
    cbcFilename = get_filename(path + "\\" + namfile, 'LPF')
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = get_unitnumber(cbcFilename_full,1,1)
    cbcfilename = get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print ("CellxCell Flow filename {} on unit {}".format(cbcfilename,cbcUnit))

    if options.terms != 'RIGHT|FRONT':
      VectorTerms = 'RIGHT|FRONT'
      print ("""Overriding terms option for flow vectors: 
             required terms are -- 'RIGHT|FRONT' 
             indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE """)
    read_cbcVectors(cbcfilename,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2,VectorTerms,cellsize,form,multiplier)
    clearINMEM()
    arcpy.CheckInExtension("Spatial")
if options.vectorbcf:
    cbcFilename = get_filename(path + "\\" + namfile, 'BCF6')
    if cbcFilename.strip() == "":
        cbcFilename = get_filename(path + "\\" + namfile, 'BCF')
        form='UF'
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = get_unitnumber(cbcFilename_full,1,1)
    if int(cbcUnit) == 0:
        cbcUnit = get_unitnumber(cbcFilename_full,1,2)
#    print "CellxCell Flow file unit number %i" % int(cbcUnit)
    cbcfilename = get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print ("CellxCell Flow filename {}".format(cbcfilename))

    if options.terms != 'RIGHT|FRONT':
      VectorTerms = 'RIGHT|FRONT'
      print ("""Overriding terms option for flow vectors: 
             required terms are -- 'RIGHT|FRONT' 
             indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE """)
    read_cbcVectors(cbcfilename,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2,VectorTerms,cellsize,form,multiplier)
    clearINMEM()
    arcpy.CheckInExtension("Spatial")
print ("...finished")

