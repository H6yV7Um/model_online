#!/usr/bin/env python
#coding=utf-8
import urllib,urllib2,json
import io,os,sys,stat,shutil,time,ConfigParser
from lib import mylogging,util
import sys   
import commands
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
        docker_images = {}
        docker_image_tag =''
        model_owner=''
        algorithm=''
	def __init__(self, action, model_name, service_name, algorithm):
                print_log("model name: " + model_name + ",service name: " + service_name) 
		self.path = os.path.dirname(os.path.abspath(__file__))
                self.restore_env_conf()
                self.algorithm = algorithm
		self.logger = mylogging.getLogger('deploy_client.log')
                cmd = "rm -rf " + os.path.join(self.path, "models/*") 
	        rc, stdout, stderr = util.run_shell(cmd,self.logger)
		self.version=time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))
		self.online_path=os.path.join(self.path,'./online')
		self.backup_path=os.path.join(self.path,'./backup')
		self.data_path=os.path.join(self.path,'./data')
		self.service_conf_path=os.path.join(self.path,'./config')
		self.release_lib_path=os.path.join(self.path,'./release')
                self.docker_images['LR'] = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.1"
                self.docker_images['DNN'] = "registry.intra.weibo.com/weibo_rd_algorithmplatform/dnn_prod:v1.0"
                self.modify_zk_info(model_name, service_name)
		#to make sure data dir exsists ,and empty
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
		self.docker_image_tag=self.docker_images[algorithm.upper()]
                print_log("docker tag: %s" % self.docker_image_tag) 
		self.model_name=model_name
		self.service_name=service_name
                self.get_model_feature_path(action) 
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
		if zk_regist=="1" and action =="deploy":
			self.registe_zk_service()
			self.logger.info("regist zk %s",zkinfo)

        def get_model_feature_path(self, action):
            cmdlist = ["deploy","update","downline"]
            if action in cmdlist:
                if 'LR' == self.algorithm.upper(): 
                    self.get_model_feature_path_lr() 
                if 'DNN' == self.algorithm.upper(): 
                    self.get_model_feature_path_dnn() 

        def get_model_feature_path_dnn(self):
            url = "http://controlcenter.ds.sina.com.cn/waic/models?name="+self.model_name
            size=len('hdfs://emr-cluster')
            req = urllib2.Request(url)
            try:
                res_data = urllib2.urlopen(req)
            except urllib2.URLError as e:
                print_log("get model path exception: %s" % e.reason) 
                return '',''
            res = res_data.read()
            text=json.loads(res)
            result=text['result']
            model_path=''            
            user = ''
            for model in result:
                if model['name'] == self.model_name:
                    print_log("find model in model lib.\n") 
                    self.model_owner = model['owner']
                    if model['location'].startswith('hdfs'):
                        self.model_path = model['location'][size:]
                    else:
                        self.model_path = model['location']
                    self.model_id = model['id']
                    if model['location'].startswith('hdfs'):
                        self.feature_path = model['featureInfo'][size:]
                    else:
                        self.feature_path = model['featureInfo']
                    print_log("dnn modelpath:%s featurepath:%s" % (self.model_path,self.feature_path))
                    return 
            print_log("did not find model:%s\n" % self.model_name) 
            
        def get_model_feature_path_lr(self):
            self.model_owner, sample_id,self.model_path=self.get_model_path(self.model_name)
            print_log("model path: " + self.model_path + ",model owner: " + self.model_owner) 
            self.feature_path=self.get_feature_path(self.model_owner, sample_id)
            print_log("feature path: " + self.feature_path) 

        def check_zk_exist_path(self):
	    for item in self.zklist:
	        group_id=item['group_id']
		type_id=item['type_id']
		cluster_id=item['cluster_id']
		service_id=item['service_id']
		http_url="http://i2.api.weibo.com/darwin/application/service_discovery/get_service.json?source=2110367561&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id
                print_log("get zk req url: %s\n" % http_url) 
		http_req=urllib2.Request(http_url)
		response=urllib2.urlopen(http_req)
		page=response.read()
		text=json.loads(page)
                print_log("check zk exists,response: %s\n" % text) 
                if text['total_count'] > 0:
                    return True 
                return False

        def modify_zk_info(self, model_name, service_name):
            cur_path = os.path.dirname(os.path.abspath(__file__))
            conf_path = os.path.join(cur_path, "./env.conf")
            rc = util.text_replace(conf_path,'svc_demo',service_name,self.logger)
            if rc is False:
                return False
            rc = util.text_replace(conf_path,'model_demo',model_name,self.logger)
            if rc is False:
                return False

        def get_model_path(self, model_name):
            url = "http://controlcenter.ds.sina.com.cn/waic/models?name="+model_name
            size=len('hdfs://emr-cluster')
            req = urllib2.Request(url)
            try:
                res_data = urllib2.urlopen(req)
            except urllib2.URLError as e:
                print_log("get model path exception: %s" % e.reason) 
                return '',''
            res = res_data.read()
            text=json.loads(res)
            result=text['result']
            sample_id=''
            model_path=''            
            user = ''
            for model in result:
                if model['name'] == model_name:
                    print_log("find model in model lib.\n") 
                    user = model['owner']
                    if model['location'].startswith('hdfs'):
                        model_path = model['location'][size:]
                    else:
                        model_path = model['location']
                    sample_id = model['sampleId']
                    self.model_id = model['id']
                    return user, sample_id, model_path
            print_log("did not find model:%s\n" % model_name) 
            return user,sample_id, model_path

        def get_feature_path(self, user, sample_id):
            print_log("sample id:%s" % sample_id) 
            url = "http://controlcenter.ds.sina.com.cn/waic/samples/detail/id/"
            url = url + sample_id 
            url = url + "?user="
            url = url + user
            size=len('hdfs://emr-cluster')
            req = urllib2.Request(url)
            try:
                res_data = urllib2.urlopen(req)
            except urllib2.URLError as e:
                print_log("get feature path exception: %s" % e.reason) 
                return ''
            res = res_data.read()
            text=json.loads(res)
            feature_path =''
            result=text['result']
            if len(result) == 0:
                print_log("did not find sample:%s" % sample_id) 
                return feature_path 
            print_log("find sample in sample lib.\n") 
            feature_path = result[0]['featureConf']
            if feature_path.startswith('hdfs'):
                feature_path = feature_path[size:]
            print_log("feature conf path:%s\n" % feature_path) 
            return feature_path

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
		if rc is False:
			self.logger.error("Fail to get %s from hdfs",feature_path)
			return False
                local_models_path = os.path.join(self.path, "models")
		if not os.path.isdir(local_models_path):
		    util.mkdir(local_models_path,self.logger)
		rc = util.hdfs_file_copy(model_path,os.path.join(local_models_path, model_name), False,"hadoop",self.logger)	
		if rc is False:
			self.logger.error("Fail to get %s from hdfs",model_path)
			return False
                predict_model_path = self.assemble_model_file(os.path.join(local_models_path,model_name))
                print_log("assemble predict model path:%s\n" % predict_model_path) 
		rc = util.copy_file(predict_model_path,os.path.join(dst_path,"predict.model"),self.logger)
		if rc is False:
                        print_log("copy predict model to data dir error:%s\n") 
			return False
		return True

        def remove_tmp_model_files(self):
            tmp_model_path = os.path.join(self.path, "models", self.model_name)
            util.del_dir(tmp_model_path,self.logger)
             
	def registe_zk_service(self):
                print_log("register zk url: \n") 
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			http_request="curl http://i2.api.weibo.com/2/darwin/application/service_discovery/registe_service.json -d 'source=646811797&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id+"&mail=yuxiang8'"
                        print_log(http_request) 
			rc, stdout, stderr = util.run_shell(http_request,self.logger)

	def modify_config(self,model_name):
		#model config
                if 'LR' == self.algorithm.upper():
		    src_models_conf = os.path.join(self.path,'./lr_templates/models.conf')
                elif 'DNN' == self.algorithm.upper():
		    src_models_conf = os.path.join(self.path,'./dnn_templates/models.conf')
		dst_models_conf = os.path.join(self.data_path,'./models.conf')
		rc = util.copy_file(src_models_conf,dst_models_conf,self.logger)
		if rc is False:
			return False
		rc = util.text_replace(dst_models_conf,'model_demo',model_name,self.logger)		
		if rc is False:
			return False
		#service config
                if 'LR' == self.algorithm.upper():
		    src_service_conf = os.path.join(self.path,'./lr_templates/service.conf')
                elif 'DNN' == self.algorithm.upper():
		    src_service_conf = os.path.join(self.path,'./dnn_templates/service.conf')
		dst_service_conf = os.path.join(self.service_conf_path,'service.conf')
		rc = util.copy_file(src_service_conf,dst_service_conf,self.logger)
		if rc is False:
			return False
		rc = util.text_replace(dst_service_conf,'model_demo',model_name,self.logger)		
		if rc is False:
			return False	
		rc = util.text_replace(dst_service_conf,'demo_version',self.version,self.logger)		
		if rc is False:
			return False
		rc = util.text_replace(dst_service_conf,'svc_name',self.service_name,self.logger)		
		if rc is False:
			return False
                if 'DNN' == self.algorithm.upper():
                    src_model_conf = os.path.join(self.path,'./dnn_templates/model.conf')
                    dst_model_conf = os.path.join(self.data_path,self.model_name,'./model.conf')
                    rc = util.copy_file(src_model_conf,dst_model_conf,self.logger)
                    if rc is False:
                        print_log("copy dnn model conf error")
                        return False
		    rc = util.text_replace(dst_model_conf,'model_demo',model_name,self.logger)		
		    if rc is False:
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
                if 'LR' == self.algorithm.upper():
		    src_release_lib=os.path.join(self.path,'./lr_templates/model_demo.so')
                elif 'DNN' == self.algorithm.upper():
		    src_release_lib=os.path.join(self.path,'./dnn_templates/model_demo.so')
		dst_release_lib = os.path.join(self.release_lib_path,self.model_name+'.so')
		rc = util.copy_file(src_release_lib,dst_release_lib,self.logger)
		if rc is False:
			return False
		os.chmod(dst_release_lib,stat.S_IRWXG|stat.S_IRWXU|stat.S_IRWXO)

        def packet_dnn(self):
                dst_path=os.path.join(self.data_path, self.model_name, "version")
                f_path = os.path.join(self.data_path, self.model_name)
                util.mkdir(dst_path,self.logger)
                print_log("client begin packeting model\n") 
                #get model
                rc = util.hdfs_file_copy(self.model_path,dst_path,False,"hadoop",self.logger)
                if rc is False:
                        print_log("Fail to get %s from hdfs" % self.model_path)
                        return False
                rc = util.hdfs_file_copy(self.feature_path,f_path,False,"hadoop",self.logger)
                if rc is False:
                        print_log("Fail to get %s from hdfs" % self.feature_path)
                        return False
		#modify config
		rc = self.modify_config(self.model_name)
		if rc is False:
		    return False,'modify config error'
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
                print_log("packet upload cmd: %s\n" % cmd) 
		rc,stdout,stderr= util.run_shell(cmd,self.logger)
		if rc is False:
			return False,'upload model error'
		self.logger.info("success upload model %s to monitor %s,model version %s",self.model_name,self.monitor,self.version)		
                print_log("client finish packet: %s\n" % tar_file) 
		return True, self.version 
        def packet(self, algo):
            if algo.upper() == 'DNN':
                res, version = obj.packet_dnn()
            elif algo.upper() == 'LR':
                res, version = obj.packet_lr()
            return res, version
	def packet_lr(self):
		#get model
                print_log("client packeting model data.\n") 
                if self.model_path == '' or self.feature_path == '':
		    return False,'model path or feature path null'
		rc = self.get_model_from_hdfs(self.model_path,self.feature_path,self.model_name)
		if rc is False:
		    return False,'get model from hdfs error'
		#modify config
		rc = self.modify_config(self.model_name)
		if rc is False:
		    return False,'modify config error'
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
                print_log("packet upload cmd: %s\n" % cmd) 
		rc,stdout,stderr= util.run_shell(cmd,self.logger)
		if rc is False:
			return False,'upload model error'
		self.logger.info("success upload model %s to monitor %s,model version %s",self.model_name,self.monitor,self.version)		
                print_log("client finish packet: %s\n" % tar_file) 
		return True, self.version 

        def assemble_model_file(self,filedir):
            predict_model = os.path.join(os.getcwd(),"predict.model")
            print_log("start assembling predict model: %s" % predict_model)
            if os.access(predict_model, os.F_OK):
                os.remove(predict_model)
                print_log("del previous assembled predict_model")
            filenames=os.listdir(filedir)
            #sort for assemble as part-0 part-1 part-2 order
            filenames.sort()
            f=open('predict.model','w')
            for filename in filenames:
                filepath = filedir+'/'+filename
                for line in open(filepath):
                    f.writelines(line)
                    if line[-1] != '\n':
                        f.writelines("\n")
            f.close()
            print_log("finish assembling predict model: %s" % predict_model)
            return predict_model 

	def notify(self,host,port,version):
                print_log("notify service %s update model\n" % host) 
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
                print_log("upload monitor model path:%s\n" % dic['model_path']) 
		dic['acquire_method']='rsync'	
		input_val=json.dumps(dic)
		input['value']=input_val
		#input['value'] = "{'modeh l_name':'fast_lr','model_version':'201801010101','model_path':'10.77.136.198::datamining_service/fast_lr/','acquire_method':'rsync'}"
		result = notifyclient.update(input)
		print 'result: ', result
        
        def get_zk_info(self):
            for item in self.zklist:
                print_log("zk info:\n") 
                print(item) 

        def get_zk_response(self):
	    for item in self.zklist:
	        group_id=item['group_id']
		type_id=item['type_id']
		cluster_id=item['cluster_id']
		service_id=item['service_id']
		http_url="http://i2.api.weibo.com/darwin/application/service_discovery/get_service.json?source=2110367561&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id
                print_log("get zk req url: %s\n" % http_url) 
		http_req=urllib2.Request(http_url)
		response=urllib2.urlopen(http_req)
		page=response.read()
		text=json.loads(page)
                print_log("zk response: %s\n" % text) 
                return text['results'] 
             
        def restore_env_conf(self):
            src_path = os.path.join(self.path,"./bakenv.conf")
            dst_path = os.path.join(self.path,"./env.conf")
            rc = util.copy_file(src_path,dst_path,self.logger)
            if rc is False:
                print_log("restore env conf error") 
                return False
        def remove_service_discovery_info(self):        
            url = "http://controlcenter.ds.sina.com.cn/waic/models/update?user=" + self.model_owner+ "&id="+self.model_id+"&"
            values={}
            values={"zkinfo":"null"}
            data = urllib.urlencode(values)
            ss = data.replace("%27","%22")
            print_log(ss)
            print("\n")
            urll = url +ss
            print_log("remove svc discovery info url: %s" % urll)
            print("\n")
            req = urllib2.Request(urll)
            req.get_method = lambda:'PUT'
            res_data = urllib2.urlopen(req)
            res = res_data.read()
            print_log("remove svc discovery result: %s" % res) 
        def registe_service_discovery_info(self):
            url = "http://controlcenter.ds.sina.com.cn/waic/models/update?user=" + self.model_owner+ "&id="+self.model_id+"&"
            values={}
            zk={}
            zk['cluster_id']="zk://10.39.11.60:2181,10.39.11.61:2181,10.39.11.62:2181,10.39.11.63:2181,10.39.11.64:2181"
            zk['group_id']=self.service_name
            zk['service_id']=self.model_name
	    for item in self.zklist:
		type_id=item['type_id']
            zk['type']=type_id
            values['zkinfo']=zk
            #values1={"zkinfo":"null"}
            data = urllib.urlencode(values)
            ss = data.replace("%27","%22")
            print_log(ss)
            print("\n")
            urll = url +ss
            print_log("registe svc discovery info url: %s" % urll)
            print("\n")
            req = urllib2.Request(urll)
            req.get_method = lambda:'PUT'
            res_data = urllib2.urlopen(req)
            res = res_data.read()
            print_log("registe svc discovery result: %s" % res) 

	def notify_all(self, version):
		for item in self.zklist:
			group_id=item['group_id']
			type_id=item['type_id']
			cluster_id=item['cluster_id']
			service_id=item['service_id']
			http_url="http://i2.api.weibo.com/darwin/application/service_discovery/get_service.json?source=2110367561&cluster_id="+cluster_id+"&group_id="+group_id+"&service_id="+service_id+"&type="+type_id
                        print_log("get zk req url:\n %s\n" % http_url) 
			http_req=urllib2.Request(http_url)
			response=urllib2.urlopen(http_req)
			page=response.read()
			text=json.loads(page)
                        print_log("notify all,zk response: %s\n" % text) 
			result=text['results']
			for it in result:
				host_info=it['msg'].split(' ')[0].split(':')
				ip=host_info[0]
				port=host_info[1]
                                print_log("update %s %s:%s model\n" % (self.service_name, ip, port)) 
				self.notify(ip,9999,version)	
	
        #def deploy_model_service(self, version,docker_image_tag,service_name,port):
        def deploy_model_service(self, version):
            #docker_image_tag = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.1"
            docker_image_tag = self.docker_image_tag 
            service_name = self.service_name 
            port = self.model_port 
            status, output = deploy.deploy_service(service_name, port, docker_image_tag, version)
            return (status, output)


        def downline_service(self):
            service_name = self.service_name
            deploy.delete_deployment(service_name)

        def validate_model(self):
            print_log("begin validating model")
            cur_path = os.path.join(os.getcwd(),"rpcclient")
            results = self.get_zk_response()
	    for it in results:
	        host_info=it['msg'].split(' ')[0].split(':')
		ip=host_info[0]
		port=host_info[1]
                print_log("validate %s %s:%s model\n" % (self.service_name, ip, port)) 
                cmd = cur_path + " " + ip + " " + port + " json ./input.json 20 1 1" 
                status,output = commands.getstatusoutput(cmd)
                print_log("output:\n%s" % output)

        def check_model_predict_result(self, ipport_list):
            print_log("begin checking model predict result")
            cur_path = os.path.join(os.getcwd(),"rpcclient")
            output_path = os.path.join(os.getcwd(),"output.json") 
            result_flag = True
            with open(output_path,'r') as load_f:
                dict1 = json.load(load_f)
            text={}
            flag = 1
            while flag == 1:
	        for ipport in ipport_list:
	            host_info=ipport.split(':')
		    ip=host_info[0]
		    port=host_info[1]
                    print_log("checking model:%s on %s:%s predict result\n" % (self.model_name, ip, port)) 
                    cmd = cur_path + " " + ip + " " + port + " json ./input.json 20 1 1" 
                    status,output = commands.getstatusoutput(cmd)
                    index = output.find("value:")
                    if index == -1:
                        flag = 1
                        break
                    else:
                        flag = 0
                    re_json = output[index+6:] 
                    print_log("output: %s\n" % re_json)
                    output_json = "".join([re_json.strip().rsplit("}", 1)[0], "}"])
                    text = json.loads(output_json)
                    for src_list, dst_list in zip(sorted(dict1), sorted(text)):
                        if str(dict1[src_list]) != str(text[dst_list]):
                            result_flag = False
                            print_log("cheking result Exception!!!not match key values:\n")
                            print(src_list,dict1[src_list],dst_list,text[dst_list])
                time.sleep(3)
            if result_flag is True:
                print_log("checking model predict result success,all key values match\n")
            print_log("finish checking model predict result")

