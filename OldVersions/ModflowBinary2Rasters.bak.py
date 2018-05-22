"""
..module:: ModflowRasters
    :platform: Windows
    :synopsis: Create ESRI rasters geodatabase from Modflow binary output
    ::create: 13-Sep-2013
    ::modified: 01-Jan-2016
..moduleauthor:: Kevin A. Rodberg <krodberg@sfwmd.gov>
"""
import time
import numpy
import arcpy
import re
from pandas import *

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
        print "undefined headertype:" + binaryType
        exit()
    return headertypes    

def parse_range(astr):
    result=set()
    if astr <> None:
        for part in astr.split(','):
            x=part.split('-')
            result.update(range(int(x[0]),int(x[-1])+1))
    return sorted(result)

def get_SpatialA():
#    
# Check out the ArcGIS Spatial Analyst
#  extension license
    availability = arcpy.CheckExtension("Spatial")
    if availability == "Available":
        print "Check availability of SA"
        print "..."
        arcpy.CheckOutExtension("Spatial")
        arcpy.AddMessage("SA Ext checked out")
        print "SA Ext checked out"
        print "..."
    else:
        arcpy.AddError("%s extension is not available (%s)"%("Spatial Analyst Extension",availability))
        arcpy.AddError("Please ask someone who has it checked out but not using to turn off the extension")
        exit()
    return(availability)
 
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
                elif line[0] <> 'HEAD' and row_num == 1 and item_num == 10:
                    row_num = 1
                    item_num = 0
            
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
    print "NameFile:" + sourcefile
    with open(sourcefile, 'r') as f:
        for line in f.readlines()[1:]:
            if (not line.startswith('#') ):
               if len(line) >1:
                 binlist.append(line.split()[0:4])
     #            print binlist
    f.close()
    
    df = DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
    #print df
    newdf = df[df['Initials'] == ftype_inits]
    _unitnum = newdf['unitnum']
    _filename = newdf['filename']
    
    theval = str(_filename.values)
    outval = theval.lstrip("['") 
    outval = outval.rstrip("']")
    filename = outval
 #   print theval
 #   print filename
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
    outval = theval.lstrip("['") 
    outval = outval.rstrip("']")
    filename = outval

    del df, newdf, _unitnum, _filename
    return filename
def get_bas_df(file,df):
    row=[]
    print file
    with open(file, 'r') as f:
        for line in f.readlines(10):
  #          print line
            if not line.startswith('#'):
                row.append(line.split())
    f.close()

#   for i in range(0,10):
#      print i, row[i]
     
    datarow1 = row[2]

    layer = datarow1[0]
    nrows = datarow1[1]
    ncols = datarow1[2]
    nper = datarow1[3]

    df.append(['layer', layer])
    df.append(['nrows',nrows])
    df.append(['ncols', ncols])
    df.append(['nperiod', nper])

    del row
    return df

def get_bcf_df(file,df):
    row=[]
    print file
    with open(file, 'r') as f:
        for line in f.readlines(10):
  #          print line
            if not line.startswith('#'):
                row.append(line.split())
    f.close()

#    for i in range(0,10):
#      print i, row[i]
     
    datarow1 = row[4]
    datarow2 = row[5]
    chkstr= datarow2[1].find('(')
    if chkstr < 0:
        cellsize1 = datarow1[1]
    else:
        cellsize1 = datarow1[1][:chkstr]
    print cellsize1

    chkstr= datarow2[1].find('(')
    if chkstr < 0:
        cellsize2 = datarow2[1]
    else:
        cellsize2 = datarow2[1][:chkstr]
    print cellsize2
   
    df.append(['cellsize1', cellsize1])
    df.append(['cellsize2', cellsize2])
    dfout = DataFrame(df, columns=['attribute', 'val'])
    del row
    return dfout

def get_dis_df(file,df):
    row=[]
    print file
    with open(file, 'r') as f:
        for line in f.readlines(10):
  #          print line
            if not line.startswith('#'):
                row.append(line.split())
    f.close()

    for i in range(0,10):
      print i, row[i]
     
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

def modelDisc(df):
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
        elif dfattrib[idx] == 'cellsize1':
            cellsz1 = float(dfval[idx])
        elif dfattrib[idx] == 'cellsize2':
            cellsz1 = float(dfval[idx])
    return nlays,nrows,ncols,npers,cellsz1,cellsz1
    
