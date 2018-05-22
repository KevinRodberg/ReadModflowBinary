"""
..module:: ReadBinary
    :platform: Windows
    :synopsis: Command line option/argument interface to ModflowRasters module
    :notes: Added to subVersion Repository 
    ::create: 13-Sep-2013
    ::modified: October 30, 2013
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""

import time
import csv
import numpy
import os
import arcpy
import struct
import sys
import ModflowBinaryCBCRasters as mfr



#from ModflowRasters import get_unitnumber
#from ModflowRasters import get_filebyNumber,get_filename, get_dis_df
#from ModflowRasters import numpytoras, read_headfile, read_cbcfile

from argparse import ArgumentParser

import Tkinter
import tkFileDialog as tkD

def getOptions(model_choices):
    """Return command line arguments and options.

    -h,           --help               Show help message and exit
    -bin,         --binheads           Read binary heads file
    -bud,         --budgets            Read binary flow budgets
    -con,         --ceoncentrations    Read binary MT3D file
    -uzf,         --uzfbudgets         Read binary uzf flow budgets
    -mod,         --modelname          Model acronym ['ECFM', 'ECFT']
                                       Used to define Lower Left Origin
    -l LOCATION,  --location=LOCATION  Define location ['SAN','NAS']
    -n NAMEFILE,  --namfile=NAMEFILE   Assign .NAM FILE
    -g GEODB,     --geodatabase=GEODB  Saves rasters in  GeoDatabase
    -t STRESS,  --stress=STRESS  Process one stress period
    -r RASTERS,   --rasters=RASTERS    Output layer (1,2,3,4,5,6,7)
                                            or   0 for no rasters
                                  or   Omit option for all layers

    Example arguments and brief description:
    
     -g ECFMdebugging.gdb -l SAN
     -nam \\WHQBLD01P\fdrive\wsmod2\ECFM\ECFM_models\transient\SEAWAT_Month\ECFMFPL\ecfm_tr.nam
         
                                           -r 1 -b -s 15
                                           
     -g ECFMper.gdb -loc SAN -r 1 -bin -s 13
        ^              ^      ^    ^     ^
        |              |      |    |     | Output
        `-geo-dabase   |      |    |     `-period = 138
                       |      |    `-Read Binary Heads
   Model file location /      `-Output  layer = 1

    """


    parser = ArgumentParser(prog='ReadBinary')
    parser.add_argument("-bin", "--binheads",
                      action="store_true",
                      dest="heads",
                      help="Process binary heads file.")
    parser.add_argument("-con", "--concentrations",
                      action="store_true",
                      dest="conc",
                      help="Process binary MT3D file.")
    parser.add_argument("-bud", "--budgets",
                      action="store_true",
                      dest="cbc",
                      help="Process binary cellbycell budgets.")    
    parser.add_argument("-uzf", "--uzfbudgets",
                      action="store_true",
                      dest="uzfcbc",
                      help="Process binary uzf cellbycell budgets.")
    parser.add_argument("-mod", 
                      dest="model",
                      choices=model_choices,
                      default='ECFM',
                      help="Model defines Raster Lower Left Origin")
    parser.add_argument("-loc", 
                      dest="location",
                      choices=['SAN','NAS'],
                      help="Define data file location['SAN','NAS'].")
    parser.add_argument("-nam", "--namfile",
                      dest="namefile",
                      help="Assign .NAM FILE")
    parser.add_argument("-geo", "--geodatabase", dest="geodb",
                      default = 'Default.gdb',
                      help="Save rasters in GeoDatabase.")
    parser.add_argument("-str","--stress",
                        type=int,
                        dest="stress",
                        help="Process a single stress period.")
    parser.add_argument("-lay", "--layers",
                        dest="layerStr",
                        type=str,
                        help="Create Rasters for         \
                            a single layer or   \
                            multiple layers '1,3-4,7'.    \
                            --Use 0 for no rasters.       \
                            --Omit option for all layers"
                        )
    """    parser.add_argument("-r", "--rasters",
                      dest="rasters",
                      choices=['0','1','2','3','4','5','6','7'],
                      default ='0',
                      help="Create Rasters for         \
                            one layer (1,2,3,4,5,6,7)  \
                            or 0 for no rasters.       \
                            Omit option for all layers")
    """
    args = parser.parse_args()
    print args
 
    return args

def setModelOrigins():
  global modelOrigins
  modelOrigins = dict(C4CDC=arcpy.Point(763329.000,437766.000),
                    ECFM=arcpy.Point(565465.000,-44448.000),
                    ECFT=arcpy.Point(330706.031,1146903.250),
                    LECSR=arcpy.Point(680961.000,318790.000),
                    LKBGWM=arcpy.Point(444435.531,903882.063),
                    LWCFAS=arcpy.Point(438900.000,-80164.000),
                    LWCSAS=arcpy.Point(292353.000,456228.000)
                    )
  model_choices= list(key for key,val in modelOrigins.iteritems())
  return model_choices

def define_workspace(options):
    """Set base paths for Modflow namefile and ESRI workspace. """
    out_folder_path = "H:\\Documents\\ArcGIS"
    if options.geodb == "Default.gdb":
        out_name = "Default.gdb"
    elif options.geodb <> None:
        
        (temp_path, gdbfile) = os.path.split(options.geodb)
        print "geodatabase path defined as" + out_folder_path
        if temp_path == "":
            out_folder_path = tkD.askdirectory(title=out_folder_path,
                                           initialdir = out_folder_path)
        else:
            out_folder_path = temp_path

        print 'output path is:' + out_folder_path
        print 'Geodb:' + options.geodb
        out_name = options.geodb        
    else:
        print "current working path " + path
        out_folder_path = tkD.askdirectory(title='Identify directory Geodatabase',
                                           initialdir = path)

        (out_folder_path, gdbfile) = os.path.split(out_folder_path)
        print 'output path:' + out_folder_path
        print 'Geodb:' + gdbfile
        out_name = gdbfile

    workspace = os.path.join(out_folder_path, gdbfile)
    print workspace


    print "does workspace exist"
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
    

    return

def define_disfile():
    disFilename = mfr.get_filename(path + "\\" + namfile, 'DIS')
    disFilename_full = path + "\\" + disFilename
    print disFilename
    disdf = mfr.get_dis_df(disFilename_full)
    return disdf

#--------------------------------------------------------------------
#
#   Let the processing Begin..............
# 
#--------------------------------------------------------------------

model_choices = setModelOrigins()

options = getOptions(model_choices)
print options.model
option_dict = vars(options)


for k in option_dict.iteritems():
    label, value = k
    print "{:<15} {:<10}".format(label, value)

"""Define Location of Model files

   NAS and SAN options provide 2 base path
   entry points for the file browser.
   
   An explicit path included with the namefile option
   will override the LOCATION path browser selection.

   If location option is provided a sample directory
   has been provided.

   If neither a NAM file or LOCATION option are
   provide a usage statement is printed and
   execution is terminated.
   
