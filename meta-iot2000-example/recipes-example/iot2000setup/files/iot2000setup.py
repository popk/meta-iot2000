#!/usr/bin/python

from __future__ import absolute_import, print_function, unicode_literals

from snack import *
import time
from subprocess import call
from subprocess import Popen, PIPE
from subprocess import check_output
import subprocess
import os
import os.path
from shutil import copyfile

networkConfigurationChanged = False
wifiEnabled = True

deviceIsIot2020 = False
def displayStartScreen():
	global wifiEnabled
	global deviceIsIot2020
	
	screen = SnackScreen()

	# Use dmidecode to determine device type (IOT2040/IOT2000)
	task = subprocess.Popen("/usr/sbin/dmidecode -t 11 | awk 'NR==8' | cut -f 2 -d :", stdout=subprocess.PIPE, shell=True)
	device = task.stdout.read().lstrip().rstrip()
		
	# Check if WLAN hardware is available	
	wifiEnabled = os.path.isdir("/sys/class/net/wlan0")
	
	
	title = device + " Setup"
	menuItems = [	"Change Root Password", "Change Host Name",
					"Expand File System", "Configure Network Interfaces",
					"Set up OPKG Repository",
					"Remove Unused Packages"]
		
	if (device == "IOT2020"):
		deviceIsIot2020 = True
	
	# Enable serial mode setting if device is IOT2040
	if (not deviceIsIot2020):	
		menuItems.append("Set Serial Mode") 
	if wifiEnabled:
		menuItems.append("Configure WLAN")
			
	action, selection = ListboxChoiceWindow(
		screen, 
		title, "", 
		menuItems, 
		[('Quit', 'quit', 'ESC')])

	screen.finish()

	if (action == 'quit'):
		if (networkConfigurationChanged == True):
			print(chr(27) + "[2J") # Clear console
			print("Restarting network services...")
			subprocess.call("/etc/init.d/networking restart", shell=True)
			if (wifiEnabled):
				subprocess.call("/sbin/ifdown wlan0", shell=True)
				subprocess.call("/sbin/ifup wlan0", shell=True)
		
		exit()
	
	if selection == 0:
		changeRootPassword()
	elif selection == 1:
		changeHostName()
	elif selection == 2:
		expandFileSystem()
	elif selection == 3:
		configureNetworkInterfaces()
	elif selection == 4:
		configureOpkgRepository()
	elif selection == 5:
		removeUnusedPackages()
	elif selection == 6:
		if (not deviceIsIot2020):
			configureSerial()
		elif wifiEnabled:
			configureWLAN()
	elif selection == 7:
		configureWLAN()

def changeRootPassword():
	print(chr(27) + "[2J") # Clear console 
	
	subprocess.call(["passwd", "root"])
	displayStartScreen()

def removeUnusedPackages():
	### Edit here ###
	packageList = ["galileo-target", "nodejs"] 	# Contains all potential 
												# candidates for removal
	###
	
	packageScreen = SnackScreen()
	bb = ButtonBar(packageScreen, (("Ok", "ok"), ("Cancel", "cancel")))
	ct = CheckboxTree(height = 10, scroll = 1,width=40)

	# Iterate through list of removal candidates and check if they are 
	# actually installed.
	task = subprocess.Popen("/usr/bin/opkg list-installed", stdout=subprocess.PIPE, shell=True)
	installedPackages = task.stdout.read()
	
	numberOfRemovablePackages = 0
	for package in packageList:
		if package in installedPackages:
			ct.append(package)
			numberOfRemovablePackages += 1

	g = GridForm(packageScreen, "Select Packages to Remove", 1, 4)
	l = Label("Use 'Space' to select the packages you want to remove.")
	g.add(l, 0, 0, growy=1, growx=1, padding=(1,1,1,1))
	g.add(ct, 0, 1)
	g.add(bb, 0, 3, growx = 1)
	result = g.runOnce()
	
	removeList = ''
	if (bb.buttonPressed(result) == "ok" and numberOfRemovablePackages > 0):
		# Build list of selected packages
		selectedPackages = ct.getSelection()
		for package in selectedPackages:
			removeList = removeList + package + '* '
		
		ret = ButtonChoiceWindow(
			packageScreen,
			"Remove Packages",
			"Are you sure you want to remove the following packages: \n\n" + removeList,
			buttons=[("OK", "ok"), ("Cancel", "cancel", "ESC")],
			width=40)
		
		packageScreen.finish()
				
		if (ret == "ok"):	
			removeList = "/usr/bin/opkg --force-removal-of-dependent-packages remove " + removeList
			print(chr(27) + "[2J") # Clear console 
			print("Removing selected packages...")
			subprocess.call(removeList, shell=True)

	displayStartScreen()
	