def numpytoras(inarr, df, rasname, llorig, SR):
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
    arcpy.DefineProjection_management(ras, SR)
    ras.save(arcpy.env.workspace +"\\" + rasname)
    del inarr, ras
    
def clipRaster(ClipRectangle,defClip,rastername,ws1,ws2):
    if ClipRectangle <> 'Default.shp':
        desc = arcpy.Describe(ClipRectangle)
        ExtObj    = desc.extent
        clip      = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin, ExtObj.XMax, ExtObj.YMax)
    else:
        clip      = "%d %d %d %d" % (defClip[0],defClip[1],defClip[2],defClip[3])
    clpRaster = "clp" +rastername
    InRastername = ws1 + "//" + rastername
    print rastername
    if defClip <> (0,0,0,0):
        arcpy.env.workspace = ws2
        arcpy.gp.ExtractByRectangle_sa(InRastername,clip,clpRaster,"INSIDE")
        print "also saving Clipped Raster: " + clpRaster
        arcpy.env.workspace = ws1
    else:
        print "Clip Extent is undefined.  Not producing " + clpRaster
    return
    
def MagDirFunc(rFaceSlice, fFaceSlice):
    # Calculate Four-Quadrant Inverse Tangent and convert radians to degrees
    tmpdirSlice = numpy.arctan2(fFaceSlice,rFaceSlice)*180 / numpy.pi
    # Negative results for degrees are adjusted to reflect range from 180 thru 360
    dirSlice = numpy.where(tmpdirSlice > 0.0, tmpdirSlice, (tmpdirSlice+360.0))
    magSlice = numpy.power((numpy.power(fFaceSlice,2)+numpy.power(rFaceSlice,2)),.5)
    return magSlice, dirSlice
    
def read_headfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2):
    read_data=[]
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(df)
    headertypes=setHeader('HEADS')
   # shape = (472,388)
    knt= nrows*ncols
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    maxTimestep =  max(strPerList)
    print strPerList
    print npers, nlays
    binfile=open(binfilename,'rb')
    endOfTime = False
    get_SpatialA()
    for i in xrange(npers):
        for l in xrange(nlays):
            pad    = []
            pad    = numpy.fromfile(file=binfile,dtype=headertypes,count=1,sep='')
           # print pad
            budget = pad["TEXT"][0].strip().replace(" ","_")
            kper   = pad["KPER"][0]
            k      = pad["K"][0]
           # print pad
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=knt, sep='').reshape(shape)
       
            rastername = "HEAD" + '{:7.5f}'.format(((kper)/100000.0)) + "_" + str(l+1)
            rastername = rastername.replace("0.","_")
            
            if layerList <> [0] or strPerList <> [0]:
                if k in layerList:
                    if not strPerList or kper in strPerList:
                        numpytoras(read_data, df, rastername, llorigin,SR)
                        clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                    elif kper > maxTimestep:   
                        endOfTime = True
                        print "EndofTime= SP="+str(strPerList)+" kper=" + str(kper) + " > Maxts = " + str(maxTimestep)
                        exit()
            if endOfTime:
                exit()
    binfile.close()
    del read_data, pad, headertypes
    
def read_concfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2):
    availability = get_SpatialA()
    print ">>>Spatial Analyst " + availability

    read_data=[]   
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(df)

# Modflow Binary Heads and Concentration share the same file structure
    headertypes=setHeader('HEADS')
   # shape = (472,388)
    knt= nrows*ncols
    shape = (nrows,ncols)
    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    maxTimestep =  max(strPerList)
    
    binfile=open(binfilename,'rb')
    endOfTime = False
    get_SpatialA()    
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
            if layerList <> [0] or strPerList <> [0]:
                if not layerList or k in layerList:
                    if not strPerList or totim in strPerList:
                        numpytoras(read_data, df, rastername,llorigin,SR)
                        clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                            
                    if strPerList and totim > maxTimestep:                        
                        endOfTime = True
                        return
    binfile.close()
    del read_data, pad, headertypes    
