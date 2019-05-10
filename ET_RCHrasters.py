import os
import arcpy

ET_RasName  = "ET_1_00001"
RCH_RasName = "RECHARGE_1_00001"

inGDB =r"\\ad.sfwmd.gov\dfsRoot\data\wsd\MOD\Uditha\CFWI\CFWI_Expansion\GIS\ETRCH03_051018.gdb"
outGDB= r"\\ad.sfwmd.gov\dfsRoot\data\wsd\MOD\Uditha\CFWI\CFWI_Expansion\GIS\ETRCH03_051018.gdb"

inETras = arcpy.Raster(os.path.join(inGDB,ET_RasName))
inRCHras = arcpy.Raster(os.path.join(inGDB,RCH_RasName))

ET_out ="ETinchPerYear"
RCH_out ="RechinchPerYear"
NET_out ="NETinchPerYear"

ETinchPerYear = ( inETras * 365*12)/(1250*1250)*(-1)
ETinchPerYear.save(os.path.join(outGDB,ET_out))
              
RechinchPerYear = ( inRCHras * 365*12)/(1250*1250)
RechinchPerYear.save(os.path.join(outGDB,RCH_out))

NETinchPerYear = RechinchPerYear - ETinchPerYear
NETinchPerYear.save(os.path.join(outGDB,NET_out))

