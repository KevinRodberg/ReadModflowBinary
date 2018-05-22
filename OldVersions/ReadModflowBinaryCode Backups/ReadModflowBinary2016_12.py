"""
..module:: ReadBinary
    :platform: Windows
    :synopsis: Command line option/argument interface to ModflowRasters module
    :notes: Added to subVersion Repository 
    ::create: 13-Sep-2013
    ::modified: 01-Jan-2016
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""

import time
import csv
import numpy
import os
import arcpy
import struct
import sys
import ModflowBinary2Rasters as mfr

from argparse import ArgumentParser

def getOptions(model_choices):
    """Return command line arguments and options.

    -h,           --help               Show help message and exit
    -bin,         --binheads           Read binary heads file
    -swi	  --swi 	       Read SWI zeta binary
    -bud,         --budgets            Read binary flow budgets
    -ext,         --extents            Clip Raster to extents of shape
    -clp,         --clipgdb            Separate Geodatabase for Clipped Rasters
    -con,         --concentrations     Read binary MT3D file
    -vec,         --vectors            Read binary flow (front and right face)
    -multi,       --multiplier         Convert Budget and Vector Rasters from
                                        CubicFeet/StressPeriod to OtherUnits
    -uzf,         --uzfbudgets         Read binary uzf flow budgets
    -mod,         --modelname          Model acronym ['ECFM', 'ECFT']
                                       Used to define Lower Left Origin

            [Arguments required with the following Options:]

    -nam NAMEFILE,  --namfile=NAMEFILE   Assign .NAM FILE
    -geo GEODB,     --geodatabase=GEODB  Saves rasters in  GeoDatabase
    -str STRESS,    --stress=STRESS      Process  stress periods '1-12,218,288'
                                            or Omit for all stress periods
                                            or 0 for option testing
    -lay RASTERS,   --layer=RASTERS      Output layer '1,3-4,7'
                                            or   0 for no rasters
                                            or   Omit option for all layers
    -res NumCELLS,  --resample=NumCELLS  resample=5 for 5x5; default is no resampling or 1x1                                            

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


    parser = ArgumentParser(prog='ReadBinary')
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
    parser.add_argument("-geo", "--geodatabase", dest="geodb",
                      default = 'Default.gdb',
                      help="Save rasters in GeoDatabase.")
    parser.add_argument("-ext", "--extents", dest="extShp",
                      default = 'Default.shp',
                      help="Clip rasters to extent.")
    parser.add_argument("-clp","--clipgdb", dest="clpgdb",
                      help="Separate Geodatabase for Clipped Rasters")
    parser.add_argument("-str","--stress",
                        type=str,
                        dest="stressStr",
                        help="One stress period: '-str 218'  or   \
                            multiple stress periods: '-str 1-12,218,288'   \
                            Omit option [-str] for all layers \
                            Use '-str 0' for none (option testing)")
    parser.add_argument("-lay", "--layers",
                        dest="layerStr",
                        type=str,
                        help="Single layer '-lay 1' or   \
                            multiple layers '-lay 1,3-4,7'    \
                            Use '-lay 0' for no rasters.       \
                            Omit option [-lay] for all layers")
    parser.add_argument("-terms",                    
                        type=str,
                        dest="terms",
                        help="Process binary cellbycell budgets. \
                        -- 'FLOW' indicates processing Right, Front and Lower face flow \
                        -- 'RIGHT|FRONT' indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE \
                        --  No parameters indicates all buget terms")        
    
    args = parser.parse_args()
    print args
 
    return args

