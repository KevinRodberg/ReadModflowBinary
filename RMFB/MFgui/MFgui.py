"""
..module::MFgui
  ::synopsis: ReadModflowBinaryV2.py uses: import MFgui.MFgui as MFgui
  :
  :	-gui  optional argument provided to ReadModflowBinary invokes use of
  :	      functions defined in this module
  :
  ::created: 10-23-2019
  :
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
import os
import sys
import easygui as ez
import RMFB.MFbinary.MFbinaryData as mf
if sys.version_info[0] == 3:
    # for Python3
    from tkinter import Tk   ## notice lowercase 't' in tkinter here
else:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter

def guiTorFOptions(justOptions,optArgs,argHelp,prog):
#
#   GUI choices for Modflow Binary processing options
#
  boolStr=('_','X')
  title ="{}.py Produces ArcGIS Rasters and Features".format(prog)
  introMsg = """
  {}.py is command line driven
  or it can be ran with this GUI

  Choose binary options:""".format(prog)
  preselected = 0
  while True:
    ##-- Really long assignment statement
    userOptions = ["{0:<1} {1:<8} {2:<20}"\
                 .format(boolStr[optArgs[value[2]]],
                         label,' '.join(value[1].split()))
      for label, value in sorted(justOptions.items())]
    ##-- End of Really long assignment statement

    reply = ez.choicebox(msg=introMsg,title=title,
               choices=userOptions,preselect=preselected)
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

def guiModel(optArgs,argHelp,prog):
#
#   GUI selection of Model from available choices
#   if not provided on cmd line
#
  title ="{}.py Produces ArcGIS Rasters and Features".format(prog)

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

def guiArgVals(justArgs,optArgs,argHelp,prog):
#
#   GUI value definitions of optional arguments such as:
#       agg, lay, strPer, res, terms
#   arguments needing path or filenames excluded:
#       ras, gdb, clpgdb, clpbox
#
  title ="Read ",prog," Rasters and Features from Modflow Binary"

  introMsg = """
  {}.py is command line driven
      or it can be ran with this GUI
          Provide arguments for these options:""".format(prog)
  while True:
    ##-- Really long assignment statement
    userOptions =["{!s:<10} {!s:<15} {!s:>20} "\
                        .format(label,optArgs[value[2]],
                                ' '.join(value[1].split()) )
      for label, value in sorted(justArgs.items())]
    ##-- End of Really long assignment statement

    reply = ez.choicebox(msg=introMsg,title=title,
              choices=userOptions)
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
        and k not in('nam','ras','mod','gdb','clpgdb','clpBox','ListOf2','rasterName')]
  return(NoneVals)

def guiMFterms(MFbudTerms,optArgs):
#
#   GUI choices for Modflow Binary processing options
#
  title ="Budget Term selection"
  introMsg = "Choose Modflow Binary CellxCell Budget Terms"

  while True:
    reply = ez.multchoicebox(msg=introMsg, title=title, choices = MFbudTerms)
    if reply: break
  return(reply)

def guiGeoVals(wkspcArgs,optArgs,argHelp,prog):
#
#   GUI argument value definitions of arguments needing path or filenames
#   for Spatial stuff like geodatabase or points:
#       ras, gdb, clpgdb, clpbox
#
  title ="{}.py workspaces".format(prog)

  introMsg = """
  {}.py is command line driven
  or it can be ran with this GUI

  Provide arguments for these options:""".format(prog)
  selectWrkSpc = r'H:\\Documents\\ArcGIS'
  while True:
    #--- Really long assignment statement
    userOptions =["{!s:<10} {!s:<15} {!s:>20} "\
                        .format(l,optArgs[v[2]],' '.join(v[1].split()) )
      for l, v in sorted(wkspcArgs.items())]
    #--- End of Really long assignment statement
    reply = ez.choicebox(msg=introMsg,title=title,choices=userOptions)
    try:
      selected = reply.split(" ")
      argValsMsg= "{}".format(argHelp[selected[0]][1])
      while True:
        dirName=ez.diropenbox(msg='Navigate to '+selected[0]+' directory',
                    title='Workspace',
                    default=selectWrkSpc)
        if dirName:
          break
      if not dirName:
        break
      if selected[0] != 'ras' and not optArgs['noArc']:
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
        print('raster Directory selection for ',selected[0])
        selectWrkSpc = os.path.join(dirName,gdbName)
        print(selectWrkSpc)
      #print(selected[0])
      #print(argHelp[selected[0]][2])
      optArgs[argHelp[selected[0]][2]]= selectWrkSpc
      #print(optArgs[argHelp[selected[0]][2]])

    except:
      #print ("Multiple Argument definition complete")
      pass
    if not reply:
      break
  #print('All wkspArgs',[(k,v[2],optArgs[v[2]]) for k, v in wkspcArgs.items()])

  DefaultVals = [k for k,v in sorted(wkspcArgs.items()) \
                 if v[1] is None or 'Default' in v[1] ]

  #print('Default vals:',DefaultVals)
  return(DefaultVals)

def guiGetFilename(getFileArgs,optArgs,argHelp,prog):
      title ="File selection"
      introMsg = """
      {}.py is command line driven
      or it can be ran with this GUI
      Provide filenames for these options:""".format(prog)
      while True:
        #--- Really long assignment statement
        userOptions =["{!s:<10} {!s:<15} {!s:>20} "\
                            .format(l,optArgs[v[2]],' '.join(v[1].split()) )
          for l, v in sorted(getFileArgs.items())]
        #--- End of Really long assignment statement
        reply = ez.choicebox(msg=introMsg,title=title,choices=userOptions)
        Key = None
        if reply is not None:   Key = reply.split(" ")[0]
        namMsg = """
        Please locate and select a file
        which will properly identify the results to process"""
        #print('optArgs',optArgs)
        if optArgs['BGDB']:
            (Bpath, namfile) = os.path.split(optArgs['BGDB'])
        else:
            Bpath = 'H:\\'
        reply = None
        while True and Key is not None:
#          print('argHelp key', Key)
#          print('argHelp items for select key', argHelp[Key])
#          print('optArgs key from argHelp', argHelp[Key][2])
#          print('optArgs value for selected key', optArgs[argHelp[Key][2]])
          if optArgs[argHelp[Key][2]] is None :
            ftypes = ["*.*", ["*.shp","*.tif"]]
            reply = ez.fileopenbox(msg=namMsg,
                                   title=title,
                                   default=Bpath+'\*',
                                   filetypes=ftypes)
            optArgs[argHelp[Key][2]] =reply
#            print('1stAssingment:',optArgs[argHelp[Key][2]])
            FileListLen = len(optArgs[argHelp[Key][2]].split())
#            print('before else',FileListLen)
          else:
            FileListLen = len(optArgs[argHelp[Key][2]].split())
#            print('else',FileListLen,argHelp[Key][2] )
            if FileListLen == 1 and argHelp[Key][2] =='ListOf2':
                (Bpath, namfile) = os.path.split(reply)
                ftypes = ["*.*", ["*.shp","*.tif"]]
                reply2 = ez.fileopenbox(msg=namMsg,
                                    title=title,
                                    default=Bpath+'\*',
                                    filetypes=ftypes)
                optArgs[argHelp[Key][2]] += ' ' +reply2
                FileListLen = len(optArgs[argHelp[Key][2]].split())
          if FileListLen > 1 or argHelp[Key][2] == 'rasterName':
              break
        #print('While loop complete')
        if not reply:
            #print('Breaking after While Loop')
            break
#      print('Attemp assignment of FileVals')
      FileVals = [k for k, v in \
                     sorted(argHelp.items()) if v[0] =='getFile' \
                     and v[3] and ('Default' in v[3]
                     or '0,0,0,0' in optArgs[v[2]])
                     and k in getFileArgs]
#      print('File vals:',FileVals)
      return(FileVals)


def guiArgs(optArgs,argHelp,prog='ReadModflowBinary'):
  global CBCbytesPer
#
#   Begin processing using GUI interface
#   when -gui option provided on Command Line
#
  justOptions ={k: v for k, v in sorted(argHelp.items()) if v[0] =='option' and k not in ('uzf')}
  justArgs    ={k: v for k, v in argHelp.items() if v[0]  in ('getArg')}
  wkspcArgs   ={k: v for k, v in argHelp.items() if v[0] =='getWkspc'}
  getFileArgs ={k: v for k, v in argHelp.items() if v[0] in ('getFile','get2Arg') and k not in ['clpbox']}

  #   select Binary data options
  TrueOptions = guiTorFOptions(justOptions,optArgs,argHelp,prog)
  while not TrueOptions and prog=='ReadModflowBinary':
      TrueOptions =guiTorFOptions(justOptions,optArgs,argHelp)

  #  Choose from an existing model definition
  if prog=='ReadModflowBinary':
      SelectedModel = guiModel(optArgs,argHelp,prog)
      print("Model has been selected as: {}".format(SelectedModel))

  #  Identify Arguments which are still = None
  NoneVals=[]
  if len(justArgs.keys())> 0:
      #print('justArgs used to call guiArgVals',justArgs.keys())
      NoneVals = guiArgVals(justArgs,optArgs,argHelp,prog)
      #print('NoneVals',NoneVals)
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
        secondPass =guiArgVals(oneDict,optArgs,argHelp,prog)
    else:
  #
  #   If terms = None all CellxCell budget term rasters will be
  #   produced for the layers and stressperiods defined
  #
      if 'bud' in TrueOptions:
          (path, namfile) = os.path.split(optArgs['namefile'])
          CBCbytesPer = 0
          print('before cbcTerms',CBCbytesPer)
          terms = mf.readCBCterms(path, namfile,optArgs)
          
          if 'terms' in NoneVals:
            terms = guiMFterms(terms,optArgs)
            optArgs['terms']= terms

            
          print('after cbcTerms',CBCbytesPer)          
          
  #
  #  Identify Arguments which are still = Default or 0,0,0,0
  #
  if optArgs['noArc']:
      wkspcArgs   ={k: v for k, v in argHelp.items() if (v[0] =='getWkspc' and 'Geo' not in v[1]) }
      # print('selected from wkspcArgs ',wkspcArgs.values())
  DefaultVals = guiGeoVals(wkspcArgs,optArgs,argHelp,prog)
  if len(DefaultVals) > 0:
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

  print('justArgs used to call getFileArgs',getFileArgs.keys())
  if len(getFileArgs.keys())> 0 :
      FileVals = guiGetFilename(getFileArgs,optArgs,argHelp,prog)
      print('Finished getting Filenames',FileVals)
  return
