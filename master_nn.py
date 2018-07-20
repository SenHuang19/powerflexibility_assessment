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
import os
import subprocess
import time
from shutil import copyfile



def clamp(value, x1, x2):
        minValue = min(x1, x2)
        maxValue = max(x1, x2)
        return min(max(value, minValue), maxValue)


def ease(target, current, limit):
        return current - np.sign(current-target)*min(abs(current-target), abs(limit))

def geomFromCurve(curve):
        c = curve.tuppleize()
        # Sort by quantity. Should already be sorted, but just in case...
        c.sort(key=lambda t: t[1])
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
#            print qLoad
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
          port=47573
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
	
def create_demand_curve0(x,tIn,tout,tSup,mDot):
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
    t = clamp(zone.tIn+zone.tDel, zone.tMinAdj, zone.tMaxAdj)
    qlow=clamp(zone.getQ(t), zone.qMax, zone.qMin)
    t = clamp(zone.tIn-zone.tDel, zone.tMinAdj, zone.tMaxAdj)
    qhig=clamp(zone.getQ(t), zone.qMax, zone.qMin)
    curve = PolyLine()
    curve.add(Point(qlow, 100))
    curve.add(Point(qhig, 10))
    return curve				  

def create_demand_curve(x,tIn,tout,tSup,mDot,idex):
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
    zone.k=info['properties']['k']		
    zone.tIn=tIn	
    zone.tout=tout
    zone.mDot=mDot
    zone.qHvacSens = round(zone.mDot,2)*1006.*(tSup-zone.tIn)
    zone.qMin = min(0, zone.mDotMin*1006.*(tSup-zone.tMinAdj))
    zone.qMax = min(0, zone.mDotMax*1006.*(tSup-zone.tMaxAdj))
    curve = PolyLine()
    tHig=zone.tMaxAdj
    tLow=zone.tMinAdj
    phig=0.15+zone.k*0.01
    plow=0.15-zone.k*0.01
    price=[]
    quantity=[]
    p=0.0
    price.append(0.0)
    q=clamp(zone.getQ(tLow), zone.qMax, zone.qMin)
    quantity.append(q)
    curve.add(Point(q, p))	
    for i in range(101):
            p=(phig-plow)/100*float(i)+plow
            price.append(p)
            t=(tHig-tLow)/100*float(i)+tLow

            q=clamp(zone.getQ(t), zone.qMax, zone.qMin)
            quantity.append(q)
            curve.add(Point(q, p))
    p=1.0
    price.append(1.0)
    q=clamp(zone.getQ(tHig), zone.qMax, zone.qMin)
    quantity.append(q)
    curve.add(Point(q, p))			
    tab=pd.DataFrame()
    tab['price']=price
    tab['quantity']=quantity
    tab.to_csv('dc_zone/'+str(x)+'_'+str(idex)+'.csv')
    return curve
	
def create_demand_curve2(x,tIn,tout,tSup,mDot,idex):
#    print 'vav-'+str(x)
    info = json.load(open('vav-'+str(x)))
    k=info['properties']['k']
    phig=0.15+k*0.01
    plow=0.15-k*0.01
    price=[]
    quantity=[]
    s=0
    curve = PolyLine()
    tab2=pd.read_csv('result_1min/eplusout_'+str(idex)+'_'+str(190)+'.csv')
          
    tin='ZONE-VAV-'+str(x)+':Zone Mean Air Temperature [C](TimeStep)'

    tout='Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)'

    mdot='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Mass Flow Rate [kg/s](TimeStep)'

    tsup='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Temperature [C](TimeStep)'
    tab2['qHvacSens']=1006*tab2[mdot]*(tab2[tsup]-tab2[tin])
    q=0
    for i in range(idex*5+1, (idex+1)*5+1):
	        q=q+tab2['qHvacSens'].iloc[i]

    quantity.append(q/5)
    price.append(0)
    curve.add(Point(q/5, 0))
    for i in range(190,235,5): 
            
          tab2=pd.read_csv('result_1min/eplusout_'+str(idex)+'_'+str(i)+'.csv')
          
          tin='ZONE-VAV-'+str(x)+':Zone Mean Air Temperature [C](TimeStep)'

          tout='Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)'

          mdot='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Mass Flow Rate [kg/s](TimeStep)'

          tsup='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Temperature [C](TimeStep)'
          tab2['qHvacSens']=1006*tab2[mdot]*(tab2[tsup]-tab2[tin])
          q=0
          for k in range(idex*5+1, (idex+1)*5+1):
              q=q+tab2['qHvacSens'].iloc[k]

          quantity.append(q/5)
          p=(phig-plow)/8*float(s)+plow
          price.append(p)
          s=s+1
          curve.add(Point(q/5, p))

    p=1.0
    price.append(1.0)
    quantity.append(q/5)
    curve.add(Point(q/5, p))
    tab=pd.DataFrame()
    tab['price']=price
    tab['quantity']=quantity
    tab.to_csv('dc_zone/'+str(x)+'_'+str(idex)+'.csv')
    
    return curve