"""
root = Tkinter.Tk()
root.withdraw()

                    
if options.location == 'NAS':
    path = '\\\\ad.sfwmd.gov\\dfsroot\\data\wsd\\'
elif options.location == 'SAN':
    path = '\\\\WHQBLD01P\\fdrive\\Wsmod2\\ECFM\\ecfm_models\\transient\\SEAWAT_month\\'
elif options.namefile:
    (path, namfile) = os.path.split(options.namefile)
    if path == '':
        print 'Explicit path missing.  '
        print 'Using default path for testing'
        path = '\\\\WHQBLD01P\\fdrive\\wsmod2\\ECFM\\ECFM_models\\transient\\SEAWAT_Month\\ECFMPER'
else:
    print "Unable to process Binary data without file location details."
    print "usage: %(prog)s [options] arg"
    print "    -l LOCATION,  --location=LOCATION  Assign data location ['SAN','NAS']"
    print "    -n NAMEFILE,  --namfile=NAMEFILE   Read data from .NAM FILE"
    path = tkD.askdirectory(initialdir='H:\\')

print path
"""Define Modflow NAM file 

   If namefile selection includes an explicit path or
   directory of file is changed in file browser
   when LOCATION option is present the explicit path
   will override the LOCATION path browser selection.
"""

if options.namefile:
    (nampath, namfile) = os.path.split(options.namefile)

else:
    print path
    choosefile = tkD.askopenfilename(initialdir=path,
                                filetypes=[('all files', '.*'),
                                           ('Modflow NAM files',
                                                          '.nam')])
    (nampath, namfile) = os.path.split(choosefile)

if nampath > '' and nampath <> path:
    print 'Using:' + nampath
    print 'Overriding' + path
    print "Path changed or Explicit path in namfile overrides location argument"
    path = nampath
    
print nampath    
print namfile

define_workspace(options)
disdf = define_disfile()
print disdf

#    
#   Setup and process binary Heads file:
#

if options.heads:
    ocFilename = mfr.get_filename(path + "\\" + namfile, 'OC')
    ocFilename_full = path + "\\" + ocFilename
    print ocFilename
    if (options.model == 'ECFM'):
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,0)
    elif (options.model == 'C4CDC'):
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,3)
    else:
       HeadsUnit = mfr.get_unitnumber(ocFilename_full,1,0)
       
    print "Heads file unit number %i" % int(HeadsUnit)
    headsfile = mfr.get_filebyNumber(path + "\\" + namfile,HeadsUnit)

    headsfile = path + "\\" + headsfile
    print "....attempting to process heads binary file"
    print headsfile
    llorigin = modelOrigins[options.model]
    mfr.read_headfile(headsfile,disdf,options.layerStr,options.stress,llorigin)

#
#   Setup and process binary Cell by cell Budgets:
#
if options.conc:
    concfile = path + "\\MT3D001.UCN"
    print "....attempting to process MT3D binary file"

    if not os.path.exists(concfile):
        print "Concetration file does not exist"
        exit(1)
    else:
        print "Concetration file exists"

    llorigin = modelOrigins[options.model]
    mfr.read_concfile(concfile,disdf,options.layerStr,options.stress,llorigin)
    
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
    mfr.read_cbcfile(uzfcbcfilename,disdf,options.layerStr,options.stress,llorigin)

#
#   Setup and process binary UZF Cell by cell Budgets:
#

if options.cbc:
    cbcFilename = mfr.get_filename(path + "\\" + namfile, 'LPF')
    cbcFilename_full = path + "\\" + cbcFilename
    cbcUnit = mfr.get_unitnumber(cbcFilename_full,1,1)
    print "CellxCell Flow file unit number %i" % int(cbcUnit)
    cbcfilename = mfr.get_filebyNumber(path + "\\" + namfile, cbcUnit)
    cbcfilename = path + "\\" + cbcfilename
    print "CellxCell Flow filename " + cbcfilename
    llorigin = modelOrigins[options.model]
    mfr.read_cbcfile(cbcfilename,disdf,options.layerStr,options.stress,llorigin)
 
print "...finished"