def print_log(message):
    print(time.strftime('%Y-%m-%d %H:%M:%S, ',time.localtime(time.time())) + message) 

def usage():
    print '===help==='
    print "usage: 'python", sys.argv[0], "[deploy/updateModel/list/validate/downline] [model_name] [service_name] [algorithm]'\n"
    print "       'python", sys.argv[0], "[list]'\n"

def get_svc_list():
    result = deploy.get_pods()
    return result

if __name__=="__main__":
        cmd_list = ["deploy","update","list","downline","validate"]
        if len(sys.argv) < 2:
            usage()
            sys.exit(0) 
        if sys.argv[1] not in cmd_list:
            usage()
            sys.exit(0) 
        if sys.argv[1] == "list":
            get_svc_list()
            sys.exit(0) 
        if len(sys.argv) < 5:
            usage()
            sys.exit(0) 
	obj = Client(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])
        if sys.argv[1] == "deploy":
            ret = obj.check_zk_exist_path()
            if ret is True:
                print_log("zk exist this service model path, please change service name or model name \n") 
                obj.restore_env_conf()
                sys.exit(0) 
	    obj.backup();
            res, version = obj.packet(sys.argv[4])
            if res is True: 
                print_log("new model packet version: %s\n" % version) 
                status, output = obj.deploy_model_service(version)
                print_log("deploy action status:%d" % status) 
                if status == 0:
                    print_log("model service deploy on nodes: %s" % output) 
                    #obj.get_zk_info() 
                    #count = obj.get_zk_response() 
                    obj.check_model_predict_result(output)        
                    obj.registe_service_discovery_info()
                else:
                    print_log("model service deploy fail: %s" % output) 
            else:
                print_log("stop packeting,reason: %s" % version) 
            obj.restore_env_conf()
        if sys.argv[1] == "update":
	    obj.backup();
            res, version = obj.packet(sys.argv[4])
            if res is True: 
                print_log("new model packet version: %s\n" % version) 
                obj.notify_all(version)
                #iplist = sys.argv[5].split(',')
                #for ip in iplist:
                #    obj.notify(ip,9999,version)
            else:
                print_log("stop packeting,reason: %s" % version) 
            obj.restore_env_conf()
        if sys.argv[1] == "downline":
            obj.downline_service()
            obj.remove_service_discovery_info()
            obj.restore_env_conf()
        if sys.argv[1] == "validate":
            obj.validate_model()
            obj.restore_env_conf()
