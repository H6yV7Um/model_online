#!/usr/bin/env python
#coding=utf-8
import urllib,urllib2,json
import io,os,sys,stat,shutil,time,ConfigParser
from lib import mylogging,util
import sys   
import json
from deploy import deploy
from ClientBasic import *
class Client:
	version = ''
	logger = ''
	data_path=''
	online_path=''
	backup_path=''
	model_name=''
	model_path=''
	model_port=''
	feature_path=''
	service_conf_path=''
	release_lib_path=''
	zklist = []
	monitor = ''
	def __init__(self, type):
		self.path = os.path.dirname(os.path.abspath(__file__))
		self.logger = mylogging.getLogger('deploy_client.log')
		self.version=time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))
		self.online_path=os.path.join(self.path,'./online')
		self.backup_path=os.path.join(self.path,'./backup')
		self.data_path=os.path.join(self.path,'./data')
		self.service_conf_path=os.path.join(self.path,'./config')
		self.release_lib_path=os.path.join(self.path,'./release')
		#to make sure data dir exsists ,and empty
                if(type !='test'):
		    if os.access(self.data_path, os.F_OK):
                        util.del_file(self.data_path,self.logger)
		    else:
			util.mkdir(self.data_path,self.logger)
		
		    if os.access(self.service_conf_path, os.F_OK):
			util.del_file(self.service_conf_path,self.logger)
		    else:
			util.mkdir(self.service_conf_path,self.logger)
		
		    if os.access(self.release_lib_path, os.F_OK):
			util.del_file(self.release_lib_path,self.logger)
		    else:
			util.mkdir(self.release_lib_path,self.logger)
		util.mkdir(self.backup_path,self.logger)
		util.mkdir(self.online_path,self.logger)
		#read config file
		config = ConfigParser.ConfigParser()
		config.read('env.conf')
		self.monitor=config.get('config', 'monitor');
		self.model_name=config.get('config', 'model_name')
		self.service_name=config.get('config', 'service_name')
		self.model_path=config.get('config', 'model_path')
		self.feature_path=config.get('config', 'feature_path')
		self.model_port=config.get('config', 'model_port')
		zk_regist=config.get('config', 'zk_regist')
		zknodes=config.get('config', 'zklist').split(',')
		for item in zknodes:
			cluster_id=config.get(item, 'cluster_id')
			group_id=config.get(item, 'group_id')
			service_id=config.get(item, 'service_id')
			type_id=config.get(item, 'type')
			zkinfo={}
			zkinfo['service_name'] = item
			zkinfo['cluster_id'] = cluster_id
			zkinfo['group_id'] = group_id
			zkinfo['service_id'] = service_id
			zkinfo['type_id'] = type_id
			self.zklist.append(zkinfo)
		if(zk_regist=='1'):
			self.registe_zk_service
			self.logger.info("regist zk %s",zkinfo)
	def backup(self):
		#if self.online_path dir is not empty
		if os.path.exists(self.online_path):
			if os.listdir(self.online_path):
				shutil.copytree(self.online_path,os.path.join(self.backup_path,'./bak-'+self.version));
			util.del_file(self.online_path,self.logger)
	def get_model_from_hdfs(self,model_path,feature_path,model_name):
		dst_path=os.path.join(self.data_path,model_name)
		util.mkdir(dst_path,self.logger)
		rc = util.hdfs_file_copy(feature_path,dst_path,False,"hadoop",self.logger)
		if(rc is False):
			self.logger.error("Fail to get %s from hdfs",feature_path)
			return False
		rc = util.hdfs_file_copy(model_path,dst_path,False,"hadoop",self.logger)	
		if(rc is False):
			self.logger.error("Fail to get %s from hdfs",model_path)
			return False
		return True
	def registe_zk_service(self):
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			http_request="curl http://i2.api.weibo.com/2/darwin/application/service_discovery/registe_service.json -d 'source=646811797&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id+"&mail=yuxiang8'"
			rc, stdout, stderr = util.run_shell(http_request,self.logger)
	def modify_config(self,model_name):
		#model config
		src_model_conf = os.path.join(self.path,'./lr_templates/models.conf')
		dst_model_conf = os.path.join(self.data_path,'./models.conf')
		rc = util.copy_file(src_model_conf,dst_model_conf,self.logger)
		if(rc is False):
			return False
		rc = util.text_replace(dst_model_conf,'model_demo',model_name,self.logger)		
		if(rc is False):
			return False
		#service config
		src_service_conf = os.path.join(self.path,'./lr_templates/service.conf')
		dst_service_conf = os.path.join(self.service_conf_path,'service.conf')
		rc = util.copy_file(src_service_conf,dst_service_conf,self.logger)
		if(rc is False):
			return False
		rc = util.text_replace(dst_service_conf,'model_demo',model_name,self.logger)		
		if(rc is False):
			return False	
		rc = util.text_replace(dst_service_conf,'demo_version',self.version,self.logger)		
		if(rc is False):
			return False
		rc = util.text_replace(dst_service_conf,'svc_name',self.service_name,self.logger)		
		if(rc is False):
			return False
		fp = dst_service_conf
		conf = ConfigParser.SafeConfigParser()
		conf.read(fp)
		#conf.set('common','port',self.model_port)
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			conf.set('monitor','zk_addr',cluster_id)
			conf.set('monitor','zk_group_id',group_id)
			conf.set('monitor','zk_service_id',service_id)
			conf.set('monitor','zk_type_id',type_id)
			with open(fp, 'w') as fw:
				conf.write(fw)
			fw.close()
		return True
	def get_release_so(self):
		src_release_lib=os.path.join(self.path,'./lr_templates/model_demo.so')
		dst_release_lib = os.path.join(self.release_lib_path,self.model_name+'.so')
		rc = util.copy_file(src_release_lib,dst_release_lib,self.logger)
		if(rc is False):
			return False
		os.chmod(dst_release_lib,stat.S_IRWXG|stat.S_IRWXU|stat.S_IRWXO)
            #service.conf modify demo_version 
        def packet_test(self):
                print("client begin packet.")
		online_path=os.path.join(self.online_path,self.service_name,self.version);
		tar_path=os.path.join(online_path,self.version)
                src_service_conf_path = os.path.join(self.service_conf_path,'service.conf')
                print("sevice conf path: %s" % src_service_conf_path)
                #all file,models.conf put in config data release,only service.conf modify demo_version 
		rc = util.text_replace(src_service_conf_path,'demo_version',self.version,self.logger)		
		if(rc is False):
                    print("text replace service conf version failed")
		    return False
		#shutil.move(self.service_conf_path,os.path.join(tar_path,"./config"))
		#shutil.move(self.data_path,os.path.join(tar_path,"./data"))
		#shutil.move(self.release_lib_path,os.path.join(tar_path,"./lib"))
                rc,stderr = util.copy_dir(self.service_conf_path,os.path.join(tar_path,"./config"),self.logger)
                if(rc is False):
                    print(stderr)
                    return False
                rc,stderr = util.copy_dir(self.data_path,os.path.join(tar_path,"./data"),self.logger)
                if(rc is False):
                    print(stderr)
                    return False
                rc,stderr = util.copy_dir(self.release_lib_path,os.path.join(tar_path,"./lib"),self.logger)
                if(rc is False):
                    print(stderr)
                    return False

		tar_file = util.tar(tar_path,self.logger)
		util.del_dir(tar_path,self.logger)
		res=util.gen_file_md5(online_path,tar_file,self.version,self.logger)
		#upload to monitor
		cmd = "rsync -r %s %s" %(os.path.join(self.online_path,self.service_name),self.monitor)
                print("packet upload cmd: %s" % cmd)
		#rc,stdout,stderr= util.run_shell(cmd,self.logger)
		#if(rc is False):
		#	return False
		self.logger.info("success upload model %s to monitor %s,model version %s",self.model_name,self.monitor,self.version)		
                print("client finish packet.")
		return self.version 

	def packet(self):
		#get model
                print("client begin packet.")
		rc = self.get_model_from_hdfs(self.model_path,self.feature_path,self.model_name)
		if(rc is False):
			return False
		#modify config
		rc = self.modify_config(self.model_name)
		if(rc is False):
			return False
		#get release so lib
		self.get_release_so()
		online_path=os.path.join(self.online_path,self.service_name,self.version);
		tar_path=os.path.join(online_path,self.version)
		shutil.move(self.service_conf_path,os.path.join(tar_path,"./config"))
		shutil.move(self.data_path,os.path.join(tar_path,"./data"))
		shutil.move(self.release_lib_path,os.path.join(tar_path,"./lib"))
		tar_file = util.tar(tar_path,self.logger)
		util.del_dir(tar_path,self.logger)
		#res = util.get_file_md5(tar_file)
		res=util.gen_file_md5(online_path,tar_file,self.version,self.logger)
		#upload to monitor
		cmd = "rsync -r %s %s" %(os.path.join(self.online_path,self.service_name),self.monitor)
                print("packet upload cmd: %s" % cmd)
		rc,stdout,stderr= util.run_shell(cmd,self.logger)
		if(rc is False):
			return False
		self.logger.info("success upload model %s to monitor %s,model version %s",self.model_name,self.monitor,self.version)		
                print("client finish packet.")
		return self.version 
	def notify(self,host,port,version):
                print("notify service update model")
		param = {}
		notifyclient = ClientBasic()
		notifyclient.init(host,port)
		input = {}
		dic={}
		dic['model_name']=self.model_name
		dic['service_name']=self.service_name
		self.version = version 
		dic['model_version']=self.version
		dic['model_path']=os.path.join(self.monitor,self.service_name,self.version)
                print("upload monitor model path:%s" % dic['model_path'])
		dic['acquire_method']='rsync'	
		input_val=json.dumps(dic)
		input['value']=input_val
		#input['value'] = "{'modeh l_name':'fast_lr','model_version':'201801010101','model_path':'10.77.136.198::datamining_service/fast_lr/','acquire_method':'rsync'}"
		result = notifyclient.update(input)
		print 'result: ', result
	def notify_all(self,version):
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			http_url="http://i2.api.weibo.com/darwin/application/service_discovery/get_service.json?source=2110367561&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id
			print http_url
			http_req=urllib2.Request(http_url)
			response=urllib2.urlopen(http_req)
			page=response.read()
			text=json.loads(page)
			result=text['results']
			for it in result:
				host_info=it['msg'].split(' ')[0].split(':')
				ip=host_info[0]
				port=host_info[1]
				print ip,port
				self.notify(ip,port,version)	
	
        #def deploy_model_service(self, version,docker_image_tag,service_name,port):
        def deploy_model_service(self, version):
            docker_image_tag = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.1"
            service_name = "fast_fs_lr"
            port = 17080 
            status, output = deploy.deploy_service(service_name, port, docker_image_tag, version)
            return (status, output)
