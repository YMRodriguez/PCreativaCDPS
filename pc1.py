'''
Created on 16 nov. 2020

@author: yamil.mateo.rodriguez
'''
from subprocess import call
import sys
import logging
import configparser
import os 

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pc1')

config = configparser.ConfigParser()

def setUpConfigFile( nServers, nClients, nLB ):
    config['VARIABLES'] = {'num_serv' : nServers,
                           'num_client' : nClients,
                           'num_lb': nLB}
    with open('pc1.cfg', 'w') as configfile:
        config.write(configfile)


#Find number of servers 
def findNServ():
    config.read('pc1.cfg')
    num_serv = config['VARIABLES']['num_serv']
    return num_serv

#Find number of clients
def findNCli():
    config.read('pc1.cfg')
    num_client = config['VARIABLES']['num_client']
    return num_client

#Find number of load balancers 
def findNLoadBalanc():
    config.read('pc1.cfg')
    num_lb = config['VARIABLES']['num_lb']
    return num_lb

#Set configuration for either the start, the stop or the release order
def setConfig(order):
    setUpConfigFile(3, 1, 1)
    num = [findNServ(), findNCli(), findNLoadBalanc()]
    words = ["s", "c", "lb"]
    for m,n in zip(num, words):
        for i in range (1,int(m)):
            call (["sudo", "virsh", f"{order}", f"{n}{i}"])
            
#Open virtual machine consoles
def openConsoles():
    num = [findNServ(), findNCli(), findNLoadBalanc()]
    words = ["s", "c", "lb"]
    for m,n in zip(num, words):
        for i in range (1,int(m)): 
            os.system(f"xterm -e \'sudo virsh console {n}{i}\'&")
            
#Set configuration to either start or stop a single virtual machine
def setUpOne(order, vm, identifier):
    num = [findNServ(), findNCli(), findNLoadBalanc()]
    words = ["s", "c", "lb"]
    for m,n in zip(num, words):
        if vm == n:
            if identifier <= m:
                break
            else:
                print("The parameter does not match any of the identifiers.")
    call (["sudo", "virsh", f"{order}", f"{vm}{identifier}"])
    if order == "start":
        os.system(f"xterm -e \'sudo virsh console {vm}{identifier}\'&")
        
#Start virtual machines and show their consoles
def startOrder():
    call(["sudo", "virt-manager"])
    if len(sys.argv[2])>1 & len(sys.argv[3])>1:
        setUpOne("start",sys.argv[2], sys.argv[3])
    elif len(sys.argv[2])<1 & len(sys.argv[3])<1:
        setConfig("start")
        openConsoles()
    else:
        print("The parameters do not match any of the established patterns.")

#Stop virtual machines saving their current state
def stopOrder():
    call(["sudo", "virt-manager"])
    if len(sys.argv[2])>1 & len(sys.argv[3])>1:
        setUpOne("shutdown",sys.argv[2], sys.argv[3])
    elif len(sys.argv[2])<1 & len(sys.argv[3])<1:
        setConfig("shutdown")
    else:
        print("The parameters do not match any of the established patterns.")

#Delete all created files releasing the practice's scenario
def releaseOrder():
    call(["sudo", "virt-manager"])
    setConfig("destroy")
    
    
#if sys.argv[1] == "create":
#    createOrder()
if sys.argv[1] == "start":
    startOrder()
if sys.argv[1] == "stop":
    stopOrder()
if sys.argv[1] == "release":
    releaseOrder()
    


    
    