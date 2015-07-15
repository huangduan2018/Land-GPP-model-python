__author__ = 'swei'
import numpy as np
import pandas as pd
import scipy.misc as sm
from scipy.ndimage import zoom
from scipy.io import netcdf
from scipy import io
from sklearn import tree
from sklearn.datasets import load_iris
from sklearn.externals.six import StringIO
import os
import pydot
import glob
from pyhdf import SD
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier,DecisionTreeRegressor


class GridData():
    def __init__(self,filenum):
        self.filenum=filenum

    def temperature(self):
        f = netcdf.netcdf_file(r"G:\Research\Gridded Data\NC\NC_data\air.mon.mean.nc", 'r')
        var = f.variables['air']
        id = self.filenum + 624
        data = var.data[id,:,:]
        temp = data * var.scale_factor + var.add_offset
        ta = np.zeros((360 , 720) , dtype = float)
        ta[: , 360:] = temp[: , :360]
        ta[: , :360] = temp[: , 360:]
        return ta[: , :]

    def fPAR(self,month,year):
        '''fPar is an unitless value ranging from 0 to 1, with monthly step and 0.5 x 0.5 spatial resolution'''
        month=month
        hdf_files = glob.glob(r'G:\Research\Gridded Data\Vegetation Index\LAI and FPAR\fPAR200{0}\*HDF'.format(year))
        cnt = 0
        for fn in hdf_files:
            if fn.endswith('HDF'):
                cnt += 1
                if cnt == int(month) + 1:
                    # print cnt
                    data = SD.SD(fn).select('fapar').get()
                    data = np.ma.masked_where(data == 255, data) / 255.0
                    return data

    def evi(self):
        '''fPar is an unitless value ranging from 0 to 1, with monthly step and 0.5 x 0.5 spatial resolution'''
        hdf_files = glob.glob(r'G:\Research\Gridded Data\Vegetation Index\EVI\*.hdf')
        id=self.filenum
        data = SD.SD(hdf_files[id]).select('CMG 0.05 Deg Monthly EVI').get() * 0.0001
        data = sm.imresize(data, [360, 720], interp='nearest') / 255.0
        evi_data= np.ma.masked_where(data == 0, data)
        return evi_data

    def precip(self):
        f = netcdf.netcdf_file(r'G:\Research\Gridded Data\NC\NC_data\precip.mon.mean.0.5x0.5.nc', 'r')
        # print f.dimensions,f.references
        var = f.variables['precip']
        id=self.filenum+624
        data = var.data[id, :, :].squeeze()
        pre = np.zeros((360, 720), dtype=float)
        pre[:, 360:] = data[:, :360]
        pre[:, :360] = data[:, 360:]
        pre = np.ma.masked_where(pre < -10000, pre)
        return pre

    def par(self):
        '''long_name: Monthly Mean of Net Shortwave Radiation Flux
        units: W/m^2; precision: 1'''
        f = netcdf.netcdf_file(r'G:\Research\Gridded Data\NC\NC_data\nswrs.sfc.mon.mean.nc', 'r')
        var = f.variables['nswrs']
        id = self.filenum + 636
        # Par is considered as 45% of the net shortwave radiation, divided by 11.58 to get MJ
        data = var[id , : , :] * 0.45
        #  Resize the data into 0.5x0.5 degree ([360,720])
        sr = -zoom(data[: , :] , [360 / 94.0 , 720 / 192.0] , mode='nearest')
        return sr

    def kp(self):
        kopTyp=np.load(r'G:\Research\Gridded Data\Koppen Climate\kg.npy')
        return kopTyp

    def pft(self):
        lc = io.loadmat('G:\Research\Gridded Data\PDSI\lc.mat')['lc']
        return lc


