'''
Created on 16 nov. 2020

@author: yamil.mateo.rodriguez 
@author: diego.garcia.fierro
'''
from subprocess import call
import sys
import logging
import configparser
from lxml import etree
import os
from _cffi_backend import string
import debinterface
from proofXMLeditor import editXML, createHostnameForMV,\
    createInterfacesFileForMV

# Logs administrator
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pc1')

# Configuration administrator
config = configparser.ConfigParser()
#-------------- Begin CREATE logic & functions -----------------------------------

# This is the main function for the order <create>
def createOrder(nServers=2, nClients=1, nLB=1):
    # Reformat given information
    nServers = int(nServers)
    nClients = int(nClients)
    nLB = int(nLB)
    
    # Check if within the limits
    if nServers < 1 and nServers > 5:
        logger.debug("Error in the amount of servers")
        raise ValueError("You must create from 1 to 5 servers")
    
    # Configure config File
    setUpConfigFile(nServers, nClients, nLB)
    
    # Extract the IDs of the machines in the environment
    machineImageIds = handleMVIds(nServers, nClients, nLB)
    
    # Create the qcow2 and the xml for each machine
    createMachineImages(machineImageIds)
    
    # Set up the LANs of the environment
    LANS = ["LAN1", "LAN2"]
    setUpBridges(LANS)
    
    print(machineImageIds)

    for i in machineImageIds:
        editXML(i, LANS)
    
    for i in machineImageIds:
        createHostnameForMV(i)
        createInterfacesFileForMV(i)
        
    for i in machineImageIds:
        setLbAsRouter(i)
    
    call(["sudo", "virt-manager"])
    print(machineImageIds)
    
    defineMVs(machineImageIds)

#----------Helpers------------------------------------------
# This function creates the list of IDs for the VMs  
def handleMVIds(nServers, nClients, nLB):
    ids = []
    for i in range(1, nServers +1):
        ids.append("s" + str(i)) 
    for i in range(1, nClients +1):
        ids.append("c" + str(i))
    for i in range(1, nLB +1):
        ids.append("lb" + str(i))
    return ids
      
# This function creates a pc1.cfg file and stores the needed variables into this file
def setUpConfigFile(nServers, nClients, nLB):
    config['VARIABLES'] = {'num_serv' : nServers,
                           'num_client' : nClients,
                           'num_lb': nLB}
    with open('pc1.cfg', 'w') as configfile:
        config.write(configfile)
    logger.debug("Config File created")
    
# This function edits an XML for a vm given its id
def editXML(id, LANS):
    # Create the parser to handle XML
    parser = etree.XMLParser(remove_blank_text=True)
    file = etree.parse("plantilla-vm-pc1.xml", parser)
    # Edit name and source file location
    file.find('/name').text = id
    file.find('/devices/disk/source').set('file', id + '.qcow2')
    # Edit network interfaces
    if 's' in id:
        file.find('/devices/interface/source').set('bridge', LANS[1]) 
    elif 'c' in id:
        file.find('/devices/interface/source').set('bridge', LANS[0])
    else:
        file.find('/devices/interface/source').set('bridge', LANS[0])
        newInterface = etree.Element('interface', type='bridge')
        source = etree.Element('source', bridge=LANS[1])
        model = etree.Element('model', type='virtio')
        newInterface.append(source)
        newInterface.append(model)
        file.find('/devices').append(newInterface)
    file.write(id + ".xml", pretty_print=True)
    logger.debug("XML edited")

# ----------- Machines--------------------------------------
# This function creates all the images from a given list of the machines    
def createMachineImages(ids):
    for i in ids:
        commandImage = "qemu-img create -f qcow2 -b cdps-vm-base-pc1.qcow2 " + i + ".qcow2"
        commandXML = "cp plantilla-vm-pc1.xml " + i + ".xml"
        call(commandImage.split(" "))
        call(commandXML.split(" "))
    logger.debug("MVs images created")

# This function defines all the virtual machines
def defineMVs(ids):
    for i in ids:
        print(i)
        command = "sudo virsh define " + i + ".xml"
        call(command.split(" "))

#-------------- Networks ----------------------------------
# This function creates the bridges from a given list of LAN
def setUpBridges(LANS):
    for i in LANS:
        addbrCommand = "sudo brctl addbr " + i
        ifconfigCommand = "sudo ifconfig " + i + " up"
        call(addbrCommand.split(" "))
        call(ifconfigCommand.split(" "))

# This function creates hostname file in the given mv id
def createHostnameForMV(id):
    filepath = os.path.join('/mnt/tmp', 'hostname')
    if not os.path.exists('/mnt/tmp'):
        logger.debug("tmp directory does not exists")
    f = open(filepath, "w+")
    f.write(id  + "/n")
    f.close()
    confCommand = "sudo virt-copy-in -a " + id + ".qcow2 /mnt/tmp/hostname /etc/"
    call(confCommand.split(" "))

