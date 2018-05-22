import numpy as np
binfilename = '//whqhpc01p/hpcc_shared/krodberg/LRWRP_DUMRUN_1/fort.91'
nrows = 292
ncols = 408
knt= int(nrows)*int(ncols)
binfile=open(binfilename, 'rb')
shape = (nrows,ncols)
Hdr = np.dtype([("KSTP","<i4"),("KPER","<i4"),("PERTIM","<f4"),("TOTIM", "<f4"),("TEXT","S16"),("NC","<i4"), ("NR","<i4"),("K","<i4")])
MFhdr  = []
MFhdr  = np.fromfile(binfile,Hdr,count=1,sep='')
print MFhdr  
read_data = np.fromfile(file=binfile, dtype=np.float32,count=knt, sep='').reshape(shape)
# print heads for column 301 for each row
print "output all rows for columns 301"
for rowRead in read_data:
    idCol = 300
    print rowRead[idCol]
print "output columns for row 101"
for allCols in range(ncols):
    idRow = 100
    print read_data[idRow][allCols]
print "output just row 101,col 301"
print read_data[idRow][idCol]