def configureSerial():
	serialScreen = SnackScreen()
		
	portAction, portSelection = ListboxChoiceWindow(
		serialScreen, 
		"Configure Serial Mode", "Select the serial port you want to configure and press 'Enter'.", 
		["X30", "X31"], 
		[('Cancel', 'cancel', 'ESC')])

	if (portAction != "cancel"):
		modes = ["RS232", "RS485", "RS422"]
		
		modeAction, modeSelection = ListboxChoiceWindow(
			serialScreen, 
			"Configure Serial Mode", "Select a mode.", 
			modes, 
			[('Cancel', 'cancel', 'ESC')])
		
		if (modeAction != "cancel"):
			switchCommand = '/usr/bin/switchserialmode'
			
			if (portSelection == "X30"):
				switchDeviceArg = '/dev/ttyS2'
			else:
				switchDeviceArg = '/dev/ttyS3'
			
			switchModeArg = modes[modeSelection].lower()
			subprocess.Popen([switchCommand, switchDeviceArg, switchModeArg], stdout=open(os.devnull, 'wb'))
			
	displayStartScreen()

def changeHostName():
	hostScreen = SnackScreen()
	currentHostName = subprocess.check_output("hostname")
	
	ret = EntryWindow(
		hostScreen,
		"Change Host Name",
		"",
		[("Host Name:", currentHostName)],
		1,
		70, 50,
		[('OK'), ('Cancel', 'cancel', 'ESC')],
		None)
		
	if ret[0] == "ok":
		hostScreen.finish()
		subprocess.Popen(["hostname", ret[1][0].rstrip()], stdout=open(os.devnull, 'wb'))
		
	displayStartScreen()
	
def configureOpkgRepository():
	opkgScreen = SnackScreen()

	ret = EntryWindow(
		opkgScreen,
		"Configure OPKG Repository",
		"",
		[("Host Address:", "")],
		1,
		70, 50,
		['OK', ('Cancel', 'cancel', 'ESC')],
		None)
	
	fileTemplate = '''src/gz all http://[host]/ipk/all
src/gz i586-nlp-32 http://[host]/ipk/i586-nlp-32
src/gz i586-nlp-32-intel-common http://[host]/ipk/i586-nlp-32-intel-common
src/gz iot2000 http://[host]/ipk/iot2000
'''
	if ret[0] == "ok":
		opkgConfig = fileTemplate.replace("[host]", ret[1][0].rstrip())
		fileName = "/etc/opkg/iot2000.conf"
		
		opkgFile = open(fileName, 'w')
		opkgFile.write(opkgConfig)
		opkgFile.close()
		
				
	opkgScreen.finish()	
	displayStartScreen()


def configureWLAN():
	wlanScreen = SnackScreen()
	global networkConfigurationChanged
	
	ret = EntryWindow(
		wlanScreen,
		"Configure WLAN",
		"",
		[("Type:", "WPA-PSK"), ("SSID:", ""), ("Key:", "")],
		1,
		70, 50,
		['OK', ('Cancel', 'cancel', 'ESC')],
		None)
	
	fileTemplate = '''ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0
update_config=1

network={
	key_mgmt=[type]
	ssid="[ssid]"
	psk="[passwd]"
}'''

	if ret[0] == "ok":
		wpaConfig = fileTemplate.replace("[type]", ret[1][0].rstrip()).replace("[ssid]", ret[1][1].rstrip()).replace("[passwd]", ret[1][2].rstrip())
		
		fileName = "/etc/wpa_supplicant.conf"
		
		backupFileName = "/etc/wpa_supplicant.conf.bak"
		copyfile(fileName, backupFileName)
		
		wpaFile = open(fileName, 'w')
		wpaFile.write(wpaConfig)
		wpaFile.close()

		rv = ButtonChoiceWindow(
				wlanScreen,
				"Configure WLAN",
				"Your WLAN configuration has been changed. A backup of the old configuration can be found at: " + backupFileName,
				buttons=["OK"],
				width=40)
				
		networkConfigurationChanged = 1
	
	wlanScreen.finish()
	displayStartScreen()

