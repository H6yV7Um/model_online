#!/usr/bin/env python
#coding=utf-8

import sys
import os
import commands
import shutil
import mylogging 
import thread
import threading
import time
from ServiceClient import *

logger = mylogging.getLogger('k8sdeploy.log')
ipList = []
mutex = threading.Lock()
def config_kubectl():
    homepath = os.environ['HOME']
    configpath = os.path.join(homepath, ".kube")
    if not os.path.exists(configpath):
        print_log("configuring k8s deploy tool.")
        os.mkdir(configpath, 0755)
    deploy_dir = get_deploy_dir() 
    logger.info("deploy_dir is:%s",deploy_dir)
    src_file = os.path.join(deploy_dir, "config")
    dst_file = os.path.join(configpath, "config")
    shutil.copyfile(src_file, dst_file)
    if not os.path.exists("/usr/bin/kubectl"):
        shutil.copyfile(deploy_dir + "/kubectl", "/usr/bin/kubectl")
        cmd = "chmod +x /usr/bin/kubectl"
        status,output = commands.getstatusoutput(cmd)
def delete_deployment(service_name):
    svc_name = service_name.replace('_','-')
    cmd = "kubectl delete deployment %s" % (svc_name)
    status,output = commands.getstatusoutput(cmd)
def get_pods():
    cmd = "kubectl get pods -o wide"
    status,output = commands.getstatusoutput(cmd)
    print_log(output) 
    return output
def buf_write(content, dstfile):
    file_add=open(dstfile, "w" )  
    file_add.write(content)   
    file_add.close()

def deploy_service(service_name, port, docker_image_tag, version):
    global ipList
    ipList = []
    config_kubectl()
    generate_jinjia(service_name, port, docker_image_tag,version)
    logger.info("finish generate jinjia")
    print_log("finish generate jinjia template")
    status,output = generate_yaml(service_name)
    logger.info("finish generate yaml")
    print_log("finish generate k8s deployment yaml ")
    if status != 0:
        logger.error("generate yaml status:%d",status)
        logger.error("generate yaml output:%s",output)
        print_log("generate yaml status:%d",status)
        print_log("generate yaml output:%s",output)
        return (status,output)
    status,output = exec_kubectl(service_name)
    meta_name = generate_meta_name(service_name)
    if status == 0:
        #print_log("Deploy service success!\nPlease use 'kubectl get pods' check your service instance '%s' is running." % meta_name)
        print_log("Deploy service action success!\n")
        ip_addrs = get_deploy_node_ips(meta_name)
        ip_list = check_wait_running(ip_addrs,meta_name)
        output = resemble_service_ip_port_list(ip_list,port)
        #check_loop(ip_list, str(port))
        #check_wait(ip_list)
        #output = ipList
    else:
        print_log("Deploy action failed!\n" + output) 
    clean_yml_jinja(service_name)
    return (status, output)

def resemble_service_ip_port_list(ip_list,port):
    results = []
    port = str(port)
    for ip in ip_list:
        ip = ip + ":" + port 
        results.append(ip)
    return results
        
def check_wait_running(ip_list, meta_name):
    print_log("start checking pod running status") 
    start_time = time.time()
    while(True):
        state = check_deploy_state(meta_name)
        if('Running' == state):
            print_log("all pod running")
            return ip_list
        end_time = time.time()
        if(end_time - start_time > 300):
            print_log("check pod state time out")
            iplists = get_available_service_ip_list(meta_name)
            return iplists
        time.sleep(3) 
def get_available_service_ip_list(podname):
    ip_list = []
    cmd = "kubectl get pods -o wide|grep %s|grep -v grep|awk '{print $3,$6}'" % (podname)
    status,output = commands.getstatusoutput(cmd)
    strarr = output.split('\n')
    for s in strarr:
        items = s.split(" ") 
        if(items[0] == 'Running'):
            ip_list.append(items[1]) 
    return ip_list 
