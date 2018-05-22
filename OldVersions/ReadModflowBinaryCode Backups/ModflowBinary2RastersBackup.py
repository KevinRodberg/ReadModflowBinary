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
  #               print binlist
    f.close()
    
    df = DataFrame(binlist, columns = ['Initials', 'unitnum', 'filename', 'status'])
#    print df
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
    
def clipRaster(ClipRectangle,defClip,rastername):
    if ClipRectangle <> 'Default.shp':
        desc = arcpy.Describe(ClipRectangle)
        ExtObj    = desc.extent
        clip      = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin, ExtObj.XMax, ExtObj.YMax)
    else:
        clip      = "%d %d %d %d" % (defClip[0],defClip[1],defClip[2],defClip[3])
    clpRaster = "clp" +rastername
    if defClip <> (0,0,0,0):
        arcpy.gp.ExtractByRectangle_sa(rastername,clip,clpRaster,"INSIDE")
        print "also saving Clipped Raster: " + clpRaster
    else:
        print "Clip Extent is undefined.  Not producing " + clpRaster
    return
                            
def read_headfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip):
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
            
            if layerList <> [0] or strPerList <> [0]:
                if k in layerList:
                    if not strPerList or kper in strPerList:
                        numpytoras(read_data, df, rastername,llorigin,SR)
                        clipRaster(ClipRectangle,defClip,rastername)
                    elif kper > maxTimestep:   
                        endOfTime = True
                        break
            if endOfTime:
                break
    binfile.close()
    del read_data, pad, headertypes
    
def read_concfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip):
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
                        clipRaster(ClipRectangle,defClip,rastername)
                            
                    if strPerList and totim > maxTimestep:                        
                        endOfTime = True
                        print "EndofTime"
                        return
    binfile.close()
    del read_data, pad, headertypes    
def read_cbcfile(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,terms):
    nlays,nrows,ncols,npers,cellsz1,cellsz1=modelDisc(df)
   
    read_data=[]   
    shape = (nrows,ncols)
    reclength= nrows*ncols
    shape3d = (nlays,nrows,ncols)
    reclen3d= nlays*nrows*ncols
    
    cbcheadertypes=setHeader('CBC')
    compactHeader=setHeader('XCBC')


    layerList = parse_range(buildRasters)
    strPerList = parse_range(buildStressPer)
    if strPerList <> None:
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
       
        pad1 = numpy.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')
 #      print "npmy.fromfile takes: %0.4f ms:" %  ((time.clock()-t0)*1000)

        if pad1.size < 1:
            print "End of File Encountered"
            exit()
           
        iper = int(pad1["KPER"][0])
        budget = pad1["TEXT"][0].strip().replace(" ","_")
       
# print stress period after reading first budget type header (STORAGE is always first)
        #if budget.strip() == 'STORAGE':           
          #  print iper

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
                        numpytoras(read_data, df, rastername,llorigin,SR)
                        clipRaster(ClipRectangle,defClip,rastername)
                elif maxTimestep > 0 and iper > maxTimestep:
                    endOfTime = True
                    print "EndOfTime in cbcBudbets"
                    return
            if endOfTime:
                return                                        
        elif layerList <> [0] and strPerList <> [0]:
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)
                rastername = budget + "_" + str(ilayer+1) + "_" + '{:7.5f}'.format(((iper)/100000.0))
                rastername = rastername.replace("_0.","_")
                #print rastername
                if not strPerList or iper in strPerList:
                    if ilayer+1 in layerList:
                        if not terms or terms == 'ALL' or termset.search(budget):
                            numpytoras(slice, df, rastername,llorigin,SR)
                            clipRaster(ClipRectangle,defClip,rastername)
                        
                elif maxTimestep > 0 and iper > maxTimestep:
                    endOfTime = True
                    return
            if endOfTime:
                return                    

    binfile.close()
    #clean-up
    del read_data, pad, cbcheadertypes, compactHeader
 
def read_cbcVectors(binfilename,df,buildRasters,buildStressPer,llorigin,SR,ClipRectangle,defClip,terms,cellsize):
    availability = get_SpatialA()
    print ">>>Spatial Analyst " + availability
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
   
    cbcheadertypes=setHeader('CBC')


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
       
        pad1 = numpy.fromfile(file=binfile,dtype=cbcheadertypes,count=1,sep='')

        if pad1.size < 1:
            print "End of File Encountered"
            exit()
           
        iper = int(pad1["KPER"][0])
        budget = pad1["TEXT"][0].strip().replace(" ","_")
        print "Period:"
        print iper
        print " Budget Term: " + budget
        print "..."
        
