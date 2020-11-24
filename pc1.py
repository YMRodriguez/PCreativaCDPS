'''
Created on 16 nov. 2020

@author: yamil.mateo.rodriguez
'''
from subprocess import call
import sys
import logging
import configparser
import xml.dom.minidom as md
from lxml import etree


logging.basicConfig(level = logging.DEBUG)
logger = logging.getLogger('pc1')
    
def createOrder(nServers = 2, nClients = 1, nLB = 1):
    if nServers < 1 and nServers > 5:
        raise ValueError("You must create from 1 to 5 servers")
    setUpConfigFile(nServers, nClients, nLB)
    machineImagesId = handleMVIds(nServers, nClients, nLB)
    createMachineImages(machineImagesId)
    for i in machineImagesId:
        editXML(i)

# This function creates the list of IDs for the VMs  
def handleMVIds(nServers, nClients, nLB):
    ids = []
    for i in range(nServers):
        ids.append("s"+ i) 
    for i in range(nClients):
        ids.append("c" + i)
    for i in range(nLB):
        ids.append("lb" + i)
    return ids
      
# This function creates a pc1.cfg file and stores the needed variables into this file
def setUpConfigFile( nServers, nClients, nLB ):
    config = configparser.ConfigParser()
    config['VARIABLES'] = {'num_serv' : nServers,
                           'num_client' : nClients,
                           'num_lb': nLB}
    with open('pc1.cfg', 'w') as configfile:
        config.write(configfile)

# This function edits an XML for a vm given its id
def editXML(id):
    # Create the parser to handle XML
    parser = etree.XMLParser(remove_blank_text=True)
    file = etree.parse(id + ".xml", parser)
    # Edit name and source file location
    file.find('/name').text = id
    file.find('/devices/disk/source').set('file', id + '.qcow2')
    # Edit network interfaces
    if 's' in id:
        file.find('/devices/interface/source').set('bridge', "LAN2") 
    elif 'c' in id:
        file.find('/devices/interface/source').set('bridge', "LAN1")
    else:
        file.find('/devices/interface/source').set('bridge', "LAN1")
        newInterface = etree.Element('interface', type = 'bridge' )
        source = etree.Element('source', bridge = 'LAN2')
        model = etree.Element('model', type = 'virtio')
        newInterface.append(source)
        newInterface.append(model)
        file.find('/devices').append(newInterface)
    file.write(id + ".xml", pretty_print=True)
    
# This function creates all the images from a given list of the machines    
def createMachineImages(ids):
    for i in ids:
        commandImage = "sudo qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 "+ i +".qcow2"
        commandXML = "cp plantilla-vm-pc1.xml " + i + ".xml"
        call(commandImage.split(" "))
        call(commandXML.split(" "))
    

if sys.argv[1] == "create":
    createOrder(sys.argv[2])
if sys.argv[1] == "start":
    startOrder()
if sys.argv[1] == "stop":
    stopOrder()
if sys.argv[1] == "release":
    releaseOrder()
    
    
    
    
    
    