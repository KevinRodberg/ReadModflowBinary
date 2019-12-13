"""
..module::MFgis
  ::synopsis: Read Modflow Binary and setup_guiStuff.py uses: 
  :    import gisStuff.gisStuff as gis arcpy specific functions are 
  :    defined in a single module
  ::created: 10-23-2019
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""

try:
    import arcpy
except ImportError:
    from osgeo import gdal, osr, ogr
    print('ESRI arcpy library not imported')
import os
if 'GDAL_DATA' not in os.environ:
    os.environ['GDAL_DATA'] = r'C:/ProgramData/Anaconda3/Library/share/gdal'    


def getSpatialA():
#
#   Check availability and check out the ArcGIS Spatial Analyst
#   extension license required for processing binary modflow
#   output to ArcGIS rasters.  Exit program if not available.
#    
  availability = arcpy.CheckExtension("Spatial")
  if availability == "Available":
    print ("Check availability of Spatial Analyst Extension")
    arcpy.CheckOutExtension("Spatial")
    print("Extension has been successfully checked out")
  else:
    print("Spatial Analyst Extension is not available")
    print("Please ask someone who has it checked out")
    print("but not using it to turn off the extension")
    exit()
  return

def setWorkspc(geodb):
#
#   Set base paths for ESRI workspace. 
#
  outputPath = r'H:\Documents\ArcGIS'
  if not os.path.exists(outputPath): os.makedirs(outputPath)
      
  if geodb == r'H:\Documents\ArcGIS\Default.gdb':
    print ("Default gdb path defined as:{}".format(outputPath))
    gdbfile = "Default.gdb"
  elif geodb != None:
    (temp_path, gdbfile) = os.path.split(geodb)
    outputPath = temp_path
    print ('Requested output path is: {}'.format(temp_path))
    print ('Geodb: {}'.format(gdbfile))
  else:
    print ("Unspecified working path.  Assigning: {}".format(outputPath))
    (outputPath, gdbfile) = os.path.split(outputPath)
    print ('output path: {}'.format(outputPath))
    print ('Geodb: {}'.format(gdbfile))

  workspace = os.path.join(outputPath, gdbfile)
  print ("Workspace has been defined as: {}".format(workspace))
  print ("does workspace exist:")
  
  if not arcpy.Exists(workspace):
    print ("Workspace does not exist.  Creating New one!")
    (temp_path, gdbfile) = os.path.split(workspace)
    if temp_path == "":
      temp_path = outputPath
    print (temp_path)
    print (gdbfile)
    arcpy.CreateFileGDB_management(temp_path, gdbfile)
    arcpy.env.workspace = os.path.join(temp_path, gdbfile)
  else:
    arcpy.env.workspace = workspace
  print ("output will be written to: {}".format(workspace))
  arcpy.env.overwriteOutput = True
  return workspace

def clearINMEM():
  import sys
#
#   Clean up In_Memory Features, Tables and Rasters
#
  arcpy.env.workspace = r"IN_MEMORY"
  fcs = arcpy.ListFeatureClasses()
  tabs = arcpy.ListTables()
  rasters = arcpy.ListRasters()
  sys.stdout.flush()

  # for each FeatClass in the list of fcs's, delete it.
  for f in fcs:
    arcpy.Delete_management(f)
    print("Clearing IN_Memory Feature Classes: {}".format(f))
  # for each TableClass in the list of tab's, delete it.
  for t in tabs:
    arcpy.Delete_management(t)
    print("Clearing IN_Memory  Tables: {}".format(t))
  # for each raster, delete it.
  for r in rasters:
    arcpy.Delete_management(r)
    print("Clearing IN_Memory  Rasters: {}".format(r))
  return

def getModel_SR(model):
#
#  Get EPSG code selected by model name
#    
   getModel_SR= {
     'C4CDC':2881,'ECFM':2881,'ECFT':2881,'ECFTX':2881,
     'LECSR':2881,'NPALM':2881,'LKBGWM':2881,'LWCFAS':2881,
     'LWCSAS':2881,'LWCSIM':2881,'WCFM':2881}
   return(getModel_SR[model])
   
def modelClips(model):      
#
#  Get coordinate extents selected by model name
#  (xmin, ymin, xmx, ymax)    
#     
   modelClips ={
        'C4CDC':(0,0,0,0),
        'ECFM':(0,0,0,0),
        'ECFT':(0,0,0,0),
        'ECFTX':(0,0,0,0),
        'LECSR':(0,0,0,0),
        'NPALM':(0,0,0,0),
        'LKBGWM':(0,0,0,0),
        'LWCFAS':(0,0,0,0),
        'LWCSAS':(0,0,0,0),
        'LWCSIM':(0,0,0,0),
        'WCFM':(215080, 428340, 587064, 985667)}
   return(modelClips[model])

def modelOrigins(model):
    modelOrigs= {
    'C4CDC' :(763329.000, 437766.000),
    'ECFM'  :(565465.000, -44448.000),
    'ECFT'  :(330706.031,1146903.250),
    'ECFTX' :( 24352.000, 983097.000),
    'LECSR' :(680961.000, 318790.000),
    'LKBGWM':(444435.531, 903882.063),
    'NPALM' :(680961.000, 840454.000),
    'LWCFAS':(438900.000, -80164.000),
    'LWCSAS':(292353.000, 456228.000),
    'LWCSIM':(218436.000, 441788.000),
    'WCFM'  :( 20665.000, -44448.000)}
    return(modelOrigs[model])
 
def CreateGeoTiff(NewFileName, Array, driver, ncols,nrows, xsize, ysize, 
                  xcoord, ycoord,SR):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(SR)
    driver = gdal.GetDriverByName( 'GTiff' )
    DataType = gdal.GDT_Float32
    DataSet = driver.Create( NewFileName, ncols, nrows, 1, DataType )
    geotransform=(xcoord,xsize,0,ycoord,0,-ysize)  
    DataSet.SetGeoTransform(geotransform) 
    DataSet.SetProjection( srs.ExportToWkt() ) 
    DataSet.GetRasterBand(1).WriteArray( Array )
    DataSet.FlushCache()
    return NewFileName

def pixelOffset2coord(raster, xOffset,yOffset):
    geotransform = raster.GetGeoTransform()
    originX = geotransform[0]
    originY = geotransform[3]
    pixelWidth = geotransform[1]
    pixelHeight = geotransform[5]
    coordX = (originX+(pixelWidth/2))+pixelWidth*xOffset
    coordY = (originY+(pixelHeight/2))+pixelHeight*yOffset
    return coordX, coordY

def rasFile2array(rasterFile):
    raster = gdal.Open(rasterFile)
    band = raster.GetRasterBand(1)
    array = band.ReadAsArray()
    return array

def raster2array(raster):
    band = raster.GetRasterBand(1)
    array = band.ReadAsArray()
    return array

def array2shp(array,outFeature,rasterFile,arrName="VALUE",espg=2881):
    raster = gdal.Open(rasterFile)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(espg)
    
    shpDriver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(outFeature):
        shpDriver.DeleteDataSource(outFeature)
    outDataSource = shpDriver.CreateDataSource(outFeature)
    outLayer = outDataSource.CreateLayer(outFeature,srs,geom_type=ogr.wkbPoint)
    featureDefn = outLayer.GetLayerDefn()
    outLayer.CreateField(ogr.FieldDefn(arrName, ogr.OFTInteger))

    point = ogr.Geometry(ogr.wkbPoint)
    for ridx, row in enumerate(array):
        for cidx, value in enumerate(row):
            Xcoord, Ycoord = pixelOffset2coord(raster,cidx,ridx)
            point.AddPoint(Xcoord, Ycoord)
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(point)
            outFeature.SetField(arrName, int(value))
            outLayer.CreateFeature(outFeature)
            outFeature.Destroy()
    outDataSource = None        
    
def Two_array2shp(array1,array2,outFeature,rasterFile,
                  arrName1="DIR",arrName2="MAG",csizeMultiplier=1,espg=2881):
    raster = gdal.Open(rasterFile)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(espg)
    shpDriver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(outFeature):
        shpDriver.DeleteDataSource(outFeature)
    outDataSource = shpDriver.CreateDataSource(outFeature)
    outLayer = outDataSource.CreateLayer(outFeature,srs,geom_type=ogr.wkbPoint)

    featureDefn = outLayer.GetLayerDefn()
    outLayer.CreateField(ogr.FieldDefn(arrName1, ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn(arrName2, ogr.OFTReal))

    point = ogr.Geometry(ogr.wkbPoint)
    for ridx, (rowa, rowb) in enumerate(zip(array1,array2)):
        for cidx, (value1,value2) in enumerate(zip(rowa,rowb)):
            Xcoord, Ycoord = pixelOffset2coord(raster,cidx,ridx)
            point.AddPoint(Xcoord, Ycoord)
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(point)
            outFeature.SetField(arrName1, int(value1))
#  Resampled Rasters need to magnitude multiplied by resample multiplier**2]            
            outFeature.SetField(arrName2, float(value2)*(csizeMultiplier**2))
            outLayer.CreateFeature(outFeature)
            outFeature.Destroy()   
    outDataSource = None 

def TwoRas2OnePnt(dirRas,magRas,outFeature,optArgs,
                  arrName1="DIR",arrName2="MAG",
                  csizeMultiplier=1):
    espg = getModel_SR(optArgs['model'])
    if optArgs['noArc'] :
        dirRas = dirRas+'.tif'
        magRas = magRas+'.tif'
        outFeature = outFeature + '.shp'
        array1 = rasFile2array(dirRas)
        array2 = rasFile2array(magRas)
        raster = gdal.Open(dirRas)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(espg)
        shpDriver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(outFeature):
            shpDriver.DeleteDataSource(outFeature)
        outDataSource = shpDriver.CreateDataSource(outFeature)
        outLayer = outDataSource.CreateLayer(outFeature,srs,geom_type=ogr.wkbPoint)
    
        featureDefn = outLayer.GetLayerDefn()
        outLayer.CreateField(ogr.FieldDefn(arrName1, ogr.OFTInteger))
        outLayer.CreateField(ogr.FieldDefn(arrName2, ogr.OFTReal))
    
        point = ogr.Geometry(ogr.wkbPoint)
        for ridx, (rowa, rowb) in enumerate(zip(array1,array2)):
            for cidx, (value1,value2) in enumerate(zip(rowa,rowb)):
                Xcoord, Ycoord = pixelOffset2coord(raster,cidx,ridx)
                point.AddPoint(Xcoord, Ycoord)
                outFeature = ogr.Feature(featureDefn)
                outFeature.SetGeometry(point)
                outFeature.SetField(arrName1, int(value1))
    #  Resampled Rasters need to magnitude multiplied by resample multiplier**2]            
                outFeature.SetField(arrName2, float(value2)*(csizeMultiplier**2))
                outLayer.CreateFeature(outFeature)
                outFeature.Destroy()   
        outDataSource = None 
    else:
        if 'clp' in dirRas:
          fgdb = optArgs['clpgdb']
        else:
          fgdb = optArgs['geodb'] 
        arcpy.env.workspace = fgdb
        arcpy.RasterToPoint_conversion(in_raster=dirRas,out_point_features=outFeature,
                              raster_field="VALUE")
        #rasFldMap = os.path.join(fgdb,os.path.basename(magRas)+' Magnitude')
        rasFldMap = magRas+' Magnitude'
        arcpy.gp.ExtractMultiValuesToPoints_sa(outFeature,rasFldMap,"NONE")
        if csizeMultiplier != 1:
            express = "!Magnitude! * "+str(csizeMultiplier)+ " * "+str(csizeMultiplier)
            arcpy.CalculateField_management(in_table=outFeature,field="Magnitude",
                                            expression=express,
                                            expression_type="PYTHON_9.3", 
                                            code_block="#")
        arcpy.env.workspace = optArgs['geodb']  
    
def raster_X_coeff(file, file2, coeff, band=1):
#
#   Given raster file and band number, 
#   multiplies it by coeff and saves resultant raster as file2
#
    driver = gdal.GetDriverByName('GTiff')
    RaserDataSet = gdal.Open(file)
    RaserBand = RaserDataSet.GetRasterBand(1).ReadAsArray()
    geotransform = RaserDataSet.GetGeoTransform()
    geoproj = RaserDataSet.GetProjection()
    xsize = RaserDataSet.RasterXSize
    ysize = RaserDataSet.RasterYSize
    RaserBand = RaserBand.astype('f')
    # Multiply band by coefficient
    calcBand = RaserBand * coeff
    DataType = gdal.GDT_Float32
    DataSet = driver.Create(file2, xsize, ysize, 1, DataType)
    DataSet.GetRasterBand(1).WriteArray(calcBand)
    DataSet.SetGeoTransform(geotransform)
    DataSet.SetProjection(geoproj)
    DataSet.FlushCache()

def noPath (file):
    return(os.path.basename(file))
    
def numPy2Ras(npArray, rasName, optArgs, discDict):
#
#   Converts NumPy Array read from Modflow Binary
#   into an ArcGIS raster with appropriate Spatial
#   Reference for the Model being processed
#   Saving the raster to the proper Workspace
#
  resx = float(discDict['cellsize1'])
  resy = float(discDict['cellsize2'])
  nrows = int(discDict['nrows'])
  ncols = int(discDict['ncols'])
  llorigin = modelOrigins(optArgs['model'])
  ulx = llorigin[0]
  uly = llorigin[1]+(nrows*resy)
  
  # Using ArcPy
  if not optArgs['noArc']:
      SR = arcpy.SpatialReference(getModel_SR(optArgs['model']))
      arcpy.env.outputCoordinateSystem =SR
      arcpy.env.cellSize = resx
      ras = arcpy.NumPyArrayToRaster(npArray,arcpy.Point(*llorigin),
                                     resx,resy,999)
      if 'IN_MEMORY' in rasName:
         print ("In_Memory Raster: {}".format(rasName))
         rasFilename = rasName
      elif 'clp' in rasName:
         rasFilename = os.path.join(optArgs['clpgdb'], rasName)
         print ("{} \t:ArcGIS Clipped Raster".format(rasName))
      else:
         rasFilename = os.path.join(optArgs['geodb'], rasName)
         print ("{} \t\t:ArcGIS Raster".format(noPath(rasName)))
      ras.save(rasFilename)
      arcpy.DefineProjection_management(ras, SR)
  else:
    if optArgs['rasFolder'] != None:
         outputPath, rasFile = os.path.split(rasName)
         if outputPath == '':
             outputPath =  optArgs['rasFolder']
         if not os.path.exists(outputPath): os.makedirs(outputPath)
         suffix = '.tif'
         rasFilename = os.path.join(optArgs['rasFolder'],rasFile+suffix)
         if 'clp' in rasName:
           print ("{} \t:GDAL Clipped Raster".format(rasFile))
         else:
           print ("{} \t\t:GDAL Raster".format(rasFile))
         driver = gdal.GetDriverByName('GTiff')
         CreateGeoTiff(rasFilename,npArray,driver,ncols,nrows,
                       resx,resy,ulx,uly,
                       getModel_SR(optArgs['model']))
    else:
        print("rasFolder' option has been set to 'None' somehow!" )
        exit(55)
  return

def clipRaster(InRastername, optArgs):
#
#   Clip ArcGIS raster to default extents
#   defined for the model being processed
#   or to the extents of a user defined Shapefile
#

  path, ras = os.path.split(InRastername)
  if optArgs['clipBox'] != 'Default.shp':
    if optArgs['noArc']:
        clip = "%d %d %d %d" % modelClips(optArgs['model'])
    else:
        desc = arcpy.Describe(optArgs['clipBox'])
        ExtObj = desc.extent
        clip = "%d %d %d %d" % (ExtObj.XMin, ExtObj.YMin,
                                ExtObj.XMax, ExtObj.YMax)
  else:
    clip = "%d %d %d %d" % modelClips(optArgs['model'])
  clpRaster = "clp" +ras
  
  if modelClips(optArgs['model']) != (0,0,0,0):
     if not optArgs['noArc']:
        ws1 = optArgs['geodb']
        ws2 = optArgs['clpgdb']
        if path == 'IN_MEMORY':
          arcpy.env.workspace = r'IN_MEMORY'
        else:
          arcpy.env.workspace = ws2
        InRasFullame = os.path.join(ws1,ras)
        arcpy.gp.ExtractByRectangle_sa(InRasFullame,clip,clpRaster,"INSIDE")
        print ("{} \t:ArcGIS Clipped Raster".format(clpRaster))
        arcpy.env.workspace = ws1
     else:
        ws1 = optArgs['rasFolder']
        InRasFullame = os.path.join(ws1,ras+'.tif')
        ds = gdal.Open(InRasFullame)
        if ds is None: print("Failed to open ",InRasFullame)
        # arcpy.gp.ExtractByRectangle_sa needs(xmin, ymin, xmax, ymax)
        # gdal.Translate needs -projwin ulx uly lrx lry 
        (xmin, ymin, xmax, ymax) = modelClips(optArgs['model'])
        ds = gdal.Translate(os.path.join(ws1,clpRaster+'.tif'), ds, 
                            projWin = [xmin, ymax, ymin, xmax])        
        if ds is None: 
            print("Failed to translate ",InRasFullame, "to \n", 
                  os.path.join(ws1,clpRaster+'.tif'))
        else:
            print ("{} \t:GDAL Clipped Raster".format(clpRaster))
        ds = None
  return
