#!/bin/env python
#-*- encoding=utf8 -*-
import sys   
sys.path.append("./gen-py/ServiceMonitorInterface")
from ServiceMonitorInterface import *
from ttypes import *
from ServiceClient import *
from thrift.Thrift import TType, TMessageType, TException  
from thrift.Thrift import TProcessor  
from thrift.transport import TSocket  
from thrift.protocol import TBinaryProtocol, TProtocol  
from thrift.server import TServer  
from lib import mylogging,util
import json,os,ConfigParser
class MonitorService:  
 	logger = ''
	#download file path
	monitor_temp=''
	port=''
	service_config_path=''
	service_plugin_path=''
	def __init__(self):
		self.logger = mylogging.getLogger('service.monitor')
		config = ConfigParser.ConfigParser()
		config.read('service.conf')
		self.monitor_temp=config.get('common', 'monitor_temp')
		self.port=config.get('common', 'monitor_port')	
		self.service_config_path=config.get('common','service_config_path')
		self.service_plugin_path=config.get('common','service_plugin_path')
        def check_file(self,file_dir,version):
		md5=''
		md5_check=''
		tar_file=os.path.join(file_dir,version,version+'.tar.gz')
		md5_file=os.path.join(file_dir,version,version+'.md5')
		if not os.path.exists(tar_file):
			err_msg=tar_file+'not exsist,retry later'
			return False,err_msg
		if not os.path.exists(md5_file):
			err_msg=md5_file+'not exsist,retry later'
			return False,err_msg
		md5 = util.get_file_md5(tar_file)
		f = open(md5_file)
		md5_check = f.readlines()[0]
		f.close()
		if(md5=='' or md5_check=='' or md5 != md5_check):
			return False,'md5 check failed,retry later'	
		util.un_tar(tar_file)
		return True,''	 	
	def downloadModel(self,model_name,model_version,model_path,acquire_method):
		try:
			#clean download dir
			if os.access(self.monitor_temp, os.F_OK):
				util.del_file(self.monitor_temp,self.logger)
			rc = util.rsync_file(model_path,self.monitor_temp,self.logger)
			if(rc is False):
				err_msg='Fail to get file from monitor '+ model_path
				self.logger.error(err_msg)
				return False,err_msg
			#check md5
			rc,stderr= self.check_file(self.monitor_temp,model_version)
			if(rc is False):
				err_msg='check md5 failed ,retry later'
				self.logger.error(err_msg)
				return False,err_msg
			
			return True,''
		except Exception,e:
			err_msg='Exception in downloadModel '+ str(e)
			return False,err_msg
	def dispatchModel(self,model_name,model_version,model_port):
		
		#dispatch confi data and lib
		src_config_file=os.path.join(self.monitor_temp,model_version,'./config')
		src_data_file=os.path.join(self.monitor_temp,model_version,'./data')
		src_lib_file=os.path.join(self.monitor_temp,model_version,'./lib')
		dst_config_file=os.path.join(self.service_plugin_path,model_name,model_version,'./config')
		dst_data_file=os.path.join(self.service_plugin_path,model_name,model_version,'./data')
		dst_lib_file=os.path.join(self.service_plugin_path,model_name,model_version,'./lib')
		rc,stderr = util.copy_dir(src_config_file,dst_config_file,self.logger)
		if(rc is False):
			return False,stderr
		rc,stderr = util.copy_dir(src_data_file,dst_data_file,self.logger)
		if(rc is False):
			return False,stderr
		rc,stderr = util.copy_dir(src_lib_file,dst_lib_file,self.logger)
		if(rc is False):
			return False,stderr
		return True,''
	def reloadModel(self,model_name,model_version,model_port):
		#dispatch service.conf
		src_service_conf=os.path.join(self.service_plugin_path,model_name,model_version,'./config/service.conf')
		dst_service_conf=os.path.join(self.service_config_path,model_port+'.conf')
		if not os.path.isfile(src_service_conf):
			return False,src_service_conf+' not exsit,try another version'
		rc = util.text_replace(src_service_conf,'maxport',model_port,self.logger)
		if(rc is False):
			return False,'Fail to change model_port in service.conf'
		rc = util.copy_file(src_service_conf,dst_service_conf,self.logger)
		if(rc is False):
			return False,'Fail to dispatch service.conf'
		client = ServiceClient()
		rc,stderr=client.init('127.0.0.1',model_port)	
		if(rc is False):
			return False,stderr
		result = client.control('ControlReloadModule','ControlReloadModule')
		reload_status = result['status']
		result = client.control('ControlModuleVersion','ControlModuleVersion')
		version_status=result['status']
		cur_version=result['value']
		if(reload_status == 0):
			return True,'reload model success,current version is ' + cur_version
		else:
			return False,'reload model failed,current version is ' + cur_version
	def updateModel(self,param):
		json_ = param.value.replace("'", '"')
		input_json = json.loads(json_)
		model_name = input_json['model_name']
		model_version=input_json['model_version']
		model_path=input_json['model_path']
		acquire_method=input_json['acquire_method']
		rc,stderr = self.downloadModel(model_name,model_version,model_path,acquire_method)
		dic={}
		if(rc is False):
			dic['status']='Failed'
			dic['error_msg']= stderr
			return json.dumps(dic)
		rc,stderr = self.dispatchModel(model_name,model_version,'17080')
		if(rc is False):
			dic['status']='Failed'
			dic['error_msg']= stderr
			return json.dumps(dic)
		rc,stderr = self.reloadModel(model_name,model_version,'17080')
		if(rc is False):
			dic['status']='Failed'
			dic['error_msg']= stderr
			return json.dumps(dic)
		
		dic['status']='Success'
		return json.dumps(dic)
		
def run():  
	#创建服务端  
	handler = MonitorService()  
	processor = Processor(handler)   
	#监听端口  
	transport = TSocket.TServerSocket('localhost', 9999)  
	#选择传输层  
	tfactory = TTransport.TBufferedTransportFactory()  
	#选择传输协议  
	pfactory = TBinaryProtocol.TBinaryProtocolFactory()   
	#创建服务端  
	server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)  
	server.setNumThreads(5)  
	#handler.logger.info('start thrift serve in python')  
	server.serve()  
	#handle.logger.info('done!')   
if __name__ == '__main__':  
	run()
	#obj = MonitorService()
	#rc,stderr=obj.reloadModel('fast_lr','20180413143838','16270')  
