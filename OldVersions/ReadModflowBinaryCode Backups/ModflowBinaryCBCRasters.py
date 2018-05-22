"""
..module:: ModflowRasters
    :platform: Windows
    :synopsis: Create ESRI rasters geodatabase from Modflow binary output
    ::create: 13-Sep-2013
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""
import time
import numpy
import arcpy
from pandas import *
def parse_range(astr):
    result=set()
    if astr <> None:
        for part in astr.split(','):
            x=part.split('-')
            result.update(range(int(x[0]),int(x[-1])+1))
    return sorted(result)
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
                if line[0] <> 'HEAD' and row_num == 1 and item_num == 0:
                    row_num = 1
                    item_num = 4
      
    f.close()
    select_row = row[row_num-1]
    unitnum = select_row[item_num-1]            
    print row[0], item_num
    print "Unit identifier: %i " % int(unitnum)
    del row
    return unitnum

def get_filename(sourcefile,ftype_inits):
  
    binlist=[]
    header = ['Initials', 'unitnum', 'filename', 'status']
    binlist.append(header)
    print "SOURCEFILE" + sourcefile
    with open(sourcefile, 'r') as f:
        for line in f.readlines()[1:]:
            if (not line.startswith('#') ):
               if len(line) >1:
                 binlist.append(line.split()[0:4])
  #               print binlist
    f.close()
    
    df = DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
    print df
    newdf = df[df['Initials'] == ftype_inits]
    _unitnum = newdf['unitnum']
    _filename = newdf['filename']
    
    theval = str(_filename.values)
    outval = theval.lstrip("[") 
    outval = outval.rstrip("]")
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
    
    df = DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
    newdf = df[df['unitnum'] == fnumber]
    _unitnum = newdf['unitnum']
    _filename = newdf['filename']

    theval = str(_filename.values)
    outval = theval.lstrip("[") 
    outval = outval.rstrip("]")
    filename = outval

    del df, newdf, _unitnum, _filename
    return filename

def get_dis_df(file):
    row=[]
    print file
    with open(file, 'r') as f:
        for line in f.readlines(10):
  #          print line
            if not line.startswith('#'):
                row.append(line.split())
    f.close()

#   for i in range(0,10):
#     print i, row[i]
     
    datarow1 = row[0]
    datarow2 = row[2]
    datarow3 = row[3]

    layer = datarow1[0]
    nrows = datarow1[1]
    ncols = datarow1[2]
    nper = datarow1[3]
   
    chkstr= datarow2[1].find('(')
    if chkstr < 0:
        cellsize1 = datarow2[1]
    else:
        cellsize1 = datarow2[1][:chkstr]
    print cellsize1

    chkstr= datarow3[1].find('(')
    if chkstr < 0:
        cellsize2 = datarow3[1]
    else:
        cellsize2 = datarow3[1][:chkstr]
    print cellsize2
   
    retarr = []
    retarr.append(['layer', layer])
    retarr.append(['nrows',nrows])
    retarr.append(['ncols', ncols])
    retarr.append(['nperiod', nper])
    retarr.append(['cellsize1', cellsize1])
    retarr.append(['cellsize2', cellsize2])

    df = DataFrame(retarr, columns=['attribute', 'val'])

    del row, retarr
    return df
def numpytoras(inarr, df, rasname, llorig):
 
    dfval=[]
    dfattrib=[]
    for idx , record in df['attribute'].iteritems():
        dfval = df[df['attribute'] == record].val
        dfattrib = df[df['attribute'] == record].attribute
        if dfattrib[idx] == 'cellsize1':
            cellsz1 = float(dfval[idx])
        elif dfattrib[idx] == 'cellsize2':
            cellsz1 = float(dfval[idx])

    print "Saving Raster: " + rasname    
     #ras = arcpy.NumPyArrayToRaster(inarr, (565465,44448), 1250, 1250, -9999)

     #llorig = arcpy.Point(565465,-44448)
    ras = arcpy.NumPyArrayToRaster(inarr,llorig,cellsz1,cellsz1,999)

    ras.save(arcpy.env.workspace +"\\" + rasname)
    

    del inarr, ras  

def read_headfile(binfilename,df,buildRasters,timestep,llorigin):
    read_data=[]   
    headertypes= np.dtype([
      ("KSTP",   "<i4"),
      ("KPER",   "<i4"),
      ("PERTIM", "<f4"),
      ("TOTIM",  "<f4"),
      ("TEXT",   "S16"),
      ("NC",     "<i4"),
      ("NR",     "<i4"),
      ("K",      "<i4")])
    dfval=[]
    dfattrib=[]
    for idx , record in df['attribute'].iteritems():
        dfval = df[df['attribute'] == record].val
        dfattrib = df[df['attribute'] == record].attribute
        if dfattrib[idx] == 'layer':
            nlays = int(dfval[idx])
        elif dfattrib[idx] == 'nrows':
            nrows= int(dfval[idx])
        elif dfattrib[idx] == 'ncols':
            ncols = int(dfval[idx])
        elif dfattrib[idx] == 'nperiod':
            npers = int(dfval[idx])

   # shape = (472,388)
    knt= nrows*ncols
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)
    #print layerList
    binfile=open(binfilename,'rb')
    endOfTime = False
    for i in xrange(npers):
        for l in xrange(nlays):
            pad    = []
            pad    = numpy.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
            budget = pad["TEXT"][0].strip().replace(" ","_")
            kper   = pad["KPER"][0]
            k      = pad["K"][0]
            #print pad
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=knt, sep='').reshape(shape)
       
            rastername = "HEAD" + '{:7.5f}'.format(((kper)/100000.0)) + "_" + str(l+1)
            rastername = rastername.replace("0.","_")
            if layerList <> [0]:
                if k in layerList:
                    #  print "layerList" + str(layerList) +" " + str(timestep)
                    #  print timestep
                    if timestep == None or timestep == kper:
                        # print rastername
                        numpytoras(read_data, df, rastername,llorigin)
                    elif kper > timestep:
                        endOfTime = True
                        break
            if endOfTime:
                break
    binfile.close()
    del read_data, pad, headertypes
    
def read_concfile(binfilename,df,buildRasters,timestep,llorigin):
    read_data=[]   
    headertypes= np.dtype([
      ("KSTP",   "<i4"),
      ("KPER",   "<i4"),
      ("PERTIM", "<i4"),
      ("TOTIM",  "<f4"),
      ("TEXT",   "S16"),
      ("NC",     "<i4"),
      ("NR",     "<i4"),
      ("K",      "<i4")])
    dfval=[]
    dfattrib=[]
    for idx , record in df['attribute'].iteritems():
        dfval = df[df['attribute'] == record].val
        dfattrib = df[df['attribute'] == record].attribute
        if dfattrib[idx] == 'layer':
            nlays = int(dfval[idx])
        elif dfattrib[idx] == 'nrows':
            nrows= int(dfval[idx])
        elif dfattrib[idx] == 'ncols':
            ncols = int(dfval[idx])
        elif dfattrib[idx] == 'nperiod':
            npers = int(dfval[idx])

   # shape = (472,388)
    knt= nrows*ncols
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)

    binfile=open(binfilename,'rb')
    endOfTime = False
    for i in xrange(npers):
        for l in range(0,nlays):
            pad    = []
            pad    = numpy.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
            #print pad
            budget = pad["TEXT"][0].strip().replace(" ","_")
            totim   = pad["TOTIM"][0]
            k      = pad["K"][0]

            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=knt, sep='').reshape(shape)
       
            rastername = "CONC" + '{:7.5f}'.format(((totim)/100000.0)) + "_" + str(l+1)
            rastername = rastername.replace("0.","_")
            if layerList <> [0]:
                if not layerList or k in layerList:
                    #print "layerList" + str(layerList) +" " + str(timestep)
                    #print totim, timestep
                    
                    if timestep == None or timestep == totim:
                        #print rastername
                        numpytoras(read_data, df, rastername,llorigin)
                    if timestep <> None and totim > timestep:
                        endOfTime = True
                        print "EndofTime"
                        exit(0)
    binfile.close()
    del read_data, pad, headertypes    
def read_cbcfile(binfilename,df,buildRasters,timestep,llorigin):
    print "Reading CBC"
    dfval=[]
    dfattrib=[]
    for idx , record in df['attribute'].iteritems():
        dfval = df[df['attribute'] == record].val
        dfattrib = df[df['attribute'] == record].attribute
        #print dfattrib[idx], dfval[idx]
        if dfattrib[idx] == 'layer':
            nlays = int(dfval[idx])
        elif dfattrib[idx] == 'nrows':
            nrows = int(dfval[idx])
        elif dfattrib[idx] == 'ncols':
            ncols = int(dfval[idx])
        elif dfattrib[idx] == 'nperiod':
            npers = int(dfval[idx])
    #print nlays, nrows, ncols, npers
   
    read_data=[]   
    shape = (nrows,ncols)
    reclength= nrows*ncols
    shape3d = (nlays,nrows,ncols)
    reclen3d= nlays*nrows*ncols
   
    headertypes= np.dtype([
        ("KSTP",   "<i4"),
        ("KPER",   "<i4"),
        ("TEXT",   "S16"),
        ("NC",     "<i4"),
        ("NR",     "<i4"),
        ("K",      "<i4")])
    #print headertypes.names
   
    compactHeader = np.dtype([
        ("IMETH",  "<i4"),
        ("DELT",   "<f4"),
        ("PERTIM", "<f4"),
        ("TOTIM",  "<f4")])
    #print compactHeader.names

    layerList = parse_range(buildRasters)
    #print layerList
    
    print binfilename
    binfile=open(binfilename,'rb')
    endOfTime = False    
    for i in xrange(npers*15):
        pad = []
        pad1 = []
        pad2 = []
        t0=time.clock()
       
        pad1 = numpy.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
 #      print "npmy.fromfile takes: %0.4f ms:" %  ((time.clock()-t0)*1000)

        if pad1.size < 1:
            print "End of File Encountered"
            exit()
           
        iper = int(pad1["KPER"][0])
        budget = pad1["TEXT"][0].strip().replace(" ","_")
       
# print stress period after reading first budget type header (STORAGE is always first)
        #if budget.strip() == 'STORAGE':           
        print budget.strip()

        cbclays = int(pad1["K"][0])

        if cbclays < 0 and layerList <> [0]:
            pad2 = numpy.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
            tottim = int(pad2["TOTIM"][0])/100000.0
       
       
            read_data = numpy.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)
 
            ilayer = read_data[1,1]
            #print "ilayer", ilayer
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)
 
            rastername = budget + "_" + str(ilayer) + "_" + str(tottim).replace("0.","")
            #print rastername
            if timestep == None or timestep == iper:            
                if ilayer in layerList:
                    numpytoras(read_data, df, rastername,llorigin)
                elif iper > timestep:
                    endOfTime = True
                    break
            if endOfTime:
                break                                        
        elif layerList <> [0]:
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            if budget.strip() == 'FLOW_LOWER_FACE':
              for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)
                rastername = budget + "_" + str(ilayer+1) + "_" + '{:7.5f}'.format(((iper)/100000.0))
                rastername = rastername.replace("_0.","_")
                #print rastername
                if timestep == None or timestep == iper:
                    if ilayer+1 in layerList:
                        numpytoras(slice, df, rastername,llorigin)
                elif iper > timestep:
                    endOfTime = True
                    break
              if endOfTime:
                break                    

    binfile.close()
    #clean-up
    del read_data, pad, headertypes
 

