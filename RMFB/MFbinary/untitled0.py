# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 09:41:38 2020

@author: krodberg
"""

import numpy as np

fFaceSlice = [100,200,150]
rFaceSlice = [-200,-100,-350]
tmpdirArray = np.arctan2(fFaceSlice,rFaceSlice)*180 / np.pi
dirArray = np.where(tmpdirArray > 0.0,tmpdirArray,(tmpdirArray+360.0))
magArray = np.power((np.power(fFaceSlice,2)+np.power(rFaceSlice,2)),.5)