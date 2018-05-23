#!/usr/bin/env python
#coding=utf-8
import urllib2
import urllib
import json
import time
import os,sys

if __name__ == "__main__":
    url = "http://controlcenter.ds.sina.com.cn/waic/models/update?user=dingping&id=dingping-1526024407181&"
    values={}
    zk={}
    zk['cluster_id']="zk://10.39.11.60:2181,10.39.11.61:2181,10.39.11.62:2181,10.39.11.63:2181,10.39.11.64:2181"
    zk['group_id']="model_service"
    zk['service_id']="fast_lr"
    zk['type']="test1"
    values['zkinfo']=zk
    ''' 
    values={"zkinfo":{
    "cluster_id":"zk://10.39.11.60:2181,10.39.11.61:2181,10.39.11.62:2181,10.39.11.63:2181,10.39.11.64:2181",
    "group_id":"model_service",
    "service_id":"fast_lraaa",
    "type":"test1"
}}
    values1={"zkinfo":"null"}
    #values = {"zkinfo":"aaa"}
    data = urllib.urlencode(values1)
    print(data) 
    ss = data.replace("%27","%22")
    print(ss)
    print("\n") 
    urll = url +ss 
    print("url: %s" % urll) 
    print("\n") 
    
    req = urllib2.Request(urll)
    req.get_method = lambda:'PUT'  
    res_data = urllib2.urlopen(req)
    res = res_data.read()
    print(res)
    '''
    with open("./output.json",'r') as load_f:
        dict1 = json.load(load_f)
    with open("./output1.json",'r') as load_f1:
        dict2 = json.load(load_f1)
    for src_list, dst_list in zip(sorted(dict1), sorted(dict2)):
        if str(dict1[src_list]) != str(dict2[dst_list]):
            print(src_list,dict1[src_list],dst_list,dict2[dst_list])