def create_demand_curve3(x,tIn,tout,tSup,mDot,idex):
#    print 'vav-'+str(x)
    info = json.load(open('vav-'+str(x)))



    curve = PolyLine()

    tab=pd.read_csv('dc_zone/'+str(x)+'_'+str(idex)+'.csv')
    for i in range(len(tab)):
                 price=tab['price'].iloc[i]
                 quantity=tab['quantity'].iloc[i]
                 curve.add(Point(quantity, price))				 
    
    return curve

def create_demand_curve4(x,tIn,tout,tSup,mDot,idex):
#    print 'vav-'+str(x)
    info = json.load(open('vav-'+str(x)))
    curve = PolyLine()
    min=100
    min_index=0
    for i in range(190,235,5):
          if abs(i/10.0-tIn)<min:
                  min_index=i
                  min=abs(i/10.0-tIn)
        
    print min_index
    tab=pd.read_csv('dz_zone/'+str(x)+'_'+str(idex)+'_'+str(min_index)+'.csv')
    for i in range(len(tab)):
                 price=tab['price'].iloc[i]
                 quantity=tab['quantity'].iloc[i]
                 curve.add(Point(quantity, price))				 
    return curve
    
    
    
def run_simulation(index,setpoint):
    index=index/5
    path=os.getcwd()
    print path
    modelPath=path+'/new_curves/BUILDING11.idf'
    weatherPath=path+'/new_curves/USA_WA_Pasco-Tri.Cities.AP.727845_TMY3.epw'
    os.environ['BCVTB_HOME']=path+'/new_curves/bcvtb'
    os.chdir(path+'/new_curves')
    cmdStr= "energyplus -w \"%s\" -r \"%s\"" % (weatherPath, modelPath)
    simulation = subprocess.Popen(cmdStr, shell=False)
    sock=subprocess.Popen('python '+path+'/new_curves/master_train2.py ' + str(float(setpoint)/10.0), shell=False)
    sock.wait()
    sock.terminate()
    copyfile(path+'/new_curves/eplusout.csv', path+'/temp/eplusout_'+str(index)+'_'+str(setpoint)+'.csv')
    os.chdir(path)


def process_data(index):

    index=index/5
    VAV_index1=['102', '118', '119', '120', '123a', '123b', '127a','corridor', '127b', '129', '131', '136', '133', '142', '143', '150', 'restroom']
    for st in range(len(VAV_index1)):
        x=VAV_index1[st].upper()
        info = json.load(open('vav-'+str(x)))
        k=info['properties']['k']
        phig=0.15+k*0.01
        plow=0.15-k*0.01
        price=[]
        quantity=[]
        s=0
        curve = PolyLine()
        
        tab2=pd.read_csv('temp/eplusout_'+str(index)+'_'+str(-5)+'.csv')
          
        tin='ZONE-VAV-'+str(x)+':Zone Mean Air Temperature [C](TimeStep)'

        tout='Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)'

        mdot='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Mass Flow Rate [kg/s](TimeStep)'

        tsup='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Temperature [C](TimeStep)'
        tab2['qHvacSens']=1006*tab2[mdot]*(tab2[tsup]-tab2[tin])
        q=0
        for i in range(index*5+1, (index+1)*5+1):
	        q=q+tab2['qHvacSens'].iloc[i]

        quantity.append(q/5)
        price.append(0)
        curve.add(Point(q/5, 0))
        for i in range(0,10,5): 
            
               tab2=pd.read_csv('temp/eplusout_'+str(index)+'_'+str(i)+'.csv')
          
               tin='ZONE-VAV-'+str(x)+':Zone Mean Air Temperature [C](TimeStep)'

               tout='Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep)'

               mdot='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Mass Flow Rate [kg/s](TimeStep)'

               tsup='ZONE-VAV-'+str(x)+' VAV BOX OUTLET NODE:System Node Temperature [C](TimeStep)'
               tab2['qHvacSens']=1006*tab2[mdot]*(tab2[tsup]-tab2[tin])
               q=0
               for k in range(index*5+1, (index+1)*5+1):
                            q=q+tab2['qHvacSens'].iloc[k]

               quantity.append(q/5)
               p=(phig-plow)/2*float(s)+plow
               price.append(p)
               s=s+1
               curve.add(Point(q/5, p))

        p=1.0
        price.append(1.0)
        quantity.append(q/5)
        curve.add(Point(q/5, p))
        tab=pd.DataFrame()
        tab['price']=price
        tab['quantity']=quantity
        tab.to_csv('dc_zone/'+str(x)+'_'+str(index)+'.csv')
    





	