def setModelOrigins():
  global modelOrigins
  global SR
  global primaryWrkSpace
  global clipWrkSpace
  SR = arcpy.SpatialReference(2881)
  print "spatial reference"
  print SR

  modelOrigins = dict(C4CDC=arcpy.Point(763329.000,437766.000),
                      ECFM=arcpy.Point(565465.000,-44448.000),
                      ECFT=arcpy.Point(330706.031,1146903.250),
                      ECFTX=arcpy.Point(307488.25,2990678.5),
                      LECSR=arcpy.Point(680961.000,318790.000),
                      LKBGWM=arcpy.Point(444435.531,903882.063),
                      NPALM=arcpy.Point(680961.000,839750.0),                      
                      LWCFAS=arcpy.Point(438900.000,-80164.000),
                      LWCSAS=arcpy.Point(292353.000,456228.000),
                      LWCSIM=arcpy.Point(218436.0,441788.0),
                      WCFM=arcpy.Point(20665.000,-44448.000)
                      )

  model_choices= list(key for key,val in modelOrigins.iteritems())
  return model_choices
  
def setModelSR():
  global model_SR
  modelSR = dict(C4CDC=(2881),
                    ECFM=(2881),
                    ECFT=(2881),
                    ECFTX=(26916),
                    LECSR=(2881),
                    NPALM=(2881),
                    LKBGWM=(2881),
                    LWCFAS=(2881),
                    LWCSAS=(2881),
                    LWCSIM=(2881),
                    WCFM=(2881)
                      )
  model_SRnum = list(key for key, value in modelSR.iteritems())
  return model_SRnum
def setClipExtents():
  global modelClips
  # clip      = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin, ExtObj.XMax, ExtObj.YMax)
  modelClips = dict(C4CDC=(0,0,0,0),
                    ECFM=(0,0,0,0),
                    ECFT=(0,0,0,0),
                    ECFTX=(0,0,0,0),
                    LECSR=(0,0,0,0),
                    NPALM=(780652,840449,968193,1016489),
                    LKBGWM=(0,0,0,0),
                    LWCFAS=(0,0,0,0),
                    LWCSAS=(0,0,0,0),
                    LWCSIM=(0,0,0,0),
                    WCFM=(215080, 428340, 587064, 985667)
                      )
  model_clip_exts = list(key for key, value in modelClips.iteritems())
  return model_clip_exts

def define_workspace(geodb):
    """Set base paths for Modflow namefile and ESRI workspace. """
    out_folder_path = "H:\\Documents\\ArcGIS"

    if geodb == "Default.gdb":
        out_name = "Default.gdb"
        print "Default geodatabase path defined as" + out_folder_path
        
    elif geodb <> None:
        (temp_path, gdbfile) = os.path.split(geodb)
        out_folder_path = temp_path
        print 'Requested output path is:' + temp_path
        print 'Geodb:' + gdbfile
        out_name = geodb        
    else:
        print "Unspecified working path.  Assigning: " + path
        out_folder_path =  path

        (out_folder_path, gdbfile) = os.path.split(out_folder_path)
        print 'output path:' + out_folder_path
        print 'Geodb:' + gdbfile
        out_name = gdbfile

    workspace = os.path.join(out_folder_path, gdbfile)
    print "Workspace has been defined as: " + workspace
    print "does workspace exist:"
    print arcpy.Exists(workspace)
    
    if not arcpy.Exists(workspace):
        print "Workspace does not exist.  Creating New one!"
        (temp_path, gdbfile) = os.path.split(workspace)
        print temp_path
        if temp_path == "":
            temp_path = out_folder_path
        print temp_path        
        print gdbfile
        arcpy.CreateFileGDB_management(temp_path, gdbfile)
        arcpy.env.workspace = os.path.join(temp_path, gdbfile)
    else:
        arcpy.env.workspace = workspace
        
    print "output will be written to:" + workspace 
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
    acrpy.Delete_management(r)
    arcpy.AddMessage("deleted Rasters: "+r)


def define_disfile():
    disFilename = mfr.get_filename(path + "\\" + namfile, 'DIS')
    basefile = path + "\\" 
    disFilename_full = path + "\\" + disFilename
    
    if disFilename.strip() == "":
        basFilename = mfr.get_filename(path + "\\" + namfile, 'BAS')
        print "new" + basFilename
        basFilename_full = path + "\\" + basFilename
        df = []
        basdf = mfr.get_bas_df(basFilename_full,df)
        print basdf
        bcfFilename = mfr.get_filename(path + "\\" + namfile, 'BCF')
        print "new" + bcfFilename
        bcfFilename_full = path + "\\" + bcfFilename
        bcfdf = mfr.get_bcf_df(bcfFilename_full,basdf)
        print bcfdf
        disdf = bcfdf
    else:
        df =[]
        disdf = mfr.get_dis_df(disFilename_full,df)
    
    return disdf

