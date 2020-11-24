'''
Created on 16 nov. 2020

@author: yamil.mateo.rodriguez
'''
from subprocess import call
import sys
import logging
import configparser

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pc1')

config = configparser.ConfigParser()

#Find number of servers 
def findNServ():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"])
    num_serv = config['pc1.cfg']['num_serv']
    return num_serv

#Find number of clients
def findNCli():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"])
    num_client = config['pc1.cfg']['num_client']
    return num_client

#Find number of load balancers 
def findNLoadBalanc():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"])
    num_lb = config['pc1.cfg']['num_lb']
    return num_lb

#Set configuration for either the start, the stop or the release order
def setConfig(order):
    num = [findNServ(), findNCli(), findNLoadBalanc()]
    words = ["s", "c", "lb"]
    for m,n in zip(num, words):
        for i in range (0,m+1):
            call (["sudo", "virsh", f"{order}", f"{n}{i}"])
            
#Open virtual machine consoles
def openConsoles():
    num = [findNServ(), findNCli(), findNLoadBalanc()]
    words = ["s", "c", "lb"]
    for m,n in zip(num, words):
        for i in range (0,m+1): 
            call(["nohup","xterm", "-e", """ "sudo """, "virsh", "console", f""" {n}{i}" """, "&"])
        
#Start virtual machines and show their consoles
def startOrder():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"])
    call(["sudo", "virt-manager"])
    setConfig("start")
    

#Stop virtual machines saving their current state
def stopOrder():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"])
    call(["sudo", "virt-manager"])
    setConfig("stop")

#Delete all created files releasing the practice's scenario
def releaseOrder():
    call(["sudo", "cd", ""])
    call(["sudo", "cd", "/CDPS/PCreativaCDPS"]) 
    call(["sudo", "virt-manager"])
    setConfig("release")
    openConsoles()
    
    
#if sys.argv[1] == "create":
#    createOrder()
if sys.argv[1] == "start":
    startOrder()
if sys.argv[1] == "stop":
    stopOrder()
if sys.argv[1] == "release":
    releaseOrder()
    
    