def check_wait(ip_list):
    count = len(ip_list) 
    size = len(ipList) 
    start = time.time()
    while(True):
        time.sleep(1)  
        size = len(ipList)
        print_log(ipList)
        end = time.time()
        check_time = end - start
        if(size == count or check_time > 130):
            break 

def check_deploy_state(podname):
    cmd = "kubectl get pods|grep %s|grep -v grep|awk '{print $3}'" % (podname)
    status,output = commands.getstatusoutput(cmd)
    strarr = output.split('\n')
    for s in strarr:
        if s != "Running":
            return s
    return "Running"

def generate_yaml(service_name):
    deploy_dir = get_deploy_dir() 
    yml_name = deploy_dir + "/" + service_name + "_deployment.yaml"
    if os.path.exists(yml_name):
        os.remove(yml_name)
    cmd = "python " + deploy_dir + "/render_template.py " + deploy_dir + "/template.jinja > " + yml_name
    status,output = commands.getstatusoutput(cmd)
    return (status,output)

#k8s yaml metaname不能有下划线大写字母
def generate_meta_name(service_name):
    #转小写
    meta_name = service_name.lower()
    #替换下滑线为-
    meta_name = meta_name.replace('_', '-')
    meta_name = meta_name.replace('.', '-')
    return meta_name
    
def generate_jinjia(service_name, port, docker_image_tag,version):
    clean_yml_jinja(service_name)
    meta_name = generate_meta_name(service_name)
    deploy_dir = get_deploy_dir()
    jinja_demo_path = deploy_dir + "/template.jinja.demo" 
    file_object = open(jinja_demo_path)
    try:
      yml = file_object.read()
    finally:
      file_object.close()
    port = str(port)
    yml_ = yml.replace('$service_name', service_name)
    yml_ = yml_.replace('$port', port)
    yml_ = yml_.replace('$docker_image_tag', docker_image_tag)
    yml_ = yml_.replace('$meta_name', meta_name)
    yml_ = yml_.replace('$model_version', version)
    buf_write(yml_,deploy_dir +"/template.jinja")

def clean_yml_jinja(service_name):
    jinja_name = "template.jinja"
    deploy_dir = get_deploy_dir() 
    file_path = os.path.join(deploy_dir, jinja_name)
    if os.path.exists(file_path):
        os.remove(file_path)

def exec_kubectl(service_name):
    deploy_dir = get_deploy_dir()
    yml_name = deploy_dir + '/' + service_name + "_deployment.yaml"
    cmd = "kubectl create -f " + yml_name
    status,output = commands.getstatusoutput(cmd)
    return (status,output)

def get_deploy_dir():
    cmd = "find . -name kubectl"
    status, output = commands.getstatusoutput(cmd)
    deploy_path = output.split('/')
    return os.path.join(deploy_path[0],deploy_path[1])

def get_deploy_node_ips(podname):
    cmd = "kubectl get pods -o wide|grep %s|grep -v grep|awk '{print $6}'" % (podname)
    status,output = commands.getstatusoutput(cmd)
    ip_list = output.split('\n')
    return ip_list 

def check_loop(ip_list, port):
    for ip in ip_list:
        thread.start_new_thread(thread_func,(ip, port))  
 
def print_log(message):
    print(time.strftime('%Y-%m-%d %H:%M:%S, ',time.localtime(time.time())) + message)
 
def check_service_available(ip, port):
    client = ServiceClient()
    rc,stderr=client.init(ip,port)
    if(rc is False):
        return False,stderr
    result = client.control('ControlModuleVersion','ControlModuleVersion')
    version_status=result['status']
    if(version_status == 0):
        print_log(result['value'])
        return True
    else:
        return False

def thread_func(ip, port):
    global ipList
    start_time = time.time()
    end_time = time.time()
    while(end_time - start_time < 120):
        re = check_service_available(ip, port)
        if(re == True and mutex.acquire()):
            #这里需要互斥
            ipList.append(ip)
            mutex.release()
            break 
        time.sleep(5)
