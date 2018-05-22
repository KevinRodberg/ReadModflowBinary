"""
..module:: ReadBinary
    :platform: Windows
    :synopsis: Command line option/argument interface to ModflowRasters module
    ::create: 13-Sep-2013
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""

import time
import csv
import numpy
import os
import arcpy
import struct
import sys

from ModflowRasters import get_headvalue, get_cbcvalue, get_uzfcbcvalue
from ModflowRasters import get_unitnumber
from ModflowRasters import get_filebyNumber,get_filename, get_dis_df
from ModflowRasters import numpytoras, read_headfile, read_cbcfile
from optparse import OptionParser

import Tkinter
import tkFileDialog as tkD

def getOptions():
    """Return command line arguments and options.

    -h,           --help               Show help message and exit
    -b,           --binheads           Read binary heads file
    -c,           --budgets            Read binary flow budgets
    -u,           --uzfbudgets         Read binary uzf flow budgets
    -l LOCATION,  --location=LOCATION  Define location ['SAN','NAS']
    -n NAMEFILE,  --namfile=NAMEFILE   Assign .NAM FILE
    -g GEODB,     --geodatabase=GEODB  Saves rasters in  GeoDatabase
    -t STRESS,  --stress=STRESS  Process one stress period
    -r RASTERS,   --rasters=RASTERS    Output layer (1,2,3,4,5,6,7)
                                            or   0 for no rasters
                                  or   Omit option for all layers

    Example arguments and brief description:
    
     -g ECFMdebugging.gdb -l SAN
     -n \\WHQBLD01P\fdrive\wsmod2\ECFM\ECFM_models\transient /
          \SEAWAT_Month\ECFMFPL\ecfm_tr.nam /
                                           -r 1 -b -s 15
                                           
     -g ECFMper.gdb -l SAN -n ecfm_tr.nam  -r 1 -b -s 13
        ^              ^      ^               ^  ^    ^
        |              |      |               |  |    | Output
        `-geo-dabase   |      |               |  |    `-period = 138
                       |      `-Namefile      |  `-Read Binary Heads
                       `-Model file location  `-Output  layer = 1

    """
    usage = "usage: %(prog) [options] args"

    parser = OptionParser(usage)
    parser.add_option("-b", "--binheads",
                      action="store_true",
                      dest="heads",
                      help="Process binary heads file.")
    parser.add_option("-c", "--budgets",
                      action="store_true",
                      dest="cbc",
                      help="Process binary cellbycell budgets.")    
    parser.add_option("-u", "--uzfbudgets",
                      action="store_true",
                      dest="uzfcbc",
                      help="Process binary uzf cellbycell budgets.")
    parser.add_option("-l", "--location",
                      dest="location",
                      choices=['SAN','NAS'],
                      help="Define data file location['SAN','NAS'].")
    parser.add_option("-n", "--namfile",
                      dest="namefile",
                      help="Assign .NAM FILE")
    parser.add_option("-g", "--geodatabase",
                      dest="geodb",
                      default = 'Default.gdb',
                      help="Save rasters in GeoDatabase.")
    parser.add_option("-s","--stress",
                      type="int",
                      dest="stress",
                      help="Process a single stress period.")
    parser.add_option("-r", "--rasters",
                      dest="rasters",
                      choices=['0','1','2','3','4','5','6','7'],
                      type = 'choice',
                      default ='0',
                      help="Create Rasters for         \
                            one layer (1,2,3,4,5,6,7)  \
                            or 0 for no rasters.       \
                            Omit option for all layers")
    (options, args) = parser.parse_args()
    
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    return options

def define_workspace(options):
    """Set base paths for Modflow namefile and ESRI workspace. """
    if options.geodb == None:
        out_folder_path = "H:\\Documents\\ArcGIS"
        out_name = "Default.gdb"
    else:
        out_folder_path = tkD.askdirectory(initialdir=
                                            "H:\\Documents\\ArcGIS")
        choosefile = tkD.askopenfilename(initialdir=out_folder_path,
                                filetypes=[('ESRI geodatabase files','.gdb'),
                                           ('all files', '.*')
                                           ])
        (out_folder_path, gdbfile) = os.path.split(choosefile)
        out_name = options.geodb

    arcpy.env.workspace = out_folder_path+"\\"+out_name
      
    if not arcpy.Exists(arcpy.env.workspace):
        print "Workspace does not exist.  Creating New one!"
        arcpy.CreateFileGDB_management(out_folder_path, out_name)
        
    print "output will be written to:" + arcpy.env.workspace 
     
    arcpy.env.overwriteOutput = True
    return

def define_disfile():
    disFilename = get_filename(path + "\\" + namfile, 'DIS')
    disFilename_full = path + "\\" + disFilename
    disdf = get_dis_df(disFilename_full)
    return disdf

#--------------------------------------------------------------------
#
#   Let the processing Begin..............
# 
#--------------------------------------------------------------------

options = getOptions()
option_dict = vars(options)

print option_dict
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
    path = tkD.askdirectory(initialdir= 
         '\\\\ad.sfwmd.gov\\dfsroot\\data\wsd\\')
    root.destroy()
elif options.location == 'SAN':
    path = tkD.askdirectory(initialdir= 
         '\\\\WHQBLD01P\\fdrive\\Wsmod2\\ECFM\\ecfm_models\\transient\\SEAWAT_month\\')
elif options.namefile is not None:
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
    sys.exit(1)
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

#    
#   Setup and process binary Heads file:
#

if options.heads:
    ocFilename = get_filename(path + "\\" + namfile, 'OC')
    ocFilename_full = path + "\\" + ocFilename
    print ocFilename

    HeadsUnit = get_unitnumber(ocFilename_full,1,0)
    print "Heads file unit number %i" % int(HeadsUnit)
    headsfile = get_filebyNumber(path + "\\" + namfile,HeadsUnit)

    headsfile = path + "\\" + headsfile
    print "....attempting to process .heads binary file"
 
    read_headfile(headsfile,disdf,options.rasters,options.stress)

#
#   Setup and process binary Cell by cell Budgets:
#

if options.uzfcbc:
    uzfsfilename = get_filename(path + "\\" + namfile, 'UZF')
    uzfFilename_full = path + "\\" + uzfFilename
    uzfcbcvalue = get_uzfcbcvalue(uzfFilename_full)
    print "CellxCell Flow file unit number %i" % int(uzfcbcvalue)
    uzfcbcfilename = get_filebyNumber(path + "\\" + namfile, 
                                      uzfcbcvalue)
    uzfcbcfilename = path + "\\" + uzfcbcfilename
    print "CellxCell Flow filename " + uzfcbcfilename
    read_cbcfile(uzfcbcfilename,disdf,options.rasters)

#
#   Setup and process binary UZF Cell by cell Budgets:
#

if options.cbc:
    cbcFilename = get_filename(path + "\\" + namfile, 'LPF')
    cbcFilename_full = path + "\\" + cbcFilename
    cbcvalue = get_cbcvalue(cbcFilename_full)
    print "CellxCell Flow file unit number %i" % int(cbcvalue)
    cbcfilename = get_filebyNumber(path + "\\" + namfile, cbcvalue)
    cbcfilename = path + "\\" + cbcfilename
    print "CellxCell Flow filename " + cbcfilename
    read_cbcfile(cbcfilename,disdf,options.rasters)
 
print "...finished"