def getNetworkInterfaceConfiguration(interface):

	lines = [line.rstrip('\n') for line in open('/etc/network/interfaces')]
	for lineNumber in range(0, len(lines)-1):
		searchString = "auto " + interface
	
		if (searchString in lines[lineNumber]):
			splitLine = lines[lineNumber].split()
			
			while (splitLine[0] != "iface"):
				lineNumber += 1
				splitLine = lines[lineNumber].split()
		
			mode = splitLine[3]
			
			if (mode == "dhcp"):
				return "dhcp"
			if (mode == "static"):
				while (splitLine[0] != "address"):
					lineNumber += 1
					splitLine = lines[lineNumber].split()
				return splitLine[1]
		lineNumber += 1
	return "dhcp"	

def configureNetworkInterfaces():
	global networkConfigurationChanged
	global wifiEnabled
	global deviceIsIot2020
	
	networkScreen = SnackScreen()
	getNetworkInterfaceConfiguration('eth0')
	if deviceIsIot2020:
		interfaces = ([('eth0', getNetworkInterfaceConfiguration('eth0'))])
	else:
		interfaces = ([('eth0', getNetworkInterfaceConfiguration('eth0')) , ('eth1', getNetworkInterfaceConfiguration('eth1'))])
		
	if wifiEnabled:
		interfaces.append(('wlan0', getNetworkInterfaceConfiguration('wlan0')))
		
	ret = EntryWindow(
		networkScreen,
		"Configure Network Interfaces",
		"Specify IP addresses for network interfaces, enter 'dhcp' to obtain address by DHCP.",
		interfaces,
		1,
		70, 50,
		['OK', ('Cancel', 'cancel', 'ESC')],
		None)
	
	interfacesConfig = """# /etc/network/interfaces -- configuration file for ifup(8), ifdown(8)
 
# The loopback interface
auto lo
iface lo inet loopback

# Wired interfaces
"""	
	dhcpTemplate = """auto [interfaceName]
iface [interfaceName] inet dhcp

"""
	staticTemplate = """auto [interfaceName]
iface [interfaceName] inet static
	address [ip]
	netmask 255.255.255.0
	
"""

	wirelessDhcpTemplate = """allow-hotplug wlan0
auto wlan0
iface wlan0 inet dhcp
	wpa-conf /etc/wpa_supplicant.conf

"""
	wirelessStaticTemplate = """allow-hotplug wlan0
auto wlan0
iface wlan0 inet static
	address [ip]
	netmask 255.255.255.0
	wpa-conf /etc/wpa_supplicant.conf

"""
	
	i = 0
	for interface in interfaces:
		if interface[0] == "wlan0":
			if ret[1][i] == "dhcp":
				interfacesConfig = interfacesConfig + wirelessDhcpTemplate.replace("[interfaceName]", interface[0])
			else:
				interfacesConfig = interfacesConfig + wirelessStaticTemplate.replace("[interfaceName]", interface[0]).replace("[ip]", ret[1][i])
		else:
			if ret[1][i] == "dhcp":
				interfacesConfig = interfacesConfig + dhcpTemplate.replace("[interfaceName]", interface[0])
			else:
				interfacesConfig = interfacesConfig + staticTemplate.replace("[interfaceName]", interface[0]).replace("[ip]", ret[1][i])
		i += 1
	
	if ret[0] == "ok":
		fileName = "/etc/network/interfaces"
		backupFileName = "/etc/network/interfaces.bak"
		copyfile(fileName, backupFileName)
		interfacesFile = open(fileName, 'w')
		interfacesFile.write(interfacesConfig)
		interfacesFile.close()
		
		networkConfigurationChanged = 1
		rv = ButtonChoiceWindow(
				networkScreen,
				"Configure Network Interfaces",
				"Your network interfaces have been reconfigured. A backup of the old configuration can be found at: " + backupFileName,
				buttons=["OK"],
				width=40)

				
	networkScreen.finish()
	displayStartScreen()
	

def expandFileSystem():
	subprocess.call("/etc/iot2000setup/expandfs.sh", stdout=open(os.devnull, 'wb')) 

	expandScreen = SnackScreen()
	lab = Label("File system will be expanded on next reboot.")
	gf = GridForm(expandScreen, "Expand File System", 1, 4)

	bt = Button("OK")
	gf.add(lab, 0,0)
	gf.add(bt, 0,2)
		
	r = gf.runOnce()
	expandScreen.finish()
	
	displayStartScreen()

displayStartScreen()	
