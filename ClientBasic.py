#!/usr/bin/env python

import sys
import os
ROOTPATH='./'
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/gen-py')
from ServiceMonitorInterface import ServiceMonitorInterface
from ServiceMonitorInterface.ttypes import *
from ServiceMonitorInterface.constants import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
import requests  
class ClientBasic:
	def __init__(self):
		self.isinit = False
		self.isframed = True
	def __del__(self):
		if (self.isinit):
			# Close!
			self.transport.close()
			self.isinit = False
	def init(self, host, port, isframed = True):
		self.isinit = False
		try:
			# Make socket
	
			socket = TSocket.TSocket(host, port)		  
			# Buffering is critical. Raw sockets are very slow
			self.transport = TTransport.TBufferedTransport(socket)
			# Wrap in a protocol
			protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
			# Create a client to use the protocol encoder
			self.client = ServiceMonitorInterface.Client(protocol)
			# Connect!
			self.transport.open()
			self.isinit = True
		except Thrift.TException, tx:
			print '%s' % (tx.message)
	def update(self, input):
		result = {}
		result['status'] = -1
		if (self.isinit):
			#print 'get'
			param = ServiceMonitorParam()
			param.value = input['value']
			print 'param.value'
			print param.value
			result = self.client.updateModel(param)
		return result
