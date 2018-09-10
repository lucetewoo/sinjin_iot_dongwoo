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
import pprint
from uuid import getnode as get_mac

import myCustomCodec

try:
	import ibmiotf.application
	import ibmiotf.device
except ImportError:
	# This part is only required to run the sample from within the samples
	# directory when the module itself is not installed.
	#
	# If you have the module installed, just use "import ibmiotf.application" & "import ibmiotf.device"
	import os
	import inspect
	cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"../../src")))
	if cmd_subfolder not in sys.path:
		sys.path.insert(0, cmd_subfolder)
	import ibmiotf.application
	import ibmiotf.device

	
def myAppEventCallback(event):
	print("Received live data from %s (%s) sent at %s: hello=%s x=%s" % (event.deviceId, event.deviceType, event.timestamp.strftime("%H:%M:%S"), data['hello'], data['x']))


try:
	opts, args = getopt.getopt(sys.argv[1:], "a:d:", ["app=", "device="])
except getopt.GetoptError as err:
	print(str(err))
	sys.exit(2)

appConfigFilePath = None
deviceConfigFilePath = None
appOptions = {}
deviceOptions = {}

# Seconds to sleep between readings
interval = 1

for o, a in opts:
	if o in ("-a", "--app"):
		appConfigFilePath = a
		appOptions = ibmiotf.application.ParseConfigFile(appConfigFilePath)
	elif o in ("-d", "--device"):
		deviceConfigFilePath = a
		deviceOptions = ibmiotf.device.ParseConfigFile(deviceConfigFilePath)
	else:
		assert False, "unhandled option" + o
		
# Initialize the application client.
try:
	appCli = ibmiotf.application.Client(appOptions)
except Exception as e:
	print(str(e))
	sys.exit()

# Connect and configuration the application
# - subscribe to live data from the device we created, specifically to "greeting" events
# - use the myAppEventCallback method to process events
appCli.setMessageEncoderModule("custom", myCustomCodec)
appCli.connect()
appCli.subscribeToDeviceEvents(deviceOptions['type'], deviceOptions['id'], "greeting")
appCli.deviceEventCallback = myAppEventCallback

	
# Initialize the device client.
try:
	deviceCli = ibmiotf.device.Client(deviceOptions)
	deviceCli.setMessageEncoderModule("custom", myCustomCodec)
except Exception as e:
	print(str(e))
	sys.exit()

# Connect and send a datapoint "hello" with value "world" into the cloud as an event of type "greeting" 10 times
deviceCli.connect()
for x in range (0,10):
	data = { 'hello' : 'world', 'x' : x}
	deviceCli.publishEvent("greeting", "custom", data)
	time.sleep(1)
		

# Disconnect the device and application from the cloud
deviceCli.disconnect()
appCli.disconnect()