def read_cbcfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2,terms,form,factor):
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(df)
   
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
    print 'see mee', strPerList
    if strPerList:
        maxTimestep =  max(strPerList)
    else:
        maxTimestep = 0
    termset = re.compile(terms)
    
    print binfilename
    binfile=open(binfilename,'rb')
    endOfTime = False
    get_SpatialA()
    for i in xrange(npers*15):
        pad = []
        pad1 = []
        pad2 = []
        t0=time.clock()
       
        if form <> 'UF':
            pad1 = numpy.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')
        else:
    #        print "using Unformatted Headertypes"
            pad1 = numpy.fromfile(file=binfile,dtype=cbcUFheadtypes,count=1,sep='')
 #      print "npmy.fromfile takes: %0.4f ms:" %  ((time.clock()-t0)*1000)

        if pad1.size < 1:
            print "End of File Encountered"
            exit()
           
        iper = int(pad1["KPER"][0])
        budget = pad1["TEXT"][0].strip().replace(" ","_")
       
# print stress period after reading first budget type header (STORAGE is always first)
        #if budget.strip() == 'STORAGE':           
        #print iper

        cbclays = int(pad1["K"][0])

        if cbclays < 0 and layerList <> [0] and strPerList <> [0]:
            pad2 = numpy.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
            tottim = int(pad2["TOTIM"][0])/100000.0
       
            read_data = numpy.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)
 
            ilayer = read_data[1,1]
            print "ilayer", ilayer
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)
 
            rastername = budget + "_" + str(ilayer) + "_" + str(tottim).replace("0.","")
            print rastername
            if not strPerList or iper in strPerList:            
                if ilayer in layerList:
                    if not terms or terms == 'ALL' or termset.search(budget):
                        print budget
                        numpytoras(read_data, df, ras, llorigin,SR)
             #           rastername = ras * factor                        
                        clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                elif maxTimestep > 0 and iper > maxTimestep:
                    endOfTime = True
                    print "EndOfTime in cbcBudbets"
                    return
            if endOfTime:
                return                                        
        elif layerList <> [0] and strPerList <> [0]:
            if form == 'UF':
                bor = numpy.fromfile(file=binfile, dtype=np.int32, count=1, sep='')      
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            if form == 'UF':
                bor = numpy.fromfile(file=binfile, dtype=np.int32, count=1, sep='')                 
            for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)
                rastername = budget + "_" + str(ilayer+1) + "_" + '{:7.5f}'.format(((iper)/100000.0))
                rastername = rastername.replace("_0.","_")
                #print rastername
                if not strPerList or iper in strPerList:
                    if ilayer+1 in layerList:
                        if not terms or terms == 'ALL' or termset.search(budget):
                            numpytoras(slice, df, rastername, llorigin,SR)
                 #           rastername = ras * factor
                            clipRaster(ClipRectangle,defClip,rastername,ws1,ws2)
                        
                elif maxTimestep > 0 and iper > maxTimestep:
                    endOfTime = True
                    return
            if endOfTime:
                return                    

    binfile.close()
    #clean-up
    del read_data, pad, cbcheadertypes, compactHeader
 
