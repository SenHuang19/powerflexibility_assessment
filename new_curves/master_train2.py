import socket
import time
import matlab.engine
import numpy as np
import sys
import random as rd
import json
from polyline import PolyLine, Point
from polyline import PolyLineFactory as PolyLineFactory, PolyLine as PolyLine
import pandas as pd


def clamp(value, x1, x2):
        minValue = min(x1, x2)
        maxValue = max(x1, x2)
        return min(max(value, minValue), maxValue)


def ease(target, current, limit):
        return current - np.sign(current-target)*min(abs(current-target), abs(limit))

def geomFromCurve(curve):
        c = curve.tuppleize()
        # Sort by quantity. Should already be sorted, but just in case...
        c.sort(key=lambda t: t[0])
#         first = c[0]
#         if first[0] > 0:
#             c.insert(0, [0,first[1]])
#         last = c[-1]
#         if xVal > 0 and last[1] < xVal:
#             c.append([last[0],xVal])
#         elif xVal < 0 and last[1] > xVal:
#             c.append([last[0],xVal])
        return c

class FirstOrderZone(object):
       
    def __init__(self):
        self.c0 = 0.3557725
        self.c1 = 0.9837171
        self.c2 = 0.002584267
        self.c3 = 0.0006142672
        self.c4 = 0.0006142672

        self.x0 = -162.6386
        self.x1 = -309.5303
        self.x2 = -4.800622
        self.x3 = 321.3943
        self.x4 = 0.9944429

        self.tOut = 20.
        self.tIn = 24.
        self.tSet = 21.11
        self.tDel = 0.25
        self.qHvacSens = 0.
        self.tMin = 22.
        self.tMax = 24.
        self.qMin = -1.
        self.qMax = -1000000.
        self.name = "FirstOrderZone"


    def getQ(self, T_new):
        qHvacNew = self.x0 + self.x1*round(self.tIn,2) + self.x2*round(self.tOut,2) + self.x3*round(T_new,2) + self.x4*round(self.qHvacSens,2)
        return round(qHvacNew,2)
    
    
    def calcMinCoolPower(self):
        # q values are negative, so this is confusing
        t = max(min((self.tSet+self.tDel), self.tMax), self.tMin)
        q = max(min(self.getQ(t), self.qMin), self.qMax)
        return q


    def calcMaxCoolPower(self):
        # q values are negative, so this is confusing
        t = min(max((self.tSet-self.tDel), self.tMin), self.tMax)
        q = max(min(self.getQ(t), self.qMin), self.qMax)
        return q


    def getT(self, qHvac):
        return round(self.c0 + self.c1*round(self.tIn,2) + self.c2*round(self.tOut,2) + self.c3*round(qHvac,2) + self.c4*round(self.qHvacSens,2),2)

class AhuChiller(object):
    
    
    def __init__(self):
        self.tAirReturn = 20.
        self.tAirSupply = 10.
        self.tAirMixed = 20.
        self.cpAir = 1006. # J/kg
        self.c0 = 0 # coefficients are for SEB fan
        self.c1 = 2.652E-01
        self.c2 = -1.874E-02
        self.c3 = 1.448E-02
        self.c4 = 0.
        self.c5 = 0.
        self.pFan = 0.
        self.mDotAir = 0.
        self.staticPressure = 0.
        self.coilLoad = 0.
        self.COP = 6.16
        self.name = 'AhuChiller'
        
        
    def calcAirFlowRate(self, qLoad):
        if self.tAirSupply == self.tAirReturn:
            self.mDotAir = 0.0
        else:
            self.mDotAir = abs(qLoad/self.cpAir/(self.tAirSupply-self.tAirReturn)) # kg/s


    def calcFanPower(self):
        self.pFan = (self.c0 + self.c1*self.mDotAir + self.c2*pow(self.mDotAir,2) + self.c3*pow(self.mDotAir,3) + self.c4*self.staticPressure + self.c5*pow(self.staticPressure,2))*1000. # watts


    def calcCoilLoad(self):
        coilLoad = self.mDotAir*self.cpAir*(self.tAirSupply-self.tAirMixed) # watts
        if coilLoad > 0: #heating mode is not yet supported!
            self.coilLoad = 0.0
        else:
            self.coilLoad = coilLoad
        
        
    def calcTotalLoad(self, qLoad):
        self.calcAirFlowRate(qLoad)
        return self.calcTotalPower()
    
    
    def calcTotalPower(self):
        self.calcFanPower()
        self.calcCoilLoad()
        return abs(self.coilLoad)/self.COP + self.pFan



