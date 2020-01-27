"""
..module::MFgui
  ::synopsis: Read Modflow Binary uses: import guiStuff.setup_guiStuff as gui
  :  
  :	-gui  optional argument provided to ReadModflowBinary invokes use of 
  :	      functions defined in this module
  :
  ::created: 10-23-2019
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
import os
import sys
import easygui as ez
import MFbinary.MFbinaryData as mf
if sys.version_info[0] == 3:
    # for Python3
    from tkinter import *   ## notice lowercase 't' in tkinter here
else:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter

def guiBin(justOptions,optArgs,argHelp):
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
      for label, value in sorted(justOptions.items())]
    ##-- End of Really long assignment statement

    reply = ez.choicebox(msg=intro_message,title=title,
               choices=presented_choices,preselect=preselected) 
    try:
      selected = reply.split(" ")
      optArgs[argHelp[selected[1]][2]] \
                = not optArgs[argHelp[selected[1]][2]]
    except:
      TrueOptions = [k for k, v in \
          sorted(argHelp.items()) if v[0] =='option' and
               optArgs[v[2]] and k not in ('uzf','gui')]
    if not reply: break
  return(TrueOptions)

def guiModel(optArgs,argHelp):
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
      #for k, v in argHelp.iteritems():
      for k, v in argHelp.items():
        if v[2] == 'model':
          modelChoices =sorted(v[4])
      reply=ez.choicebox(msg=modelMsg,title=title,choices=modelChoices)
    else:  break
    if reply: break
  try:
    selected = reply
    if reply: optArgs['model'] = selected
  except:
    pass
  return (optArgs['model'])

def guiArgVals(justArgs,optArgs,argHelp):
#
#   GUI value definitions of optional arguments such as:
#       agg, lay, strPer, res, terms
#   arguments needing path or filenames excluded:
#       ras, gdb, clpgdb, clpbox
#
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"

  intro_message = """
  ReadModflowBinary.py is command line driven
      or it can be ran with this GUI
          Provide arguments for these options:"""
  
  while True:
    ##-- Really long assignment statement      
    presented_choices =["{!s:<10} {!s:<15} {!s:>20} "\
                        .format(label,optArgs[value[2]],
                                ' '.join(value[1].split()) )
      for label, value in sorted(justArgs.items())]
    ##-- End of Really long assignment statement
      
    reply = ez.choicebox(msg=intro_message,title=title,
              choices=presented_choices)
    try:
      selected = reply.split(" ")
      argValsMsg= "{}".format(argHelp[selected[0]][1])
      while True:
        reply = ez.enterbox(msg = argValsMsg)
        if reply: break
      if ('-'+selected[0]) in reply:
          reply = reply.strip('-'+selected[0])
      optArgs[argHelp[selected[0]][2]]= reply
    except:
      pass
    if not reply: break
    
  NoneVals = [k for k, v in \
    sorted(argHelp.items()) if v[0] !='option' and not optArgs[v[2]]
        and k not in('nam','ras','mod','gdb','clpgdb','clpBox')]    
  return(NoneVals)

def guiMFterms(MFbudTerms,optArgs):
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
    if reply: break
  return(reply)

def guiGeoVals(geoArgs,optArgs,argHelp):
#
#   GUI argument value definitions of arguments needing path or filenames
#   for Spatial stuff like geodatabase or points:
#       ras, gdb, clpgdb, clpbox
#
  title ="Read Modflow Binary Produces ArcGIS Rasters and Features"

  intro_message = """
  ReadModflowBinary.py is command line driven
  or it can be ran with this GUI

  Provide arguments for these options:"""
  while True:
    #--- Really long assignment statement      
    presented_choices =["{!s:<10} {!s:<15} {!s:>20} "\
                        .format(l,optArgs[v[2]],' '.join(v[1].split()) )
      for l, v in sorted(geoArgs.items())]
    #--- End of Really long assignment statement
    reply = ez.choicebox(msg=intro_message,title=title,
              choices=presented_choices)
    try:
      selected = reply.split(" ")
      print ("Select = {}".format(selected[0]))
      argValsMsg= "{}".format(argHelp[selected[0]][1])
      while True:
        dirName=ez.diropenbox(msg='Navigate to output directory',
                    title='ArcGIS Workspace',
                    default=os.path.dirname((optArgs['geodb'])))
        if dirName:
          break
      if not dirName:
        break
      if selected[0] != 'ras':
        if '.gdb' not in dirName:
          while True:
            gdbName = ez.enterbox(msg = 'geoDatabase Name for '+argValsMsg)
            if gdbName:
              if '.gdb' not in gdbName:
                gdbName = gdbName+'.gdb'
              else:
                pass
            break
      else:
        gdbName = ''
        print('ras Directory select:')
        print(os.path.join(dirName,gdbName))
      optArgs[argHelp[selected[0]][2]]= os.path.join(dirName,gdbName)

    except:
      print ("Multiple Argument definition complete")    
    if not reply:
      break
  DefaultVals = [k for k, v in \
    sorted(argHelp.items()) if v[0] !='option' \
        and optArgs[v[2]] and ('Default' in optArgs[v[2]]
        or '0,0,0,0' in optArgs[v[2]])
                 and k in('ras','gdb','clpgdb','clpBox')]    
  return(DefaultVals)

def guiArgs(optArgs,argHelp):
#
#   Begin processing using GUI interface
#   when -gui option provided on Command Line
#
  justOptions ={k: v for k, v in sorted(argHelp.items()) if v[0] =='option' and k not in ('uzf')}
  justArgs    ={k: v for k, v in argHelp.items() if v[0] !='option' and k not in('nam','mod','ras','gdb','clpgdb','clpBox')}
  geoArgs     ={k: v for k, v in argHelp.items() if v[0] !='option' and k in('ras','gdb','clpgdb','clpBox')}
  #   select Binary data options
  
  TrueOptions = guiBin(justOptions,optArgs,argHelp)
  while not TrueOptions:
      TrueOptions =guiBin(justOptions,optArgs,argHelp)
  
  #  Choose from an existing model definition
  SelectedModel = guiModel(optArgs,argHelp)
  SelectedFunction = guiModel(optArgs,argHelp)
  print("Model has been selected as: {}".format(SelectedModel))
  
  #  Identify Arguments which are still = None
  NoneVals = guiArgVals(justArgs,optArgs,argHelp)

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
        oneDict={k: v for k, v in argHelp.items()
             if v[0] !='option' and k ==arg}
        secondPass =guiArgVals(oneDict,optArgs,argHelp)
    else:
  #
  #   If terms = None all CellxCell budget term rasters will be
  #   produced for the layers and stressperiods defined
  #
      if 'terms' in NoneVals and 'bud' in TrueOptions:
          (path, namfile) = os.path.split(optArgs['namefile'])
          terms = mf.readCBCterms(path, namfile)
          terms = guiMFterms(terms,optArgs)
          optArgs['terms']= terms
  #
  #  Identify Arguments which are still = Default or 0,0,0,0
  #          
  DefaultVals = guiGeoVals(geoArgs,optArgs,argHelp)
  for arg in DefaultVals:
      text= "Default values for "+arg+"""
              ...  [Cancel] to provide value
              ...  [Continue] defaults to all """
      if ez.ccbox(msg=text,title="Please Confirm"):
        pass
      else:
        oneDict={k: v for k, v in argHelp.items()
             if v[0] !='option' and k ==arg}
        secondPass =guiGeoVals(oneDict,optArgs,argHelp) 
  return