def read_cbcVectors(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,ws1,ws2,terms,cellsize,form,factor):
    availability = get_SpatialA()
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(df)

    csizeMultiplier = int(cellsize)
    CsizeVal = csizeMultiplier * cellsz1
    cellsize = str(CsizeVal)            
    #print nlays, nrows, ncols, npers
   
    read_data=[]   
    shape = (nrows,ncols)
    reclength= nrows*ncols
    shape3d = (nlays,nrows,ncols)
    reclen3d= nlays*nrows*ncols
    get_SpatialA()
    cbcheadertypes=setHeader('CBC')
    print "FORM-" + form
    cbcheadertypes=setHeader('CBC')
    cbcUFheadtypes=setHeader('CBCUF')
    
    def doFlowVec(factor):
        global rFaceSlice
        print "Inside function doFlowVec: " +budget
        if budget == 'FLOW_RIGHT_FACE':
            rFaceSlice = slice
        if budget == 'FLOW_FRONT_FACE':
            fFaceSlice = slice
            (magSlice, dirSlice) = MagDirFunc(rFaceSlice, fFaceSlice)
            rasterdir = "LAY0" + str(ilayer+1) + "DIR_" + '{:7.5f}'.format(((iper)/100000.0))
            rasterdir = rasterdir.replace("_0.","_")
            rastermag = rasterdir.replace("DIR_","MAG_")
            print rasterdir
            print rastermag
            numpytoras(dirSlice, df, rasterdir,llorigin,SR)
            numpytoras(magSlice, df, rastermag,llorigin,SR)
            if defClip <> (0,0,0,0):
                clipRaster(ClipRectangle,defClip,rasterdir,ws1,ws2)
                clipRaster(ClipRectangle,defClip,rastermag,ws1,ws2)

            print csizeMultiplier
            if csizeMultiplier > 1:

                print "Resampling rasters ..."
                rasterdirResamp="LAY0" + str(ilayer+1) + "DIRX_" + '{:7.5f}'.format(((iper)/100000.0))
                rasterdirResamp = rasterdirResamp.replace("_0.","_")
                rastermagResamp = rasterdirResamp.replace("DIRX_","MAGX_")
                arcpy.Resample_management(rasterdir, rasterdirResamp, cellsize, "BILINEAR")
                arcpy.Resample_management(rastermag, rastermagResamp, cellsize, "BILINEAR")
                if defClip <> (0,0,0,0):
                    clipRaster(ClipRectangle,defClip,rasterdirResamp,ws1,ws2)
                    clipRaster(ClipRectangle,defClip,rastermagResamp,ws1,ws2)
                
                print rasterdirResamp
                print rastermagResamp
                            
                rastDirX = arcpy.env.workspace + "\\" + rasterdirResamp
                
#                inMemFCX = "in_memory/" + rasterdirResamp + "arw"
                arrowFeatureX = arcpy.env.workspace +"\\" + rasterdirResamp + "arw"
                inMemFCX = arrowFeatureX
                
                rastMagX = arcpy.env.workspace + "\\" + rastermagResamp
                print "Creating points from Directional Rasters"
                print "Saving " + rasterdirResamp + "arw"
                
                arcpy.RasterToPoint_conversion(in_raster=rastDirX,out_point_features=inMemFCX,raster_field="VALUE")
                inRasterListX = rastermagResamp+ " Magnitude"
                print "Extracting Magnitudes to points"
                
                arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCX,inRasterListX,"NONE")
                express = "!Magnitude! * "  + str(csizeMultiplier) + " * " + str(csizeMultiplier)
                arcpy.CalculateField_management(in_table=inMemFCX,field="Magnitude",
                                                expression=express,expression_type="PYTHON_9.3",code_block="#")
#                print "Saving " + rasterdirResamp + "arw"
#                arcpy.CopyFeatures_management(inMemFCX, arrowFeatureX)
                            
                if defClip <> (0,0,0,0):
                    print "Processing Re-sampled Rasters with Clipped Boundary"
                    arcpy.env.workspace = ws2
                    rastDirXclp = arcpy.env.workspace + "\\clp" + rasterdirResamp
                    arrowFeatureXclp = arcpy.env.workspace +"\\clp" + rasterdirResamp + "arw"
                    inMemFCXclp = arrowFeatureXclp
 #                   inMemFCXclp = "in_memory/clp" + rasterdirResamp + "arw"
                    rastMagXclp = arcpy.env.workspace + "\\clp" + rastermagResamp
                    print "Saving " + "\\clp" + rasterdirResamp + "arw"                    
                    arcpy.RasterToPoint_conversion(in_raster=rastDirXclp,out_point_features=inMemFCXclp,raster_field="VALUE")
                    inRasterListXclp = "clp"+rastermagResamp+ " Magnitude"
                    arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCXclp,inRasterListXclp,"NONE")
                    arcpy.CalculateField_management(in_table=inMemFCXclp,field="Magnitude",
                                                            expression=express,expression_type="PYTHON_9.3",code_block="#")
#                    arcpy.CopyFeatures_management(inMemFCXclp, arrowFeatureXclp)
                    arcpy.env.workspace = ws1
            else:
                print "No resampling"
                            
                rastDir = arcpy.env.workspace +"\\" + rasterdir
                arrowFeature = arcpy.env.workspace +"\\" + rasterdir + "arw"
                inMemFC = arrowFeature
                print "Saving " + rasterdir + "arw"                