#--------------------------------------------------------------------
#
#   Let the processing Begin..............
# 
#--------------------------------------------------------------------


model_choices = setModelOrigins()
modelExtents = setClipExtents()
model_SRnum = setModelSR()
options = getOptions(model_choices)

option_dict = vars(options)

for k in option_dict.iteritems():
    label, value = k
    print "{:<15} {:<10}".format(label, value)

if options.namefile:
    (path, namfile) = os.path.split(options.namefile)
    if path == '':
        print 'Explicit path missing.  '
        print 'Using default path for testing'
        path = '\\\\WHQBLD01P\\fdrive\\wsmod2\\ECFM\\ECFM_models\\transient\\SEAWAT_Month\\ECFMPER'
else:
    print "Unable to process Binary data without file location details."
    print "nam/namfile argument is required:"
    print "    -nam NAMEFILE,  --namfile=NAMEFILE   Read data from .NAM FILE"
    exit()


#--------------------------------------------------------------------
#   Assign Modflow NAM file 
#--------------------------------------------------------------------
if options.namefile:
    (nampath, namfile) = os.path.split(options.namefile)


primaryWrkSpace=define_workspace(options.geodb)
ws1 = primaryWrkSpace
disdf = define_disfile()

#    
#   Setup and process binary Heads file:
#

if options.extShp:
    ClipRectangle = options.extShp
    if not arcpy.Exists(ClipRectangle):
        print "Did Not Find shapefile for Clip Extents: " + ClipRectangle
        if modelClips[options.model] == (0,0,0,0):
            print "No clip extents"
        else:
            print "Default clip extents are: ", modelClips[options.model]
    else:
        print ClipRectangle + " has been found"
    if options.clpgdb:
        clipWrkSpace=define_workspace(options.clpgdb)

        print "Clip Workspace =", clipWrkSpace
    else:
        clipWrkSpace = primaryWrkSpace
        print "No Clip Workspace defined...Using Primary Workspace for Clipped Raster Storage"

    ws2 = clipWrkSpace        
    arcpy.env.workspace = primaryWrkSpace
 
    
if options.heads:
    ocFilename = mfr.get_filename(path + "\\" + namfile, 'OC')
    ocFilename_full = path + "\\" + ocFilename
    print ocFilename
    if (options.model == 'ECFM'):
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,0)
    elif (options.model == 'C4CDC'):
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,3)
    elif (options.model == 'NPALM'):
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,3)        
    else:
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,0)
       
    print "Heads file unit number %i" % int(HeadsUnit)
    headsfile = mfr.get_filebyNumber(path + "\\" + namfile,HeadsUnit)

    headsfile = path + "\\" + headsfile
    print "....attempting to process heads binary file"
    print headsfile
    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    SR = modelSR[options.model]
    mfr.read_headfile(headsfile,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)
if options.zeta:
    swiFilename = mfr.get_filename(path + "\\" + namfile, 'SWI2')
    swiFilename_full = path + "\\" + swiFilename
    
    zetaUnit = mfr.get_unitnumber(swiFilename_full,1,4)

    
    print "SWI Zeta file unit number %i" % int(zetaUnit)
    
    zetafilename = mfr.get_filebyNumber(path + "\\" + namfile, zetaUnit)
    zetafilename = path + "\\" + zetafilename

    print "....attempting to process zeta binary file"
    print zetafilename
    
    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    mfr.read_headfile(zetafilename,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)   

