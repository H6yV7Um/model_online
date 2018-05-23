import sys   
sys.path.append('./gen-py/ServiceMonitorInterface')  
  
from ServiceMonitorInterface import *  
from thrift import Thrift   
from thrift.transport import TSocket  
from thrift.transport import TTransport  
from thrift.protocol import TBinaryProtocol  
import requests  
  
try:  
    transport = TSocket.TSocket('localhost', 9999)  
    transport = TTransport.TBufferedTransport(transport)  
    protocol = TBinaryProtocol.TBinaryProtocol(transport)  
    client = Client(protocol)  
    transport.open()  
  
    print 'start'  
    res = requests.get('http://www.baidu.com')  
    xml = client.parseHtml2Xml(res.content)  
    print xml   
    transport.close()  
except Thrift.TException as e:  
    print 'exceptino'  
    print e  