#                inMemFC = "in_memory/" + rasterdir + "arw"
                rastMag = arcpy.env.workspace +"\\" + rastermag
                arcpy.RasterToPoint_conversion(in_raster=rastDir,out_point_features=inMemFC,raster_field="VALUE")
                MyField = "Magnitude"
                inRasterList = rastermag+ " " + MyField
                arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFC,inRasterList,"NONE")
#                arrowFeature = arcpy.env.workspace +"\\" + rasterdir + "arw"
#                print "Saving " + rasterdir + "arw"
#                arcpy.CopyFeatures_management(inMemFC, arrowFeature)
                        
                if defClip <> (0,0,0,0):
                    print "Processing Rasters with Clipped Boundary"
                    
                    arcpy.env.workspace = ws2
                    rastDirclp = arcpy.env.workspace +"\\clp" + rasterdir
                    arrowFeatureclp = arcpy.env.workspace +"\\clp" + rasterdir + "arw"                    
#                    inMemFCclp = "in_memory/clp" + rasterdir + "arw"
                    inMemFCclp = arrowFeatureclp
                    rastMagclp = arcpy.env.workspace +"\\clp" + rastermag
                    print "Saving " + "\\clp" + rasterdir + "arw"                    
                    arcpy.RasterToPoint_conversion(in_raster=rastDirclp,out_point_features=inMemFCclp,raster_field="VALUE")
                    arcpy.env.workspace = ws1
                    MyField = "Magnitude"
                    inRasterList = rastermag+ " " + MyField
                    arrowFeatureclp = arcpy.env.workspace +"\\clp" + rasterdir + "arw"
                    arcpy.gp.ExtractMultiValuesToPoints_sa(inMemFCclp,inRasterList,"NONE")
#                    print "Saving " + "\\clp" + rasterdir + "arw"
#                    arcpy.CopyFeatures_management(inMemFCclp, arrowFeatureclp)
        return

    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    if strPerList <> []:
        print strPerList
        maxTimestep =  max(strPerList)
    else:
        maxTimestep = 0    
    termset = re.compile(terms)
    
    print binfilename
    binfile=open(binfilename,'rb')
    endOfTime = False    
    for i in xrange(npers*15):
        pad = []
        pad1 = []
        pad2 = []
        t0=time.clock()
        
        if form <> 'UF':
          #  print "using formatted Headertypes"
            pad1 = numpy.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')
        else:
          #  print "using Unformatted Headertypes"
            pad1 = numpy.fromfile(file=binfile,dtype=cbcUFheadtypes,count=1,sep='')       
        print pad1
        if pad1.size < 1:
            print "End of File Encountered"
            exit()
           
        iper = int(pad1["KPER"][0])
        budget = pad1["TEXT"][0].strip().replace(" ","_")
 #       print "Period:"
 #       print iper
 #       print " Budget Term: " + budget
 #       print "..."
        
# print stress period after reading first budget type header (STORAGE is always first)
        #if budget.strip() == 'STORAGE':           
            #print iper

        cbclays = int(pad1["K"][0])

        if cbclays < 0 and layerList <> [0] and strPerList <> [0]:
            print "Working with Comact Headers"
            pad2 = numpy.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
            tottim = int(pad2["TOTIM"][0])/100000.0
              
            read_data = numpy.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)
 
            ilayer = read_data[1,1]
            #print "ilayer", ilayer
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)

            if strPerList == [] or iper in strPerList:            
                if ilayer in layerList:
                    if termset.search(budget):
                        doFlowVec(factor)
                        

            elif maxTimestep > 0 and iper > maxTimestep:
                endOfTime = True
                return
            if endOfTime:
                return                                        
        elif layerList <> [0] and strPerList <> [0]:
            if form == 'UF':
                bor = numpy.fromfile(file=binfile, dtype=np.int32, count=1, sep='')      
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            if form == 'UF':
                eor = numpy.fromfile(file=binfile, dtype=np.int32, count=1, sep='') 

            for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)

                if strPerList == [] or iper in strPerList:                  
                    if ilayer+1 in layerList:
                        if termset.search(budget):
            #                print "calling doFlowvec from CBC vector routine"
                            doFlowVec(factor)
                            
                elif iper > maxTimestep:
                    endOfTime = True
                    return
            if endOfTime:
                return                    

    binfile.close()
    #clean-up
    del read_data, cbcheadertypes
    
