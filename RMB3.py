"""
..alias::  RMB3
..module:: ReadModflowBinaryV3
  :
  :    -gui  Entering this optional argument will provide
  :          a Graphical User Interface for all command line arguments
  :
  :synopsis: Read Modflow Binary and create rasters and features
  ::created: 13-Sep-2013
  ::Recent mods: 02-12-2020
  ::Recent mods: 06-30-2021 option to write out ascii file added (BM)
  ::Recent mods: 03/29/2022 multiprocessing experimentation
  ::Alias of RMB2 developed: 06-12-2020
  ::Author: Kevin A. Rodberg <krodberg@sfwmd.gov>

"""
import RMFB.ReadModflowBinaryV3 as RMB

if __name__ == "__main__":
    RMB.main()