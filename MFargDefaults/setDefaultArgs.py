"""
..module::setDefaultArgs
  :
  :synopsis: Read Modflow Binary uses: import defStuff.setDefaultArgs as defs
  ::created: 10-23-2019
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
def setDefaultArgs():
  model_choices =['C4CDC','ECFM','ECFT','ECFTX','LECSR','NPALM','LKBGWM','LWCFAS','LWCSAS','LWCSIM','WCFM']
  function_choices=['min','max','mean']
#
#   Define dictionary of arguments to use in ArgumentParser
#    
  resampleHelp="""\
    Resampling only aggregates horizontal flow vector results
      -Flow Magnitudes are summed
      -Flow Direction is averaged
      --------------------------
      -res 5 Aggregates 5x5 grid
      -res 1 Default or no resampling:[1x1]
      """
  aggregateHelp="""\
    Aggregate multiple rasters into a single raster
     usings one of the predefined functions
     {0} """.format( function_choices)
      
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
    'noArcGIS':
    ['option',"Process binary files without using ArcGIS",'noArc'],
    'quiet':
    ['option',"Reduce output to console",'quiet'],
    'gui':
    ['option',"GUI for options & arguments",'gui'],
    'hds':
    ['option',"Process Heads file.",'heads'],
    'swi':
    ['option',"Process SWI Zetas file.",'zeta'],
    'res':
    ['getArg',resampleHelp,'resample','1'],
    'agg':
    ['getArg',aggregateHelp,'aggregate',None,function_choices],
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
    'ras':
    ['getArg',"Save rasters in folder.",'rasFolder',
     r'H:\Documents\ArcGIS'],
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
  import argparse
  import textwrap

#
#   Loop through argHelp dictionary to add arguments to ArgumentParser
#
  parser = argparse.ArgumentParser(usage=argparse.SUPPRESS,prog='ReadModflowBinary',
          formatter_class=argparse.RawTextHelpFormatter)

  argHelp=setDefaultArgs()
#  for label, value in sorted(argHelp.iteritems()):
  for label, value in sorted(argHelp.items()):
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
  try:
      args = parser.parse_args()
  except:
      print('--- End of Usage Description --- ')
  return args,argHelp


  