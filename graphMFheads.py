# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 09:19:18 2017

@author: rhaynes
	Modified by krodberg
"""
import multiprocessing as mp
import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mpdt
import matplotlib.ticker as mptk
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
import easygui as ez

years = mpdt.YearLocator()   # every year
months = mpdt.MonthLocator()  # every month
yearsFmt = mpdt.DateFormatter('%Y')

##############################
#This function will take two lists and plot them
# from SDabral's stage_dur_plots.py
##############################
def plot_data_D (dataDict, cellid, topo,RunOptions,tempOutName):
        data3=[topo,topo]
        data4=[0,100]
        fig, ax = plt.subplots (1)
        fig.set_size_inches(18.5,9.0)
        ax.set_xlabel (r'Percent Time Equal to or Exceeded', fontsize = 17)
        ax.set_ylabel (r'Computed Head (ft, NGVD29)',fontsize = 17)
        ax.set_title ('Duration Curve for %s\nElevation:%6.2f ft, NGVD29' % (cellid,topo),x=0.5,y=1.03,fontsize = 21)
        ax.xaxis.set_label_coords(0.45, -0.1)
        ax.yaxis.set_label_coords(-0.047, 0.45)
        xmajorlocator = mptk.MultipleLocator (10)
        xminorlocator = mptk.MultipleLocator (5)
        ymajorlocator = mptk.MultipleLocator (0.5)
        yminorlocator = mptk.MultipleLocator (0.1)
        ax.tick_params (axis='x',labelsize=15.0)
        ax.tick_params (axis='y',labelsize=15.0)
        ax.xaxis.set_major_locator (xmajorlocator)
        ax.xaxis.set_minor_locator (xminorlocator)
        ax.yaxis.set_major_locator (ymajorlocator)
        ax.yaxis.set_minor_locator (yminorlocator)
        ax.yaxis.grid(True,'major',linewidth=0.5)
        ax.xaxis.set_tick_params (direction = 'inout',which = 'both',length=7)
        ax.yaxis.set_tick_params (direction = 'inout',which = 'both',length=7)
        ax.grid (True)
        fig.tight_layout (pad=2.08)
        for Run,Heads in dataDict.items():
            heads = sorted(Heads[cellid])
            lenght = len(heads)
            exceedance_prob = [float(i)/float(lenght)*100. for i in range(lenght)]
            #Sort computed head data from highest to lowest
            heads =  [float(data) for data in heads]
            computed_head_high_to_low = sorted (heads,reverse=True)
            opts = RunOptions[Run]
            if opts[2] == 'line':
                opts[2] = ''
            plt.plot(exceedance_prob,computed_head_high_to_low,linestyle=opts[1], marker=opts[2], color=opts[0],markersize=0.3, label= str(Run))
        plt.plot(data4,data3, linestyle = '-', color='black', label = 'Elevation')
        plt.legend ()
        plt.savefig(tempOutName + r'\DC_'+ cellid.strip()+'.png')
        plt.close()
# reading control file
#From SDabral hydrograph_with_your_topo_SEGMENTS1.py
def plot_data ( dataDict, segmentId, topo,RunOptions,tempOutName):
    small = 100
    large = 0
    L=[topo]*2
    fig, ax = plt.subplots (1)
    fig.set_size_inches(18.5,9.0)
    ax.set_xlabel (r'Year', fontsize=12, labelpad= 30)
    ax.set_ylabel (r'Computed Head (ft, NGVD29)',fontsize = 14, labelpad= 35)
    ax.set_title ('Stage Hydrograph for  %s\nElevation:%6.2f ft, NGVD29' % (segmentId,topo),x=0.5,y=1.03,fontsize = 15)


    for Run,Heads in dataDict.items():
        opts = RunOptions[Run]
        if opts[2] == 'line':
            opts[2] = ''
        y=[]
   #     print (Run, Heads)
        x= pd.to_datetime(Heads['     _Date'])
        y= Heads[segmentId]
        minDate = min(x)
        maxDate = max(x)
        plt.plot_date (x, y,  linestyle = opts[1], marker = opts[2], color = opts[0], label = str(Run))
        s = min(y)
        l = max(y)
        if s <  small:
            small = s
        if l > large:
            large = l
    plt.plot_date ([minDate,maxDate], L, linestyle="-",lw=1.2, label = "Elevation", markersize = 4,color="indigo")
    years = YearLocator ()
    months = MonthLocator ()
    yearsFmt = DateFormatter ("%Y")
    ymin= min(small,topo)
    ymax = max(large,topo)
    plt.ylim([ymin-1,ymax+1])
    # format the ticks
    ax.xaxis.set_major_locator(years)
    ax.xaxis.set_major_formatter(yearsFmt)
    ax.xaxis.set_minor_locator(months)
    ax.yaxis.set_minor_locator (mptk.MultipleLocator(0.1))
    ax.xaxis.grid(True,'major',linestyle = ':')
    ax.yaxis.grid(True,'major',linestyle = ':')
    ax.set_xlim (minDate,maxDate)
#   ax.autoscale_view()
    fig.autofmt_xdate(rotation = 40)
    ax.yaxis.set_major_formatter(mptk.FormatStrFormatter('%.2f'))
    plt.legend ()
#        tight_layout()
    plt.savefig(tempOutName + r'\HG_'+ segmentId.strip()+'.png')
    plt.close()



def log_result(result):
    result_list.append(result)

def compileFigs(platform,headsbyRun,Stations,RunsOptions,tempOutName):
    results = []
    if platform == 'mp':
        print("    Multiprocessing enabled:")
        print("    Figures will be created in the background using {} processors.".format(mp.cpu_count()))
        pool = mp.Pool(processes=None)
        for runName, Rheads in headsbyRun.items():
            pass
        for statName in Rheads.keys():
            station = statName.strip()
            print ("station={}".format(station))
            if station in Stations.keys():
                 topo = Stations[station]
                 result=pool.apply_async(plot_data, (headsbyRun, statName, topo,RunsOptions,tempOutName),callback=log_result)
                 results.append(result)
                 result=pool.apply_async(plot_data_D, (headsbyRun, statName, topo,RunsOptions,tempOutName),callback=log_result)
                 results.append(result)
        pool.close()
    else:
        print ("    Single processor mode")
        for runName, Rheads in headsbyRun.items():
            pass
        for statName in Rheads.keys():
                station = statName.strip()
                print ("station={}".format(station))
                if station in Stations.keys():
                    topo = Stations[station]
                    plot_data(headsbyRun, statName, topo,RunsOptions,tempOutName)
                    plot_data_D(headsbyRun, statName, topo,RunsOptions,tempOutName)
    return(results)
def checkExec_env():
    cmdL = False
    a = sys.executable
    m = '\\'
    m = m[0]
    while True:
        b = len(a)
        c = a[(b - 1)]
        if c == m:
            break
        a = a[:(b - 1)]

    print (sys.executable)
    if sys.executable == a + 'python.exe':
        cmdL=True
    elif 'WinPython' in sys.executable:
        cmdL=True
    elif 'Anaconda' in sys.executable:
        cmdL=True
    else:
        cmdL=False
    return (cmdL)

def main():
    GRIDCONTS = 'GridDump'
    RowsNumConts = 'RowsNum'
    ColsNumConts = 'ColsNum'
    HeadsFileConts = 'HeadsFile'
    InputFileConts = 'InputFile'
    OutNameConts = 'OutName'
    RowsNum = 0
    ColsNum = 0
    ControlFileLoc = ""
    Stations = dict()
    RunsOptions = dict()
    HeadsDict = dict()
    tempOutName = ""

    cmdLine = checkExec_env()
    if cmdLine:
        print('Runnable with multiple processors')
    else:
        print('Unable to run with multiple processors')
    platform = (None, 'mp')[cmdLine]

    #platform='sp'
    #platform= 'mp'
    arg1 = sys.argv[1:]


    if len(arg1) < 2:
    #
    #   GUI to select ControlFile if not provided on command line
    #
      title ="Make Hydrographs and Duraction Curves"
      namMsg = "Please locate and select a ControlFile"
      reply = None
      while True:
        if len(arg1) < 2:
          ftypes = ["*.dat", ["*.txt","*.log","Non Standard Namefiles"]]
          reply = ez.fileopenbox(msg=namMsg,title=title,
                             default='*', filetypes=ftypes)
        else:
          break
        if reply:
          break
      if reply:
        arg1[0] = reply
      print ("{} has been selected as the ControlFile."\
             .format(arg1[0]))
   # print(arg1,len(arg1))
    if len(arg1) == 1:
        (path, namfile) = os.path.split(arg1[0])
        if path == '':
          print ("""Explicit path missing from {}
                Using default path for testing""".format(namfile))
          path = 'H:\\'
    else:
        print ("""Unable to process ControlFile data without file location
        details.
        """)
        exit()

    if len(arg1) > 0:
        ControlFileLoc = arg1[0]
    else:
        print('EasyGui failed to identify control file.  Using defaults')
        ControlFileLoc = r'\\ad.sfwmd.gov\dfsroot\data\wsd\MOD\kr\pmg\controlHyroDur.dat'


    ControlFile = open(ControlFileLoc, 'r')
    for line in ControlFile:
        if not line in ['\n', '\r\n']:
            values = line.split()
        if values[0].strip() == GRIDCONTS:
            tempGDfile = open(values[1], 'r')
            tempString = tempGDfile.read()
            TempDump = tempString.split()
        if values[0].strip() == RowsNumConts:
            RowsNum = values[1]
        if values[0].strip() == ColsNumConts:
            print(values[1])
            ColsNum = values[1]
        if values[0].strip() == InputFileConts:
            InputFile = open(values[1], 'r')
        if values[0].strip() == HeadsFileConts:
            print(values[1])
            HeadsDict[values[1]] = values[2]
            options = [values[3], values[4] ,values[5]]
            RunsOptions[values[1]] = options
        if values[0].strip() == OutNameConts:
            tempOutName = values[1]

    GridDump = [float(g)for g in TempDump]
    Grid = np.reshape(GridDump,(int(RowsNum),int(ColsNum)))
    #rid = np.reshape(GridDump,(292,408))
    for line in InputFile:
        values = line.split()
        if values[0].upper() != 'STATION':
            Station = values[0]
            Row = int(values[1])
            Col = int(values[2])
            topo = Grid[Row-1,Col-1]
            Stations[Station] = topo
   #         print(Station, Row, Col, topo, Stations[Station])
    headsbyRun = dict()
    for Run,File in HeadsDict.items():
        HeadsFile = open(File,'r')
        pdData =pd.read_csv(HeadsFile)
        headsbyRun[Run]=pdData


    AllrPool=[]

    AllrPool.append(compileFigs(platform,headsbyRun,Stations,RunsOptions,tempOutName))

    if platform == 'mp':
    	for rPool in reversed(AllrPool):
    		for rp in rPool:
                    rp.wait()
    	print("Figure Creation process completed")

    print('Done')

if __name__ == "__main__":
    result_list =[]
    main()