# This function creates interfaces file in the given id
def createInterfacesFileForMV(id):
    filepath = os.path.join('/mnt/tmp', 'interfaces')
    if not os.path.exists('/mnt/tmp'):
        logger.debug("tmp directory does not exists")
    f = open(filepath, "w+")
    interfaces = debinterface.Interfaces(interfaces_path='/mnt/tmp/interfaces')
    
    numberDirIP = [int(i) for i in list(id) if i.isdigit()][0]
    if 's' in id:
        options = {
            'addrFam': 'inet',
        'broadcast': '10.0.2.255',
        'name': 'eth0',
        'up': [],
        'gateway': '10.0.2.1',
        'down': [],
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.2.1' + str(numberDirIP)
        }
        interfaces.addAdapter(options)
    if 'c' in id: #Aqui hay que ver como esquivar al host
        options = {
            'addrFam': 'inet',
        'broadcast': '10.0.1.255',
        'name': 'eth0',
        'up': [],
        'gateway': '10.0.1.1',
        'down': [],
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.1.' + str(numberDirIP)
        }
        interfaces.addAdapter(options)
    if 'lb' in id: #Hay que ver como hacerlo generico
        options = {
            'addrFam': 'inet',
        'broadcast': '10.0.1.255',
        'name': 'eth0',
        'up': [],
        'gateway': '10.0.1.1',
        'down': [],
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.1.1'
        }
        options2 = {
            'addrFam': 'inet',
        'broadcast': '10.0.2.255',
        'name': 'eth1',
        'up': [],
        'gateway': '10.0.2.1',
        'down': [],
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.2.1'
        }
        interfaces.addAdapter(options)
        interfaces.addAdapter(options2)
    
    interfaces.writeInterfaces()
    
    # Copiarlo dentro de la MV
    confCommand = "sudo virt-copy-in -a " + id + ".qcow2 /mnt/tmp/interfaces /etc/network"
    call(confCommand.split(" "))

# This function sets the lbs from the given list as routers
def setLbAsRouter(id):
    if 'lb' in id:
        command = "sudo virt-edit -a " + id + ".qcow2 /etc/sysctl.conf -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/'"
        call(command.split(" "))

#---------------- End CREATE logic & functions ---------------------
#-------------------------------------------------------

#---------------- Begin START logic --------------------
#Start virtual machines and show their consoles
def startOrder():
    nMVs = findNumberMachines()
    machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    for i in machineImageIds:
        setConfig("start", i)
    for i in machineImageIds:
        openConsoles(i)
    #map(lambda x: setConfig("start" , x), machineImageIds)
    #map(lambda x: openConsoles(x), machineImageIds)
# --------------- End START logic ----------------------
#-------------------------------------------------------

#---------------- Begin STOP logic --------------------
#Stop virtual machines saving their current state
def stopOrder():
    call(["sudo", "virt-manager"])
    nMVs = findNumberMachines()
    machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    for i in machineImageIds:
        setConfig("shutdown", i)
    #map(lambda x: setConfig("shutdown" , x), machineImageIds)
# --------------- End STOP logic ----------------------
#-------------------------------------------------------

#---------------- Begin RELEASE logic --------------------
#Delete all created files releasing the practice's scenario
def releaseOrder():
    call(["sudo", "virt-manager"])
    nMVs = findNumberMachines()
    machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    for i in machineImageIds:
        setConfig("destroy", i)
    #map(lambda x: setConfig("destroy" , x), machineImageIds)    
# --------------- End RELEASE logic ----------------------
#-------------------------------------------------------

#--------- Helpers for START, STOP, RELEASE----------------------
# This function get the amount of machines from the config file
def findNumberMachines():
    config.read('pc1.cfg')
    nServ = int(config['VARIABLES']['num_serv'])
    nCli = int(config['VARIABLES']['num_client'])
    nLb = int(config['VARIABLES']['num_lb'])
    return [nServ, nCli, nLb]

# This function sets configuration for specified order
def setConfig(order, id):
    commandOrder = "sudo virsh " + order + " " + id
    call(commandOrder.split(" "))
            
# This function opens virtual machine consoles
def openConsoles(id):
    os.system(f"xterm -e \'sudo virsh console " + id + "\'&")
           
#------ Main logic ---------   
if sys.argv[1] == "create":
    createOrder(sys.argv[2])
elif sys.argv[1] == "start":
    startOrder()
elif sys.argv[1] == "stop":
    stopOrder()
elif sys.argv[1] == "release":
    releaseOrder()
elif sys.argv[1] == "-help":
    print("")

    
