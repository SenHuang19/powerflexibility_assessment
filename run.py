import os
import subprocess
import time
from shutil import copyfile


modelPath='BUILDING11.idf'
weatherPath='USA_WA_Pasco-Tri.Cities.AP.727845_TMY3.epw'

os.environ['BCVTB_HOME']='bcvtb'

cmdStr="energyplus -w \"%s\" -r \"%s\"" % (weatherPath, modelPath)

sock=subprocess.Popen('python master_nn.py', shell=True)
simulation = subprocess.Popen(cmdStr, shell=True)

time.sleep(50000)
simulation.terminate()
sock.terminate()
