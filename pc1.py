'''
Created on 16 nov. 2020

@author: yamil.mateo.rodriguez
'''
from subprocess import call
import sys
import logging
import configparser
from lxml import etree
import os
from _cffi_backend import string
import debinterface

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pc1')

    
def createOrder(nServers=2, nClients=1, nLB=1):
    nServers = int(nServers)
    nClients = int(nClients)
    nLB = int(nLB)

    if nServers < 1 and nServers > 5:
        logger.debug("Error in the amount of servers")
        raise ValueError("You must create from 1 to 5 servers")
    setUpConfigFile(nServers, nClients, nLB)
    machineImagesId = handleMVIds(nServers, nClients, nLB)
    createMachineImages(machineImagesId)
    LANS = ["LAN1", "LAN2"]
    for i in machineImagesId:
        editXML(i, LANS)
    setUpBridges(LANS)
    for i in machineImagesId:
        createHostnameForMV(i)
        createInterfacesFileForMV(i)
    setLbAsRouter(machineImagesId)

#----------Helpers----------------
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
    config = configparser.ConfigParser()
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


# ----------- Machines------------
# This function creates all the images from a given list of the machines    
def createMachineImages(ids):
    for i in ids:
        commandImage = "qemu-img create -f qcow2 -b cdps-vm-base-pc1.qcow2 " + i + ".qcow2"
        commandXML = "cp plantilla-vm-pc1.xml " + i + ".xml"
        call(commandImage.split(" "))
        call(commandXML.split(" "))
    logger.debug("MVs images created")


#-------------- Networks ---------
# This function creates the bridges from a given list of LAN
def setUpBridges(LANS):
    for i in LANS:
        addbrCommand = "sudo brctl addbr " + i
        ifconfigCommand = "sudo ifconfig " + i + " up"
        call(addbrCommand.split(" "))
        call(ifconfigCommand.split(" "))


def createHostnameForMV(id):
    filepath = os.path.join('/mnt/tmp', 'hostname')
    if not os.path.exists('/mnt/tmp'):
        logger.debug("tmp directory does not exists")
    f = open(filepath, "w+")
    f.write(id  + "/n")
    f.close()
    confCommand = "sudo virt-copy-in -a " + id + ".qcow2 /mnt/tmp/hostname /etc/"
    call(confCommand.split(" "))

    
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

def setLbAsRouter(ids):
    lbs = [i for i in ids if 'lb' in i]
    for lb in lbs:
        command = "sudo virt-edit -a " + lb + ".qcow2 /etc/sysctl.conf -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/'"
        call(command.split(" "))

if sys.argv[1] == "create":
    createOrder(sys.argv[2])
# if sys.argv[1] == "start":
#     startOrder()
# if sys.argv[1] == "stop":
#     stopOrder()
# if sys.argv[1] == "release":
#     releaseOrder()
    