# print stress period after reading first budget type header (STORAGE is always first)
        #if budget.strip() == 'STORAGE':           
            #print iper

        cbclays = int(pad1["K"][0])

        if cbclays < 0 and layerList <> [0] and strPerList <> [0]:
            pad2 = numpy.fromfile(file=binfile,dtype=compactHeader,count=1,sep='')
            tottim = int(pad2["TOTIM"][0])/100000.0
              
            read_data = numpy.fromfile(file=binfile, dtype=np.int32, count=reclength, sep='').reshape(shape)
 
            ilayer = read_data[1,1]
            #print "ilayer", ilayer
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclength, sep='').reshape(shape)

            if strPerList == [] or iper in strPerList:            
                if ilayer in layerList:
                    if termset.search(budget):
                        print budget
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
                            clipRaster(ClipRectangle,defClip,rasterdir)
                            numpytoras(magSlice, df, rastermag,llorigin,SR)
                            clipRaster(ClipRectangle,defClip,rastermag)
                            
                            print cellsize
                            if cellsize > '1':
                                print "Resampling rasters ..."
                                rasterdirResamp="LAY0" + str(ilayer+1) + "DIRX_" + '{:7.5f}'.format(((iper)/100000.0)) 
                                rasterdirResamp = rasterdirResamp.replace("_0.","_")
                                rastermagResamp = rasterdirResamp.replace("DIRX_","MAGX_")
                                arcpy.Resample_management(rasterdir, rasterdirResamp, cellsize, "BILINEAR")
                                clipRaster(ClipRectangle,defClip,rasterdirResamp)
                                arcpy.Resample_management(rastermag, rastermagResamp, cellsize, "CUBIC")
                                clipRaster(ClipRectangle,defClip,rastermagResamp)
                                
                                print rasterdirResamp
                                print rastermagResamp
                                
                                rastDirX = arcpy.env.workspace + "\\" + rasterdirResamp
                                inMemFCX = "in_memory/" + rasterdirResamp + "arw"
                                rastMagX = arcpy.env.workspace + "\\" + rastermagResamp
                                print "Creating points"
                                arcpy.RasterToPoint_conversion(in_raster=rastDirX,
                                                               out_point_features=inMemFCX,
                                                               raster_field="VALUE")

                                inPointFeatureX = inMemFCX
                                inRasterListX = rastermagResamp+ " Magnitude"
                                print "Extracting Magnitudes to points"
                                arcpy.gp.ExtractMultiValuesToPoints_sa(inPointFeatureX,inRasterListX,"NONE")
                                arcpy.CalculateField_management(in_table=inMemFCX,field="Magnitude",
                                                                expression="!Magnitude! * 7.48",
                                                                expression_type="PYTHON_9.3",
                                                                code_block="#")
                                arrowFeatureX = arcpy.env.workspace +"\\" + rasterdirResamp + "arw"
                                arcpy.CopyFeatures_management(inMemFCX, arrowFeatureX)
                                
                                if defClip <> (0,0,0,0):
                                    rastDirXclp = arcpy.env.workspace + "\\clp" + rasterdirResamp
                                    inMemFCXclp = "in_memory/clp" + rasterdirResamp + "arw"
                                    rastMagXclp = arcpy.env.workspace + "\\clp" + rastermagResamp
                                    arcpy.RasterToPoint_conversion(in_raster=rastDirXclp,
                                                               out_point_features=inMemFCXclp,
                                                               raster_field="VALUE")
                                    inPointFeatureXclp = inMemFCXclp
                                    inRasterListXclp = "clp"+rastermagResamp+ " Magnitude"
                                    arcpy.gp.ExtractMultiValuesToPoints_sa(inPointFeatureXclp,inRasterListXclp,"NONE")
                                    arcpy.CalculateField_management(in_table=inMemFCXclp,field="Magnitude",
                                                                expression="!Magnitude! * 7.48",
                                                                expression_type="PYTHON_9.3",
                                                                code_block="#")
                                    arrowFeatureXclp = arcpy.env.workspace +"\\clp" + rasterdirResamp + "arw"
                                    arcpy.CopyFeatures_management(inMemFCXclp, arrowFeatureXclp)

                                    
                            else:
                                print "No resampling"
                                
                            rastDir = arcpy.env.workspace +"\\" + rasterdir
                            inMemFC = "in_memory/" + rasterdir + "arw"
                            rastMag = arcpy.env.workspace +"\\" + rastermag
                            arcpy.RasterToPoint_conversion(in_raster=rastDir,
                                                               out_point_features=inMemFC,
                                                               raster_field="VALUE")
                            inPointFeature = inMemFC
                            MyField = "Magnitude"
                            Fields = ['Magnitude']
                            inRasterList = rastermag+ " " + MyField
                            arcpy.gp.ExtractMultiValuesToPoints_sa(inPointFeature,inRasterList,"NONE")

                            with arcpy.da.UpdateCursor(inMemFC, Fields) as cursor:
                                for row in cursor:
                                    row[0] = row[0]*7.48
                                    cursor.updateRow(row)

                            arrowFeature = arcpy.env.workspace +"\\" + rasterdir + "arw"                             
                            arcpy.CopyFeatures_management(inMemFC, arrowFeature)
                            
                            if defClip <> (0,0,0,0):
                                rastDirclp = arcpy.env.workspace +"\\clp" + rasterdir
                                inMemFCclp = "in_memory/clp" + rasterdir + "arw"
                                rastMagclp = arcpy.env.workspace +"\\clp" + rastermag
                                arcpy.RasterToPoint_conversion(in_raster=rastDirclp,
                                                               out_point_features=inMemFCclp,
                                                               raster_field="VALUE")
                                

            elif maxTimestep > 0 and iper > maxTimestep:
                endOfTime = True
                break
            if endOfTime:
                break                                        
        elif layerList <> [0] and strPerList <> [0]:
            read_data = numpy.fromfile(file=binfile, dtype=np.float32, count=reclen3d, sep='').reshape(shape3d)
            for ilayer in range(nlays):
                slice = read_data[ilayer,:,:].reshape(shape)

                if strPerList == [] or iper in strPerList:                  
                    if ilayer+1 in layerList:
                        if termset.search(budget):
                            print budget
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
                                print "Dataframe slices complete"
                                print cellsize
                                if cellsize > '1':
                                    print "Resampling rasters ..."
                                    rasterdirResamp="LAY0" + str(ilayer+1) + "DIRX_" + '{:7.5f}'.format(((iper)/100000.0)) 
                                    rasterdirResamp = rasterdirResamp.replace("_0.","_")
                                    rastermagResamp = rasterdirResamp.replace("DIRX_","MAGX_")
                                    arcpy.Resample_management(rasterdir, rasterdirResamp, cellsize, "BILINEAR")
                                    arcpy.Resample_management(rastermag, rastermagResamp, cellsize, "CUBIC")
                                    print rasterdirResamp
                                    print rastermagResamp     
                                    rastDirX = arcpy.env.workspace +"\\" + rasterdirResamp
                                    inMemFCX = "in_memory/" + rasterdirResamp + "arw"
                                    rastMagX = arcpy.env.workspace +"\\" + rastermagResamp
                                    print "Creating points"
                                    arcpy.RasterToPoint_conversion(in_raster=rastDirX,out_point_features=inMemFCX,raster_field="VALUE")
                                    inPointFeatureX = inMemFCX
                                    inRasterListX = rastermagResamp+ " Magnitude"
                                    print "Extracting Magnitudes to points"
                                    arcpy.gp.ExtractMultiValuesToPoints_sa(inPointFeatureX,inRasterListX,"NONE")
                                    arcpy.CalculateField_management(in_table=inMemFCX,field="Magnitude",expression="!Magnitude! * 7.48",
                                                                    expression_type="PYTHON_9.3",code_block="#")
                                    arrowFeatureX = arcpy.env.workspace +"\\" + rasterdirResamp + "arw"
                                    arcpy.CopyFeatures_management(inMemFCX, arrowFeatureX)
                                else:
                                    print "No resampling"

                                rastDir = arcpy.env.workspace +"\\" + rasterdir
                                inMemFC = "in_memory/" + rasterdir + "arw"
                                rastMag = arcpy.env.workspace +"\\" + rastermag

                                print "inMemory Raster to Point conversion"
                                print "..."                                
                                arcpy.RasterToPoint_conversion(in_raster=rastDir,out_point_features=inMemFC,raster_field="VALUE")
                                print "..."
                                inPointFeature = inMemFC
                                MyField = "Magnitude"
                                Fields = ['Magnitude']
                                inRasterList = rastermag+ " " + MyField
                                
                                print "extracting points"
                                print "..."
                                arcpy.gp.ExtractMultiValuesToPoints_sa(inPointFeature,inRasterList,"NONE")

                                print "Calc Gallons from Cubic Feet"
                                print "..."
                                with arcpy.da.UpdateCursor(inMemFC, Fields) as cursor:
                                    for row in cursor:
                                        row[0] = row[0]*7.48
                                        cursor.updateRow(row)
                                        
                                arrowFeature = arcpy.env.workspace +"\\" + rasterdir + "arw"
                                print "saving arrowFeature from inMemoryFC"
                                print "..."
                                arcpy.CopyFeatures_management(inMemFC, arrowFeature)
                                print "..."

                elif iper > maxTimestep:
                    endOfTime = True
                    break
            if endOfTime:
                break                    

    binfile.close()
    #clean-up
    del read_data, pad, cbcheadertypes
    
def MagDirFunc(rFaceSlice, fFaceSlice):
    dirSlice = numpy.arctan2(fFaceSlice,rFaceSlice)*180 / numpy.pi 
    magSlice = numpy.power((numpy.power(fFaceSlice,2)+numpy.power(rFaceSlice,2)),.5)
    return magSlice, dirSlice