def create_demand_curve5(x,tIn,tout,tSup,mDot,idex):
#    print 'vav-'+str(x)
    info = json.load(open('vav-'+str(x)))
    curve = PolyLine()
    min=100
    min_index=0
    for i in range(190,235,5):
          if abs(i/10.0-tIn)<min:
                  min_index=i
                  min=abs(i/10.0-tIn)
        
    print min_index
    tab=pd.read_csv('dz_zone/'+str(x)+'_'+str(idex)+'_'+str(min_index)+'.csv')
    for i in range(len(tab)):
                 price=tab['price'].iloc[i]
                 quantity=tab['quantity'].iloc[i]
                 curve.add(Point(quantity, price))				 
    return curve        


def convert_demand_curve(x,tret,tsup,tmix,demandCurve,idex):
    info = json.load(open('AHU-00'+str(x)))
    ahu=AhuChiller()
    ahu.tAirReturn = tret
    ahu.tAirSupply = tsup
    ahu.tAirMixed = tmix
#    print demandCurve.points

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



def updateTset(x,tIn,tout,tSup,mDot,demandCurve,pClear):
    info = json.load(open('vav-'+str(x)))
    zone=FirstOrderZone()
    zone.tIn=tIn	
    zone.tout=tout
    zone.mDot=mDot
    zone.mDotMin=info['properties']['mDotMin']	
    zone.mDotMax=info['properties']['mDotMax']
    zone.tMinAdj=info['properties']['tMin']
    zone.tMaxAdj=info['properties']['tMax']		
    zone.qHvacSens = round(zone.mDot,2)*1006.*(tSup-zone.tIn)
    zone.qMin = min(0, zone.mDotMin*1006.*(tSup-zone.tMinAdj))
    zone.qMax = min(0, zone.mDotMax*1006.*(tSup-zone.tMaxAdj))
    zone.c0=info['properties']['c0']
    zone.c1=info['properties']['c1']
    zone.c2=info['properties']['c2']
    zone.c3=info['properties']['c3']
    zone.c4=info['properties']['c4']


    zone.tMinAdj=info['properties']['tMin']
    zone.tMaxAdj=info['properties']['tMax']
    zone.tNomAdj=info['properties']['tIn']
    zone.k=info['properties']['k']		
    tHig=zone.tIn+0.5
    tLow=zone.tIn-0.5
    phig=0.15+zone.k*0.01
    plow=0.15-zone.k*0.01
    tSet =(tHig-tLow)/(phig-plow)*(pClear-plow)+tLow
    tSet =clamp(tSet,zone.tMinAdj,zone.tMaxAdj)
#    qClear = clamp(demandCurve.x(pClear), zone.qMax, zone.qMin)
#    qClear=demandCurve.x(pClear)
    for point in demandCurve.points:
            if abs(float(point.y)-float(pClear))<0.01 or not (float(point.y)<float(pClear)):
                  qClear=point.x
                  break
#            print ahu.calcTotalLoad(point.x)
    return tSet,qClear

	
#import matlab.engine

### start the matlab engine (optional)

#eng = matlab.engine.start_matlab()

server=socket_server()
content='T0'

for i in range(1,25):
    content=content+','+'T'+str(i)

for i in range(21):
    content=content+','+'L'+str(i)	
	
f=open('setpoint.csv','w')
f.writelines(content+'\n')
f.close()

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
for s in range(len(index)):

                               f=open(str(VAV_index1[s])+'.csv','w')
                               f.close()				 
				 