class TowerAlpha():

    def getAlpha(self, df):
        df = df.ix[:, 1:]
        df.ix[:, 5] = df.ix[:, 5].fillna(0)
        df.ix[:, 16] = df.ix[:, 16].fillna(0)
        for i in range(len(df.index)):
            df.ix[i, 5:] = df.ix[i, 5:].fillna(df.ix[i, 5:].mean())

        # df.ix[:, 5:] = df.ix[:, 5:].interpolate(method='linear', axis=1).copy()
        lats = df.Latitude
        lons = df.Longitude
        gpp = {}
        for site in df.index:
            gpp[site] = df.ix[site, 5:].as_matrix()
        return gpp, lats, lons

def gridToPoint(lats, lons):
    lat_ind=[]
    lon_ind=[]
    for lat in lats:
        if -90 <= lat <= 90:
            lat = 90 -lat
            ind = int(lat // 0.5)
            lat_ind.append(ind)
    for lon in lons:
        if -180 <= lon <= 180:
            lon += 180
            ind = int(lon // 0.5)
            lon_ind.append(ind)
    return lat_ind, lon_ind


df = pd.read_csv(r"G:\Research\modelling\machine learning\complete_info_alpha.csv", header=0, index_col=1)
evi=[]
pre=[]
ra=[]
ta=[]
fpar=[]
pft=[]
kp=[]
target=[]


total_GPP=0
T = TowerAlpha()
gpp,lats,lons= T.getAlpha(df)

sitNam=gpp.keys()
lat_ind,lon_ind=gridToPoint(lats,lons)


for year in range(2003,2006):
    for month in range(1,13):
        filenum=(year-2000)*12+month-1
        G=GridData(filenum)
        preGri=G.precip()
        eviGri=G.evi()
        taGri=G.temperature()
        fpaGri=G.fPAR(month-1,year-2000)
        raGri=G.par()
        kpGri=G.kp()
        pftGri=G.pft()
        siteNum=0
        for site in sitNam:
            target.append(gpp[site][month-1])
            (r,c)=zip(lat_ind,lon_ind)[siteNum]       
            if eviGri[r,c] is np.ma.masked or fpaGri[r,c] is np.ma.masked:
               target.pop(-1)
            else:                 
                pre.append(preGri[r,c])
                evi.append(eviGri[r,c])
                ra.append(raGri[r,c])
                ta.append(taGri[r,c])
                kp.append(kpGri[r,c])
                fpar.append(fpaGri[r,c])
                pft.append(pftGri[r,c])
            siteNum+=1
        del preGri,eviGri,taGri,fpaGri,raGri,kpGri,pftGri

features = np.zeros([len(pre), 7], dtype=float)
features[:,0]=pre
features[:,1]=evi
features[:,2]=ra
features[:,3]=ta
features[:,4]=kp
features[:,5]=fpar
features[:,6]=pft            

    
clf=DecisionTreeRegressor()
clf=clf.fit(features,target)
# results=clf.predict(features)
# plt.plot(target,results,'*')
# plt.show()
del features
output=np.zeros([360,720],dtype=float)
for r in range(360):
   for  c in range(720):
       eviPre=[]
       prePre=[]
       taPre=[]
       fpaPre=[]
       raPre=[]
       kpPre=[]
       pftPre=[]
       for year in range(2000, 2003):
            for month in range(1, 13):
                filenum = (year - 2000) * 12 + month - 1
                G = GridData(filenum)
                prePre.append(G.precip()[r,c])
                eviPre.append(G.evi()[r,c])
                taPre.append(G.temperature()[r,c])
                fpaPre.append(G.fPAR(month - 1, year - 2000)[r,c])
                raPre.append(G.par()[r,c])
                kpPre.append(G.kp()[r,c])
                pftPre.append(G.pft()[r,c])

       features=np.zeros([3*12,7],dtype=float)
       features[:, 0] = prePre
       features[:, 1] = eviPre
       features[:, 2] = raPre
       features[:, 3] = taPre
       features[:, 4] = kpPre
       features[:, 5] = fpaPre
       features[:, 6] = pftPre
       output[r,c]=clf.predict(features)

plt.imshow(output)
plt.colorbar()
plt.show()