#
#   Setup and process binary Cell by cell Budgets:
#
if options.conc:
    concfile = path + "\\MT3D001.UCN"
    print "....attempting to process MT3D binary file"

    if not os.path.exists(concfile):
        print "Modflow Concentration file does not exist"
        exit(1)
    else:
        print "Modflow Concentration file exists"

    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    SR = modelSR[options.model]

    mfr.read_concfile(concfile,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2)
    
if options.uzfcbc:
    uzfFilename = mfr.get_filename(path + "\\" + namfile, 'UZF')
    uzfFilename_full = path + "\\" + uzfFilename
    
    uzfUnit = mfr.get_unitnumber(uzfFilename_full,1,6)
    
    print "CellxCell Flow file unit number %i" % int(uzfUnit)
    uzfcbcfilename = mfr.get_filebyNumber(path + "\\" + namfile, 
                                      uzfUnit)
    uzfcbcfilename = path + "\\" + uzfcbcfilename
    print "CellxCell Flow filename " + uzfcbcfilename
    llorigin = modelOrigins[options.model]
    SR = modelSR[options.model]

    mfr.read_cbcfile(uzfcbcfilename,disdf,options.layerStr,options.stressStr,llorigin,SR)

#
#   Setup and process binary LPF Cell by cell Budgets:
#

      
if options.cbc:
    form = 'BINARY'
    cbcFilename = mfr.get_filename(path + "\\" + namfile, 'LPF')
    if cbcFilename.strip() == "":
        cbcFilename = mfr.get_filename(path + "\\" + namfile, 'BCF')
        form='UF'
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,1)
    if int(cbcUnit) == 0:
        cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,2)    
    print "CellxCell Flow file unit number %i" % int(cbcUnit)
    cbcfilename = mfr.get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print "CellxCell Flow filename " + cbcfilename
    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    SR = modelSR[options.model]

    multiplier = options.multiplier
    mfr.read_cbcfile(cbcfilename,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2,options.terms,form,multiplier)
    
if options.resample:
    cellsize = options.resample
else:
    cellsize = '1'
    
if options.vector:
    cbcFilename = mfr.get_filename(path + "\\" + namfile, 'LPF')
    print "LPF filename unit" + cbcFilename
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,1)
    print "CellxCell Flow file unit number %i" % int(cbcUnit)
    cbcfilename = mfr.get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print "CellxCell Flow filename " + cbcfilename
    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    SR = modelSR[options.model]

    multiplier = options.multiplier
  
    if options.terms <> 'RIGHT|FRONT':
      VectorTerms = 'RIGHT|FRONT'
      print "Overriding terms option for flow vectors:"
      print "  required terms are -- 'RIGHT|FRONT'"
      print "  indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE "
    mfr.read_cbcVectors(cbcfilename,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2,VectorTerms,cellsize,form,multiplier)
    clearINMEM()
    arcpy.CheckInExtension("Spatial")
if options.vectorbcf:
    cbcFilename = mfr.get_filename(path + "\\" + namfile, 'BCF6')
    if cbcFilename.strip() == "":
        cbcFilename = mfr.get_filename(path + "\\" + namfile, 'BCF')
        form='UF'
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,1)
    if int(cbcUnit) == 0:
        cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,2)
    print "CellxCell Flow file unit number %i" % int(cbcUnit)
    cbcfilename = mfr.get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print "CellxCell Flow filename " + cbcfilename
    llorigin = modelOrigins[options.model]
    defClip = modelClips[options.model]
    SR = modelSR[options.model]

    multiplier = options.multiplier
    
    if options.terms <> 'RIGHT|FRONT':
      VectorTerms = 'RIGHT|FRONT'
      print "Overriding terms option for flow vectors:"
      print "  required terms are -- 'RIGHT|FRONT'"
      print "  indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE "
    mfr.read_cbcVectors(cbcfilename,disdf,options.layerStr,options.stressStr,llorigin,SR,ClipRectangle,defClip,ws1,ws2,VectorTerms,cellsize,form,multiplier)
    clearINMEM()
    arcpy.CheckInExtension("Spatial")    
print "...finished"