#eng = matlab.engine.start_matlab()

class socket_server:

    def __init__(self):     
          self.sock=socket.socket()
          host=socket.gethostname()
          port=47574
          self.sock.bind(('127.0.0.1',port))
          self.sock.listen(10)

def data_parse(data): 
    data=data.replace('[','')     
    data=data.replace(']','')  	
    data=data.split(',')

    for i in range(len(data)):
	              data[i]=float(data[i])
         
    return data

def read_data(file_name): 
    reg=np.loadtxt(file_name)
    reg_ref=[abs(number) for number in reg]
    reg=reg/max(reg_ref)
    return reg

def data_parse(data): 
    data=data.replace('[','')     
    data=data.replace(']','')  	
    data=data.split(',')

    for i in range(len(data)):
	              data[i]=float(data[i])
         
    return data		
		  

def create_demand_curve(x,tIn,tout,tSup,mDot):
#    print 'vav-'+str(x)
    info = json.load(open('vav-'+str(x)))
    zone=FirstOrderZone()
    zone.x0=info['properties']['x0']
    zone.x1=info['properties']['x1']
    zone.x2=info['properties']['x2']
    zone.x3=info['properties']['x3']
    zone.x4=info['properties']['x4']
    zone.mDotMin=info['properties']['mDotMin']	
    zone.mDotMax=info['properties']['mDotMax']
    zone.tMinAdj=info['properties']['tMin']
    zone.tMaxAdj=info['properties']['tMax']		
    zone.tIn=tIn	
    zone.tout=tout
    zone.mDot=mDot
    zone.qHvacSens = round(zone.mDot,2)*1006.*(tSup-zone.tIn)
    zone.qMin = min(0, zone.mDotMin*1006.*(tSup-zone.tIn))
    zone.qMax = min(0, zone.mDotMax*1006.*(tSup-zone.tIn))
    curve = PolyLine()
    for i in range(10,110,5):
            tHig=zone.tIn+0.5
            tLow=zone.tIn-0.5			
            t=(tHig-tLow)/90*(float(i-10))+tLow
            q=clamp(zone.getQ(t), zone.qMax, zone.qMin)
            curve.add(Point(q, float(i)))   
    return curve

def convert_demand_curve(x,tret,tsup,tmix,demandCurve):
    info = json.load(open('AHU-00'+str(x)))
    ahu=AhuChiller()
    ahu.tAirReturn = tret
    ahu.tAirSupply = tsup
    ahu.tAirMixed = tmix
    ahu.c0=info['properties']['c0']
    ahu.c1=info['properties']['c1']
    ahu.c2=info['properties']['c2']
    ahu.c3=info['properties']['c3']
    ahu.COP=info['properties']['COP']
    curve = PolyLine()
    for point in demandCurve.points:
            curve.add(Point(ahu.calcTotalLoad(point.x), point.y))
#            print ahu.calcTotalLoad(point.x)
    return curve	


def updateTset(x,tIn,tout,tSup,mDot,demandCurve,pClear,Tset):
    info = json.load(open('vav-'+str(x)))
    zone=FirstOrderZone()
    zone.tIn=tIn	
    zone.tout=tout
    zone.mDot=mDot
    zone.mDotMin=info['properties']['mDotMin']	
    zone.mDotMax=info['properties']['mDotMax']
    zone.qHvacSens = round(zone.mDot,2)*1006.*(tSup-zone.tIn)
    zone.qMin = min(0, zone.mDotMin*1006.*(tSup-zone.tIn))
    zone.qMax = min(0, zone.mDotMax*1006.*(tSup-zone.tIn))
    zone.c0=info['properties']['c0']
    zone.c1=info['properties']['c1']
    zone.c2=info['properties']['c2']
    zone.c3=info['properties']['c3']
    zone.c4=info['properties']['c4']


    zone.tMinAdj=info['properties']['tMin']
    zone.tMaxAdj=info['properties']['tMax']
    zone.tNomAdj=info['properties']['tIn']		
    curve = PolyLine()
    if pClear is not None:
            tHig=zone.tIn+0.5
            tLow=zone.tIn-0.5			
            qClear = clamp(demandCurve.x(pClear), zone.qMax, zone.qMin)	
            tSet =(tHig-tLow)/90.0*(pClear-10.0)+tLow
    else:
            tSet = clamp(ease(zone.tNomAdj, Tset, 0.1), zone.tIn-zone.tDel, zone.tIn+zone.tDel)
            qClear=0
    tSet=clamp(tSet, zone.tMinAdj, zone.tMaxAdj)

    return tSet,qClear
	
