#!/usr/bin/env python
#coding=utf-8

import os
from deploy import deploy

if __name__ == '__main__':
    service_name = "fast_lr"
    port = 17080
    docker_image_tag = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.1"
    cmd = "pp"
    print("cmd: %s" % cmd)
