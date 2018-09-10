# *****************************************************************************
# Copyright (c) 2014 IBM Corporation and other Contributors.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html 
#
# Contributors:
#   David Parker - Initial Contribution
# *****************************************************************************

import getopt
import time
import sys
import psutil
import platform
import json
import signal
import subprocess
from uuid import getnode as get_mac


try:
	import ibmiotf.device
except ImportError:
	# This part is only required to run the sample from within the samples
	# directory when the module itself is not installed.
	#
	# If you have the module installed, just use "import ibmiotf"
	import os
	import inspect
	cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"../../src")))
	if cmd_subfolder not in sys.path:
		sys.path.insert(0, cmd_subfolder)
	import ibmiotf.device



def interruptHandler(signal, frame):
	client.disconnect()
	sys.exit(0)

def usage():
	print(
		"IOT-PSUTIL: Publish basic system utilization statistics to IBM Watson IoT Platform." + "\n" +
		"\n" +
		"Datapoints sent:" + "\n" +
		"  name          The name of this device.  Defaults to hostname ('%s')" % platform.node() + "\n" +
		"  cpu           Current CPU utilization (%)" + "\n" +
		"  mem           Current memory utilization (%)" + "\n" +
		"  network_up    Current outbound network utilization across all network interfaces (KB/s)" + "\n" +
		"  network_down  Current inbound network utilization across all network interfaces (KB/s)" + "\n" + 
		"\n" + 
		"Options: " + "\n" +
		"  -h, --help       Display help information" + "\n" + 
		"  -n, --name       Override the default device name" + "\n" + 
		"  -v, --verbose    Be more verbose"
	)

def isDmidecodeAvailable():
	try:
		value = subprocess.check_output(['dmidecode', '-h'], stderr=subprocess.STDOUT).decode("utf-8").strip()
	except subprocess.CalledProcessError as e:
		print(str(e))
		return False
	except Exception as e:
		print(str(e))
		return False
	return True
	
def dmidecode(property):
	try:
		value = subprocess.check_output(['dmidecode','-s', property], stderr=subprocess.STDOUT).decode("utf-8").strip()
	except subprocess.CalledProcessError as e:
		return None
	except Exception:
		return None
	return value

def commandProcessor(cmd):
	global interval
	print("Command received: %s" % cmd.data)
	if cmd.command == "setInterval":
		if 'interval' not in cmd.data:
			print("Error - command is missing required information: 'interval'")
		else:
			interval = cmd.data['interval']
	elif cmd.command == "print":
		if 'message' not in cmd.data:
			print("Error - command is missing required information: 'message'")
		else:
			print(cmd.data['message'])
	
if __name__ == "__main__":
	signal.signal(signal.SIGINT, interruptHandler)

	try:
		opts, args = getopt.getopt(sys.argv[1:], "hn:vo:t:i:T:c:", ["help", "name=", "verbose", "type=", "id=", "token=", "config="])
	except getopt.GetoptError as err:
		print(str(err))
		usage()
		sys.exit(2)

	verbose = False
	organization = "quickstart"
	deviceType = "sample-iotpsutil"
	deviceId = str(hex(int(get_mac())))[2:]
	deviceName = platform.node()
	authMethod = None
	authToken = None
	configFilePath = None
	
	# Seconds to sleep between readings
	interval = 10
	
	for o, a in opts:
		if o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-n", "--name"):
			deviceName = a
		elif o in ("-o", "--organization"):
			organization = a
		elif o in ("-t", "--type"):
			deviceType = a
		elif o in ("-i", "--id"):
			deviceId = a
		elif o in ("-T", "--token"):
			authMethod = "token"
			authToken = a
		elif o in ("-c", "--cfg"):
			configFilePath = a
		elif o in ("-h", "--help"):
			usage()
			sys.exit()
		else:
			assert False, "unhandled option" + o


	client = None
	
	if not isDmidecodeAvailable():
		print("dmidecode could not be found on the system path.  Device information will be based on the Python platform module alone.")
		print(" * http://www.nongnu.org/dmidecode/")
		print(" * http://gnuwin32.sourceforge.net/packages/dmidecode.htm")
	
	myDeviceInfo = ibmiotf.device.DeviceInfo()
	myDeviceInfo.description = "%s (%s)" % (dmidecode("system-version"), deviceName) if isDmidecodeAvailable() else deviceName 
	myDeviceInfo.deviceClass = dmidecode("system-version") if isDmidecodeAvailable() else platform.machine()
	myDeviceInfo.manufacturer = dmidecode("system-manufacturer") if isDmidecodeAvailable() else platform.system()
	myDeviceInfo.fwVersion = dmidecode("bios-version") if isDmidecodeAvailable() else platform.version()
	myDeviceInfo.hwVersion = dmidecode("baseboard-product-name") if isDmidecodeAvailable() else None
	myDeviceInfo.model = dmidecode("system-product-name") if isDmidecodeAvailable() else None
	myDeviceInfo.serialNumber = dmidecode("system-serial-number") if isDmidecodeAvailable() else None

	try:
		if configFilePath is not None:
			options = ibmiotf.device.ParseConfigFile(configFilePath)
		else:
			options = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
		client = ibmiotf.device.ManagedClient(options, logHandlers=None, deviceInfo=myDeviceInfo)
		client.commandCallback = commandProcessor
		client.connect()
	except ibmiotf.ConfigurationException as e:
		print(str(e))
		sys.exit()
	except ibmiotf.UnsupportedAuthenticationMethod as e:
		print(str(e))
		sys.exit()
	except ibmiotf.ConnectionException as e:
		print(str(e))
		sys.exit()
	

	print("(Press Ctrl+C to disconnect)")
	
	# Take initial reading
	psutil.cpu_percent(percpu=False)
	ioBefore_ts = time.time()
	ioBefore = psutil.net_io_counters()

	# Initiate DM action to update the geo location of the device, but don't wait (async) for it to complete
	client.setLocation(longitude=100, latitude=78, accuracy=100)
	
	# Initiate DM action to set error codes to 1, wait for it to be completed (sync) and then clear all error codes
	client.setErrorCode(1).wait()
	client.clearErrorCodes()
	
	# Initiate DM action to add log, wait for it to be completed (sync) and then clear all error codes
	client.addLog(msg="test",data="testdata",sensitivity=0).wait()
	client.clearLog()

	while True:
		time.sleep(interval)
		ioAfter_ts = time.time()
		ioAfter = psutil.net_io_counters()
  		
		# Calculate the time taken between IO checksor do 
		ioDuration = ioAfter_ts - ioBefore_ts
  
		data = { 
			'cpu' : psutil.cpu_percent(percpu=False),
			'mem' : psutil.virtual_memory().percent,
			'network': {
				'up': round( (ioAfter.bytes_sent - ioBefore.bytes_sent) / (ioDuration*1024), 2 ), 
				'down':  round( (ioAfter.bytes_recv - ioBefore.bytes_recv) / (ioDuration*1024), 2 )
			}
		}
		if verbose:
			print("Datapoint = " + json.dumps(data))
  		
		client.publishEvent("psutil", "json", data)
  		
		# Update timestamp and data ready for next loop
		ioBefore_ts = ioAfter_ts
		ioBefore = ioAfter
 	
