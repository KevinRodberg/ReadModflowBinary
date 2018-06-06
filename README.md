	# ReadModflowBinary
Python code developed to read most Modflow binary output and create ArcGIS geodatabases of rasters 
and point features representing layers of data

usage: ReadModflowBinary 

		[-h] [-bud] [-clpbox CLIPBOX] [-clpgdb CLPGDB]
		[-gdb GEODB] [-gui] [-hds] [-lay LAYERSTR]
		[-mod {ECFTX,NPALM,LECSR,LWCSIM,C4CDC,LWCSAS,LWCFAS,ECFM,LKBGWM,WCFM,ECFT}]
		[-nam NAMEFILE] [-res RESAMPLE] [-strPer STRSTR]
		[-swi] [-tds] [-terms TERMS] [-uzf] [-vec]


optional arguments:

	-h, --help          Show this help message and exit
	-bud                Process CellxCell budgets
	-clpbox CLIPBOX     Clip rasters to extent.
  	-clpgdb CLPGDB      Separate Geodatabase for Clipped Rasters
	-gdb    GEODB       Save rasters in GeoDatabase.
	-gui                GUI for options & arguments
	-hds                Process Heads file.
	-lay   LAYERSTR     Define Layers to process:
                      -- Single layer:    '-lay 1'
                      -- Multiple layers: '-lay 1,3-4,7'
                      -- No Layers:       '-lay 0'
                      -- All Layers:      '-lay None'
                      -- Command line Default is all layers
	-mod {ECFTX,NPALM,LECSR,LWCSIM,C4CDC,LWCSAS,LWCFAS,ECFM,LKBGWM,WCFM,ECFT}
                      Model defines Spatial Reference and Raster Lower Left Origin
	-nam    NAMEFILE    Assign Modflow .NAM FILE
	-res    RESAMPLE    Resampling aggregates values
                        Heads are averaged, 
                        Flows Magnitude is summed, 
                        Flow Direction is averaged
                      --------------------------
                     -res 5 Aggregates 5x5 grid
                     -res 1 Default or no resampling:[1x1]
	-strPer STRSTR   Define Stress Periods to process:
                  -- One stress period: 
                            '-strPer 218'
                  -- Multiple stress periods: 
                            '-strPer 1-12,218,288'
                  -- Omit [-strPer] for all periods
                  -- Use '-strPer 0' for none 
 	-swi             Process SWI Zetas file.
	-tds             Process TDS from MT3D file.
	-terms TERMS     Process 'TERMS' for CellxCell budget.
                  -- 'FLOW' indicates Right, Front and Lower face flow
                  -- 'RIGHT|FRONT' indicates FLOW_RIGHT_FACE and FLOW_FRONT_FACE
                  --  No parameters uses all budget terms
	-uzf             Process UZF cellbycell budgets.
	-vec             Process Flow budgets for flow vectors 
                  Automatically assigns:
                      TERMS=FLOW_RIGHT_FACE|FLOW_FRONT_FACE