#import matlab.engine

### start the matlab engine (optional)

#eng = matlab.engine.start_matlab()

server=socket_server()

### user define if the model is baseline 0 or 1

#num = int(raw_input("Baseline 0 or 1: (type 0 or 1) "))

#reg=read_data('Regulation.csv')

#print reg

#ides=[22,25,28,31,34]
	
vers = 2
flag = 0
ePlusInputs=46

idex=0
server.sock.listen(10)
vavs=['105','120','004','123A','142','CORRIDOR','129','102','112','119','002','123B','143','118','104','RESTROOM','131','136','108','116','150','133','107','127A','127B']

VAV_index1=['102', '118', '119', '120', '123a', '123b', '127a','corridor', '127b', '129', '131', '136', '133', '142', '143', '150', 'restroom']
index=[]
for i in range(len(VAV_index1)):
    for j in range(len(vavs)):
	     if vavs[j].lower().find(VAV_index1[i].lower())!=-1:
		         index.append(j)
		         break
			 
#print index
tset=[21]*25
conn,addr=server.sock.accept()
prices=[]
power_hig=[]
power_low=[]
power=[]
debug=True

sp_tab=pd.read_csv('setpoint.csv')
index_rec=len(sp_tab)




sp=float(sys.argv[1])
while 1:


### data received from dymola
         
         data = conn.recv(10240)
		 
#         print('I just got a connection from ', addr)

         data = data.rstrip()

         arry = data.split()
         flagt = float(arry[1])
         if flagt==1 and debug:
                 tab=pd.DataFrame()
                 tab['price']=prices
                 tab['power_hig']=power_hig
                 tab['power_low']=power_low	
                 tab['power']=power				 
                 tab.to_csv('price.csv')
                 conn.close()
                 sys.exit()
         if len(arry)>6:
#              print arry[-1]
              time=float(arry[5])
              setpoints=arry[6:6+25]
              liglevel=arry[6+25:6+25+21]
              ztemp=arry[6+25+21:6+25+21+25]
              zdt=arry[6+25+21+25:6+25+21+25+25]
              zdp=arry[6+25+21+25+25:6+25+21+25+25+21]
              ligP=arry[6+25+21+25+25+21:6+25+21+25+25+21+21]
              zdm=arry[6+25+21+25+25+21+21:6+25+21+25+25+21+21+25]
              ahu1=	arry[6+25+21+25+25+21+21+25:6+25+21+25+25+21+21+25+5]
              ahu2=	arry[6+25+21+25+25+21+21+25+5:6+25+21+25+25+21+21+25+10]
              ahu3=	arry[6+25+21+25+25+21+21+25+10:6+25+21+25+25+21+21+25+15]
              ahu4=	arry[6+25+21+25+25+21+21+25+15:6+25+21+25+25+21+21+25+20]
              total=arry[6+25+21+25+25+21+21+25+20]
              tout=arry[6+25+21+25+25+21+21+25+21]
              hour=arry[6+25+21+25+25+21+21+25+22]
#              print arry[-1] 
              if float(arry[-1])>0 and (idex>=index_rec and idex<index_rec+5): 
                   for s in range(len(index)): 
                                 tset[index[s]]=tset[index[s]]+sp                
              elif idex<index_rec: 
                   for s in range(len(index)): 
                                 tset[index[s]]=sp_tab['T'+str(s)].iloc[idex]    			  
                   lights=[0]*25
                   for s in range(len(index)):
                          f=open(str(VAV_index1[s])+'.csv','a')
                          f.writelines(str(0)+'\n')
                          f.close()				   
              mssg = '%r %r %r 0 0 %r' % (vers, flag, ePlusInputs, time)
			  
              for i in range(25):
                   mssg = mssg + ' ' + str(tset[i])
              for i in range(21):
	               mssg = mssg + ' ' + str(lights[i])
              mssg =  mssg+'\n'
#              print mssg
              conn.send(mssg)


#         conn.close()	
              idex=idex+1		 


	 

