#!/bin/env python
#-*- encoding=utf8 -*-
import urllib,urllib2,json
import os,sys,shutil,time,ConfigParser,subprocess
import subprocess
from subprocess import Popen, PIPE
#from lib import mylogging
from socket import *
from deploy import deploy
class RsyncUpdate:
	monitor = ''
	modulename = ''
	version = ''
	zklist = []
	logger = ''
	data_path=''
	def __init__(self):
		self.path = os.path.dirname(os.path.abspath(__file__))
		#self.logger = mylogging.getLogger('log.update')
		config = ConfigParser.ConfigParser()
		config.read('env.conf')
		self.monitor=config.get('config', 'monitor');
		self.modulename=config.get('config', 'modulename');
		zknodes=config.get('config', 'zklist').split(',');
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
                self.data_path=os.path.join(self.path,'./data')
                self.mkdir(self.data_path)
                print self.data_path
		#print self.zklist
		self.version=time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))
	def backup(self):
		backup_path=os.path.join(self.path,'./backup')
		online_path=os.path.join(self.path,'./online')
		self.mkdir(os.path.join(backup_path,'./data'))
		self.mkdir(os.path.join(backup_path,'./lib'))
		self.mkdir(os.path.join(online_path,'./data'))
		self.mkdir(os.path.join(online_path + '/lib'))
		print 'version'+self.version
		shutil.move(os.path.join(online_path,'./data'),os.path.join(backup_path,'./data','./bak-'+self.version));
		shutil.move(os.path.join(online_path,'./lib'),os.path.join(backup_path,'./lib','./bak-'+self.version));
	def packet(self):
		data_path=os.path.join(self.path,'./data')
		lib_path=os.path.join(self.path,'./release')
		shutil.copytree(data_path,os.path.join(self.path,'./online/data/'));
		shutil.copytree(lib_path,os.path.join(self.path,'./online/lib/'));
	def update(self):
		fo = open(os.path.join(self.path,'./online/success'), "w")
		fo.write(self.version)
		fo.close()
		cmd = "rsync %s/* %s::datamining_plugin/%s/lib/" %(os.path.join(self.path,'./online/lib'),self.monitor,self.modulename)
		subprocess.call(cmd, shell=True)
		cmd = "rsync -r %s/* %s::datamining_plugin/%s/data/" %(os.path.join(self.path,'./online/data'),self.monitor,self.modulename)
		subprocess.call(cmd, shell=True)
		cmd = "rsync  %s %s::datamining_plugin/%s/" %(os.path.join(self.path,'./online/success'),self.monitor,self.modulename)
		subprocess.call(cmd, shell=True)
		#print cmd
	def notify(self):
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			http_url="http://i2.api.weibo.com/darwin/application/service_discovery/get_service.json?source=2110367561&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id
			http_req=urllib2.Request(http_url)
			response=urllib2.urlopen(http_req)
			page=response.read()
			text=json.loads(page)
			result=text['results']
			for it in result:
				host_info=it['msg'].split(' ')[0].split(':')
				ip=host_info[0]
				port=host_info[1]
				print ip
				print port
	def run_shell(self,cmd):
		self.logger.info("begin to run cmd:%s", str(cmd))
		rc = 1
		stdout = stderr = ""
		try:
			p = Popen(cmd, shell = True, stdout = PIPE, stderr = PIPE)
			stdout, stderr = p.communicate()
			rc = p.returncode
			self.logger.info("run cmd success, rc:%s, stdout:%s, stderr:%s", rc, stdout, stderr)
			return rc, stdout, stderr
		except Exception, msg:
			self.logger.error("run cmd faild, rc:%s, stdout:%s, stderr:%s", rc, stdout, stderr)
		return 1, "", ""
	def hdfs_file_copy(self,hdfs_file, local_file, force = False, hadoop_bin = "/usr/bin/hadoop"):
		self.logger.info("copy hdfs_file:%s to local:%s.", hdfs_file, local_file)
		cmd = "%s fs -get %s %s" % (hadoop_bin, hdfs_file, local_file)
		if force:
			cmd = cmd + " -f"
		rc, stdout, stderr = self.run_shell(cmd)
		return rc == 0 
	def get_model_from_hdfs(self,model_path,feature_conf,model_name):
		dst_path=os.path.join(self.data_path,model_name)
                self.mkdir(dst_path)
		obj.hdfs_file_copy(feature_conf,dst_path,False,"hadoop")
		obj.hdfs_file_copy(model_path,dst_path,False,"hadoop")
	def mkdir(self,path):
		path=path.strip()
		path=path.rstrip("\\")
		isExists=os.path.exists(path)
    		# get result
    		if not isExists:
			os.makedirs(path)  
			return True
		else:
			return False

        def deploy_model_service(self):
            service_name = "fast_lr" 
            port = 17080
            docker_image_tag = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.0" 
            status, output = deploy.deploy_service(service_name, port, docker_image_tag)
            if status == 0:
                #status为0，部署动作成功
                print("Deploy success!")
            else:
                #status非0，部署动作失败，打印失败原因
                print(output)

if __name__=="__main__":
	obj = RsyncUpdate()
	#obj.get_model_from_hdfs('/user/feed_weibo/haibo/ml_fata/model/predict.model','/user/feed_weibo/haibo/ml_fata/feature.conf','fast_lr')
        #obj.deploy_model_service()
	#obj.notify()
	obj.backup();
	obj.packet();
	obj.update();
	#obj.mkdir("/data0/user/zhili1/dockerbuilder/online/auto_deploy/text_deploy/test_rsync/backup")
