#!/usr/bin/env python
#coding=utf-8

import sys
import os
import commands
import shutil

def config_kubectl():
    homepath = os.environ['HOME']
    configpath = os.path.join(homepath, ".kube")
    if not os.path.exists(configpath):
        os.mkdir(configpath, 0755)
    deploy_dir = get_deploy_dir() 
    src_file = os.path.join(deploy_dir, "config")
    dst_file = os.path.join(configpath, "config")
    shutil.copyfile(src_file, dst_file)
    if not os.path.exists("/usr/bin/kubectl"):
        shutil.copyfile(deploy_dir + "/kubectl", "/usr/bin/kubectl")
        cmd = "chmod +x /usr/bin/kubectl"
        status,output = commands.getstatusoutput(cmd)
    
def buf_write(content, dstfile):
    file_add=open(dstfile, "w" )  
    file_add.write(content)   
    file_add.close()

def deploy_service(service_name, port, docker_image_tag):
    config_kubectl()
    generate_jinjia(service_name, port, docker_image_tag)
    status,output = generate_yaml(service_name)
    if status != 0:
        return (status,output)
    status,output = exec_kubectl(service_name)
    meta_name = generate_meta_name(service_name)
    if status == 0:
        #print("Deploy service success!\nPlease use 'kubectl get pods' check your service instance '%s' is running." % meta_name)
        print("Deploy action success!\n")
        output = meta_name
    else:
        print("Deploy action failed!\n" + output) 
    clean_yml_jinja(service_name)
    return (status, output)

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
    
def generate_jinjia(service_name, port, docker_image_tag):
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
