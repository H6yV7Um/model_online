#!/usr/bin/env python
#coding=utf-8

import os
import deploy

if __name__ == '__main__':
    service_name = "fast_lr"
    port = 17080
    docker_image_tag = "registry.intra.weibo.com/weibo_rd_algorithmplatform/modelservice_lr:v1.1"
    deploy.deploy_service(service_name, port, docker_image_tag)
