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


import argparse
import textwrap

global modelOrigins
global primaryWrkSpace
global clipWrkSpace

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
def setDefaultArgs():
    argHelp={'bud':    ['option',"Process binary cellbcell budgets",'cbc'],
             'gui':    ['option',"Interactive definition of options and arguments",'gui'],
             'hds':    ['option',"Process binary heads file.",'heads'],
             'swi':    ['option',"Process binary zetas file.",'zeta'],
             'res':    ['getArg',
                        """\
                Resampling appropriately aggregates values from model results
                -- Heads are averaged
                -- Flow Magnitudes are summed
                -- Flow Direction is averaged
                res=5 Aggregates 5x5 grid;
                default=no resampling:[1x1]""",'resample','1'],             
             'tds':    ['option',"Process binary TDS from MT3D file.",'conc'],
             'uzf':    ['option',"Process binary uzf cellbycell budgets.",'uzfcbc'],
             'vec':    ['option',"Process binary flow budgets for flow vectors",'vector'],
             'vecbcf': ['option',"Process binary BCF flow budgets for flow vectors",'vectorbcf'],
             'multi':  ['getArg',
                        """\
                Multiplier is applied to all Flow values by Stress Period
                -- multiplier=7.48 for gal/Stress Period;
                -- default=no conversion""",'multiplier','1.0'],
             'mod':    ['getArg',"""\
                Model defines Spatial Reference
                and Raster Lower Left Origin""",'model','WCFM',model_choices],
             'nam':    ['getArg',"Assign Modflow .NAM FILE",'namefile',None],
             'gdb':    ['getArg',"Save rasters in GeoDatabase.",'geodb','Default.gdb'],
             'clpext': ['getArg',"Clip rasters to extent.",'extShp','Default.shp'],
             'clpgdb': ['getArg',"Separate Geodatabase for Clipped Rasters",'clpgdb',None],
             'strPer': ['getArg',
                        """\
                Define Stress Periods to process:
                -- One stress period: '-strPer 218'  
                -- Multiple stress periods: '-strPer 1-12,218,288'
                -- Omit option [-strPer] for all layers
                -- Use '-strPer 0' for none (option testing)""",'stressStr',None],
             'lay':    ['getArg',
                        """\
                Define Layers to process:
                -- Single layer '-lay 1'
                -- Multiple layers '-lay 1,3-4,7'
                -- Use '-lay 0' for no rasters.
                -- Omit option [-lay] for all layers""",'layerStr',None],
             'terms':  ['getArg',
                        """\
                Process binary cellbycell budgets.
                -- 'FLOW' indicates processing Right, Front and Lower face flow
                -- 'RIGHT|FRONT' indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE
                --  No parameters indicates all budget terms""",'terms',None]
             }
    return argHelp
def getOptions():
    parser = argparse.ArgumentParser(prog='ReadModflowBinary',
                    formatter_class=argparse.RawTextHelpFormatter)
    argHelp=setDefaultArgs()
    for label, value in sorted(argHelp.iteritems()):
        parseArg = '-'+label
        if value[0] == 'option' :
#   True or False arguments mainly used to flag the types of binary data to process
#   parseArg == '-gui' invokes the qui tool to set/modify options
            parser.add_argument(parseArg,dest=argHelp[label][2],
                    action="store_true",
                    help=textwrap.dedent(argHelp[label][1]))
#   argHelp value lists for non=true/false arguments define destination variable as item 2
#   and item 3 provides default values
        elif len(argHelp[label]) <5:
            parser.add_argument(parseArg,dest=argHelp[label][2],
                    default=argHelp[label][3],
                    help=textwrap.dedent(argHelp[label][1]))
        else:
#   rgHelp value lists with 5 items provide a list for ArgumentParser.choices
            print (argHelp[label][4])
         #   print (str(argHelp[label][4]))
            parser.add_argument(parseArg,dest=argHelp[label][2],
                    default=argHelp[label][3],
                    choices=argHelp[label][4],
                    help=textwrap.dedent(argHelp[label][1]))

    args = parser.parse_args()
    return args

def guiArgs(options):
    msg = []
    msg.append("Pick the option that you wish to modify.")
    msg.append(" * Python version {}".format(sys.version))
    intro_message = "\n".join(msg)
    title = "ReadMFbinary_EasyGui " 
    # Table that relates keys in choicebox with functions to execute
    descriptions = options.list_descriptions()
    preselected = 0
    
options = getOptions()
print options
option_dict = vars(options)
print option_dict

for k in option_dict.iteritems():
    label, value = k
    print ("{:<15} {:>6}--- {:>6}".format(label, value,option_dict[label]))