if __name__=="__main__":
        if(len(sys.argv) < 2):
            print("usage: 'python LRClient.py deploy [docker_tag] [service_name] [port] '\n       'python LRClient.py update [ip1,ip2]'")
            sys.exit(0) 
	obj = Client('test')
	obj.backup();
        if(sys.argv[1] == "deploy"):
            #if(len(sys.argv) < 5):
            #    print("usage: 'python LRClient.py deploy [docker_tag] [service_name] [port] '\n       'python LRClient.py update [ip1,ip2]'")
            #    sys.exit(0) 
            #service.conf modify demo_version 
            version = obj.packet_test();
            print(version)
            status, output = obj.deploy_model_service(version)
            print("status:%d" % status)
            print(output)
        if(sys.argv[1] == "update"):
            if(len(sys.argv) < 3):
                print("usage: 'python LRClient.py deploy [docker_tag] [service_name] [port] '\n       'python LRClient.py update [ip1,ip2]'")
                sys.exit(0) 
            #service.conf modify demo_version 
            version = obj.packet_test();
            print(version)
            iplist = sys.argv[2].split(',')
            for ip in iplist:
                print(ip)
                obj.notify(ip,9999,version)
            #obj.registe_zk_service();
            #obj.notify_all(version)
        if(sys.argv[1] != "update" and sys.argv[1] != "deploy"):
            print("usage: 'python LRClient.py deploy [docker_tag] [service_name] [port] '\n       'python LRClient.py update [ip1,ip2]'")
            
