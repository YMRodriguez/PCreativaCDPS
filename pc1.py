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
import pyhaproxy


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
    
    for i in machineImageIds:
        editXML(i, LANS)
        createHostnameForMV(i)
        createInterfacesFileForMV(i)
    
    editIndexHtml(machineImageIds)
    setLbAsRouter(machineImageIds)
    
    createHAProxy(machineImageIds)
    #addHostToVirtualNetwork()
    call(["sudo", "virt-manager"])
    
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
    file.find('/devices/disk/source').set('file', os.getcwd() + "/" + id + '.qcow2')
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

def editIndexHtml(ids):
    for id in ids:
        if 's' in id:
            filepath = os.path.join('/mnt/tmp', 'index.html')
            if not os.path.exists('/mnt/tmp'):
                logger.debug("tmp directory does not exists")
            f = open(filepath, "w+")
            f.write(id  + "\n")
            f.close()
            confCommand = "sudo virt-copy-in -a " + id + ".qcow2 /mnt/tmp/index.html /var/www/html/"
            call(confCommand.split(" "))
    
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
    f.write(id  + "\n")
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
        'name': 'eth0',
        'auto': True,
        'gateway': '10.0.2.1',
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.2.1' + str(numberDirIP)
        }
        interfaces.addAdapter(options)
    if 'c' in id: #Aqui hay que ver como esquivar al host
        options = {
            'addrFam': 'inet',
        'name': 'eth0',
        'auto': True,
        'gateway': '10.0.1.1',
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.1.' + str(numberDirIP+3) #se añaden desde el 4 para evitar colision
        }
        interfaces.addAdapter(options)
    if 'lb' in id: #Hay que ver como hacerlo generico
        options = {
            'addrFam': 'inet',
        'broadcast': '10.0.1.255',
        'name': 'eth0',
        'auto': True,
        'gateway': '10.0.1.1',
        'source': 'static',
        'netmask': '255.255.255.0',
        'address': '10.0.1.1'
        }
        options2 = {
            'addrFam': 'inet',
        'broadcast': '10.0.2.255',
        'name': 'eth1',
        'auto': True,
        'gateway': '10.0.2.1',
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
def setLbAsRouter(ids):
    for id in ids:
        if 'lb' in id:
            f = open("/mnt/tmp/sysctl.conf", "w+")
            f.write("net.ipv4.ip_forward=1\n")
            f.close()
            command = "sudo virt-copy-in -a " + id + ".qcow2 /mnt/tmp/sysctl.conf /etc/"
            call(command.split(" "))
            
# This function includes the host in LAN1      
def addHostToVirtualNetwork():
    commandIfConfig = "sudo ifconfig LAN1 10.0.1.3/24"
    commandIpRoute = "sudo ip route add 10.0.0.0/16 via 10.0.1.1"
    call(commandIfConfig.split(" "))
    call(commandIpRoute.split(" "))

#-----------------HAproxy------------------------------
def createHAProxy(ids):
    # For the host the statictics page is in http://10.0.1.1:8001
    for i in ids:
        if 'lb' in i:
            commandStract = "sudo virt-copy-out -a " + i + ".qcow2 /etc/haproxy/haproxy.cfg " + os.getcwd()
            call(commandStract.split(" "))
            commandPerm = "cp " + os.getcwd() + "/haproxy.cfg " + os.getcwd() + "/phaproxy.cfg"
            call(commandPerm.split(" "))
            commandDelete = "rm -r " + os.getcwd() + "/haproxy.cfg"
            call(commandDelete.split(" "))
            commandPerm2 = "cp " + os.getcwd() + "/phaproxy.cfg " + os.getcwd() + "/haproxy.cfg"
            call(commandPerm2.split(" "))
            commandDelete = "rm -r " + os.getcwd() + "/phaproxy.cfg"
            call(commandDelete.split(" "))
            file = open("haproxy.cfg", "a")
            file.write("frontend " + i + "\n")
            file.write("\tbind *:80\n")
            file.write("\tmode http\n")
            file.write("\tdefault_backend webservers\n")
            file.write("\n")
            file.write("backend webservers\n")
            file.write("\tmode http\n")
            file.write("\tbalance roundrobin\n")
            file.close()
    for i in ids:
        if 's' in i:
            numberDirIP = [int(c) for c in list(i) if c.isdigit()][0]
            file = open("haproxy.cfg", "a")
            file.write("\tserver " + i + " 10.0.2.1" + str(numberDirIP) + ":80 check\n")
            file.close()
    file = open("haproxy.cfg", "a")
    file.write("listen stats\n")
    file.write("\tbind *:8001\n")
    file.write("\tstats enable\n")
    file.write("\tstats uri /\n")
    file.write("\tstats hide-version\n")
    file.write("\tstats auth admin:cdps\n")
    file.close()
    commandTransf= "sudo virt-copy-in -a " + [i for i in ids if 'lb' in i][0] + ".qcow2 " + os.getcwd() + "/haproxy.cfg /etc/haproxy/"
    call(commandTransf.split(" ")) 
#---------------- End CREATE logic & functions ---------------------
#-------------------------------------------------------
    
#---------------- Begin START logic --------------------
#Start virtual machines and show their consoles
def startOrder(): 
    nMVs = findNumberMachines()
    machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    try:
        if len(sys.argv[2])>1:
            setUpOne("start")
            return
        else:
            print("The parameter introduced does not match any of the virtual machine identifiers. Use the order '-help' for more information.")
            return 
    except:  
        for i in machineImageIds:
            setConfig("start", i)
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
    try:
        if len(sys.argv[2])>1:
            setUpOne("shutdown")
            return
        else:
            print("The parameter introduced does not match any of the virtual machine identifiers. Use the order '-help' for more information.")
            return 
    except:  
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
        undefineVMs(i)
    deleteFiles(machineImageIds)    
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
    
#This function deletes virtual machines 
def undefineVMs(id):
    commandOrder = "sudo virsh undefine " + id
    call(commandOrder.split(" "))
    
#This function deletes the practice's scenario associated files 
def deleteFiles(ids):
    configFiles = ["pc1" , "haproxy"]
    for i in configFiles:
        commandDelete1 = "rm -r " + os.getcwd() + "/" + i + ".cfg"
        call(commandDelete1.split(" "))
    for i in ids:
        commandDelete2 = "rm -r " + os.getcwd() + "/" + i + ".qcow2"
        call(commandDelete2.split(" "))
        commandDelete3 = "rm -r " + os.getcwd() + "/" + i + ".xml"
        call(commandDelete3.split(" "))

#This function sets configuration of a single virtual machine for a specific order
def setUpOne(order): 
    flag = 0
    nMVs = findNumberMachines()
    ids = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    for i in ids:
        if  i == sys.argv[2]:
            setConfig(order,i)
            if order == "start":
                openConsoles(i)
            flag = 1
    if flag == 0:
        print("The parameter introduced does not match any of the virtual machine identifiers. Use the order '-help' for more information.")
    else:
        flag = 0    
 
    
#--------------------- Start MONITORIZE logic ----------------------
def monitorizeOrder(option="all"):
    try:
        if option == "all":
            print("List of domains and their state")
            com1= "sudo virsh list" 
            call(com1.split(" "))
            printNewSection()
            print("Server connection test")
            nMVs = findNumberMachines()
            machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
            for id in machineImageIds:
                if 's' in id:
                    com2= "ping -c 5 10.0.1.1" + str([int(c) for c in list(id) if c.isdigit()][0])
                    call(com2.split(" "))
            printNewSection()
    
        elif option == "connection":
            print("Server connection test")
            nMVs = findNumberMachines()
            machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
            for id in machineImageIds:
                if 's' in id:
                    com2= "ping -c 5 10.0.1.1" + str([int(c) for c in list(id) if c.isdigit()][0])
                    call(com2.split(" "))
            printNewSection()
            
        elif option == "state":
            setMonitoring("domstate")
            
        elif option == "info":
            setMonitoring("dominfo")
            
        elif option == "cpu":
            setMonitoring("cpu-stats")
        
        else:
            print("The parameter introduced does not match any of the established patterns. Use the order '-help' for more information.")
    except:
        #print("The parameter introduced does not match any of the established patterns.")
        return
        
#--------------------- Helpers
def printNewSection():
    print("----------------------------------")
    print("|                                |")
    print("----------------------------------")
    
#This function sets the specific configuration for monitoring the virtual machines
def setMonitoring(order):
    nMVs = findNumberMachines()
    machineImageIds = handleMVIds(nMVs[0], nMVs[1], nMVs[2])
    command = "watch "
    for i in machineImageIds:
        command = command + f"sudo virsh {order} {i} & "
    command = command [::-1]
    command = command.replace("&", "", 1)
    command = command [::-1] 
    call(command.split(" ")) 

#------ Main logic ---------   
if sys.argv[1] == "create":
    try:
        createOrder(sys.argv[2])
    except:
        createOrder()
        print("There will be two servers by default ")
elif sys.argv[1] == "start":
    startOrder()
elif sys.argv[1] == "stop":
    stopOrder()
elif sys.argv[1] == "release":
    releaseOrder()
elif sys.argv[1] == "monitor":
    try:
        monitorizeOrder(sys.argv[2])
    except:
        monitorizeOrder()
        print("No parameter introduced. Default (all) monitoring option presented. Use the order '-help' for more information.")
elif sys.argv[1] == "-help":
    print(" ")
    print("------------ SCRIPT SUPPORT ------------")
    print(" ")
    print("This is a Python script that implements the automatic creation of a load balancer virtual scenario.")
    print(" ")
    print("The script understands the following orders:")
    print(" ")
    print("CREATE")
    print("This order creates the .qcow2 and the XML files of each VM, along with all the configuration files required for the scenario's correct functioning.")
    print("The 'create' order implements an scenario with two servers, one load balancer and one client by default (if no extra parameters are used). However, the number of servers of the scenario can be programmed by the user just by adding an extra parameter.The 'create' order implements the creation and configuration of a HAproxy load balancer.")
    print("The structure of the 'create' order command would be:")
    print(" ")
    print("python3 pc1.py create <NumberOfServers>")
    print(" ")
    print("START")
    print("This order is used to initialize the scenario's VMs and to display their textual consoles.")
    print("The 'start' order allows to initialize either all the VMs of the scenario or just a single VM indicated by the user (extra parameter).")
    print("The structure of the 'start' order command would be:")
    print(" ")
    print("python3 pc1.py start <VirtualMachineDomain>.")
    print(" ")
    print("If no extra parameter is specified, the 'start' order will just initialize all the scenario's VMs.")
    print(" ")
    print("STOP")
    print("This order is used to shut down the scenario's VMs.")
    print("The 'stop' order allows to shut down either all the VMs of the scenario or just a single VM indicated by the user (extra parameter).")
    print("The structure of the 'stop' order command would be:")
    print(" ")
    print("python3 pc1.py stop <VirtualMachineDomain>.")
    print(" ")
    print("If no extra parameter is specified, the 'stop' order will just shut down all the scenario's VMs.")
    print(" ")
    print("RELEASE")
    print("This order deletes all created files and VMs in order to release the practice's scenario.")
    print("The structure of the 'release' order command would be:")
    print(" ")
    print("python3 pc1.py release")
    print(" ")
    print("---COMPLEMENTARY ORDERS---")
    print(" ")
    print("MONITOR")
    print("This order implements a monitoring feature to visualize and control the usage of the scenario's VMs.")
    print("The 'monitor' order allows to perform server connection tests and to visualize the information and state of each VM, among other functionalities.")
    print("The structure of the 'monitor' order command would be:")
    print(" ")
    print("python3 pc1.py monitor <MonitoringOption>")
    print(" ")
    print("The order supports the following monitoring options:")
    print("    - 'all'. Displays a list of the VM domains and their state and run server connection tests.")
    print("    - 'connection'. Run server connection tests.")
    print("    - 'state'. Opens a panel (through the 'watch' command) which periodically displays the updated state of the machines.")
    print("    - 'info'. Opens a panel (through the 'watch' command) which periodically displays updated information regarding the VMs (identifier, memory usage, tasks carried out...).")
    print("    - 'cpu'. Opens a panel (through the 'watch' command) which periodically displays the updated CPU-time information of the machines.")
    print(" ")
    print("HELP")
    print("This order displays a manual with the main documentation regarding the functioning of the script.")
    print("The structure of the 'help' order command would be:")
    print(" ")
    print("python3 pc1.py -help")
    print(" ")
    print("------------END------------")
    print(" ")
    
else:
    print("Incorrect order, introduce one of the established orders. Use the order '-help' for more information.")
    
    
    