#print index
tset=[21]*25
lights=[0]*21
conn,addr=server.sock.accept()
prices=[]
power_hig=[]
power_low=[]
power=[]
price_base=0.15
price_temp=price_base
debug=True
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
#                 tab['power']=power				 
                 tab.to_csv('price.csv')
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
              if float(arry[-1])>0 and (idex%5 == 0) and (idex/5 > 62) and (idex/5 < 205): 

                   for i in range(-5,10,5):
                                             run_simulation(idex,i)
                   process_data(idex)
                   validSells=[]
                   tmin=[]
                   tmax=[]
                   for s in range(len(index)):
                          tIn=float(setpoints[index[s]])
                          tSup=float(zdt[index[s]])
                          mDot=float(zdm[index[s]])
                          x= create_demand_curve3(vavs[index[s]],tIn,tout,tSup,mDot,idex/5)
#                          x= create_demand_curve0(vavs[index[s]],tIn,tout,tSup,mDot)
                          validSells.append(x)
                   demandCurve = PolyLineFactory.combine(validSells, 100)
                   quantity=[]
                   price=[]
                   tab=pd.DataFrame()
                   for point in demandCurve.points:
                             quantity.append(point.x)
                             price.append(point.y)
                   tab['quantity']=quantity
                   tab['price']=price
                   tab.to_csv('demand_curve/'+str(idex/5)+'_aggregated.csv')	                   				   
                   z=convert_demand_curve(1,float(ahu1[0]),float(ahu1[1]),float(ahu1[3]),demandCurve,idex/5)	
                                 

				   
                   dc= geomFromCurve(z)
                   dc.append([0.0,1.0])
                   price=[]
                   quantity=[]				   
                   for i in range(len(dc)):
				        price.append(dc[i][1])
				        quantity.append(dc[i][0])				   
                   tab=pd.DataFrame()
                   tab['quantity']=quantity
                   tab['price']=price
                   tab.to_csv('demand_curve/'+str(idex/5)+'.csv')	
				   
				   
#                   print dc
                   power_low.append(dc[0][0])
                   power_hig.append(dc[-1][0])				   

#                   supplyCurve= PolyLine()


#                   supplyCurve.add(Point(0.0, 0.15))  			   
#                   supplyCurve.add(Point(6575.0, 0.15))				   
#                   supplyCurve.add(Point(6575.0, 3.0))
			   
				   
				  
                   limit=6000.0
#                   sc= geomFromCurve(supplyCurve)
#                   print sc
                   price=price_temp
                   if dc[0][0]<limit:

                         price = price_temp
#                         price_temp=price_temp*0.9
                   elif dc[-2][0]>limit:
				         price = 1				   
                   else:
				         for i in range(len(dc)-1,-1,-1):
						           if dc[i][0]>=limit:
                                                             price= dc[i+1][1]
                                                             break															 
				         if price<0.15:
				                   price=0.15
#                   intersection = PolyLine.intersection(dc, sc)


#                   price = intersection[1]
                   print price 
                   prices.append(price)
#                   if price is None:
#                         for i in range(len(dc)):
#                               if dc [i][0]>sc [0][0]:
#                                      price = dc[i][1]
#                                      break
#                               price = dc[-1][1]							   
#                   power.append(intersection[0])	  
									  
                   if debug:
                        for s in range(len(index)):
                               tIn=float(setpoints[index[s]])
                               tSup=float(zdt[index[s]])
                               mDot=float(zdm[index[s]])
                               tset[index[s]],qclear=updateTset(vavs[index[s]],tIn,tout,tSup,mDot,validSells[s],price)
							  
                               f=open(str(VAV_index1[s])+'.csv','a')
                               f.writelines(str(-qclear)+'\n')

                               f.close()
                   lights=[0]*21
              elif not(float(arry[-1])>0) or (idex/5 >= 205):      			  
                   tset=[21]*25
                   lights=[0]*21
                   
              mssg = '%r %r %r 0 0 %r' % (vers, flag, ePlusInputs, time)

              content=str(tset[0])
              for i in range(24):
                    content=content+','+str(tset[i])
                    
              for i in range(21):
                    content=content+','+str(lights[i])
                    
              f=open('setpoint.csv','a')
              f.writelines(content+'\n')			  
              f.close()

              for i in range(25):
                   mssg = mssg + ' ' + str(tset[i])
              for i in range(21):
	               mssg = mssg + ' ' + str(lights[i])
              mssg =  mssg+'\n'
#              print mssg
              conn.send(mssg)

#              print idex
#         conn.close()	
              idex=idex+1		 


	 

