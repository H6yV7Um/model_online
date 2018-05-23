#!/usr/bin/env python

import sys
import os
ROOTPATH='./'
#sys.path.append(ROOTPATH+'/gen-py')
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/gen-py')
from ServiceInterface import ServiceInterface
from ServiceInterface.ttypes import *
from ServiceInterface.constants import *
from ServiceClassifyInterface import *
from ServiceClassifyInterface.ttypes import *
from ServiceClassifyInterface.constants import *
from ServiceCommonInterface import *
from ServiceCommonInterface.ttypes import *
from ServiceCommonInterface.constants import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

class ServiceClient:
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
            if (isframed):
                self.transport = TTransport.TFramedTransport(socket)
                self.isframed = True
            else:
                self.transport = TTransport.TBufferedTransport(socket)
                self.isframed = False
          
            # Wrap in a protocol
            protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
          
            # Create a client to use the protocol encoder
            self.client = ServiceInterface.Client(protocol)
          
            # Connect!
            self.transport.open()

            self.isinit = True
            return True,''
        except Thrift.TException, tx:
	    err_msg=tx.message
            return False,err_msg

    #def get(self, type, key, value, valuetype):
    def get(self, input):
        result = {}
        result['status'] = -1
        if (self.isinit):
            #print 'get'
            param = ServiceClassifyGetParam()
            param.type = input['type']
            param.key = input['key']
            param.value = input['value']
            param.valueType = input['valuetype']
			#print 'param: ', param
            tmpvalue = self.client.classifyGet(param)
			#print 'value: ', tmpvalue
            result['status'] = tmpvalue.status
            result['value'] = self._getResult(tmpvalue)
        return result
    
    def stat(self, key, value):
        result = {}
        result['status'] = -1
        if (self.isinit):
            print 'stat'
            param = ServiceStatParam()
            param.cmd = key
            #param.valueDict[key] = value
            print 'param: ', param
            tmpvalue = self.client.stat(param)
            #print 'value: ', tmpvalue
            result['status'] = tmpvalue.status
            result['value'] = self._getResult(tmpvalue)
        return result
        
    def control(self, key, value):
        result = {}
        result['status'] = -1
        if (self.isinit):
            param = ServiceControlParam()
            param.cmd = key
            param.valueDict = {}
            param.valueDict[key] = value
            tmpvalue = self.client.control(param)
            #print 'value: ', tmpvalue
            result['status'] = tmpvalue.status
            result['value'] = self._getResult(tmpvalue)
        return result
     
    def controllog(self, key, value):
        result = {}
        result['status'] = -1
        if (self.isinit):
            print 'controllog'
            param = ServiceControlParam()
            param.cmd = 'ControlServerLog'
            param.valueDict = {}
            param.valueDict[key] = value
            #print 'param: ', param
            tmpvalue = self.client.control(param)
            print 'value: ', tmpvalue
            result['status'] = tmpvalue.status
            result['value'] = self._getResult(tmpvalue)
        return result
     
    def _getResult(self, tmpvalue):
        if tmpvalue.valueType == 2:
            return tmpvalue.valueDict
        elif tmpvalue.valueType == 0:
            return tmpvalue.valueMatrix
        else: # json
            return tmpvalue.value
