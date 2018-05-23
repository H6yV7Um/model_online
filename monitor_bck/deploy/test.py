#!/usr/bin/env python
#coding=utf-8

import os
import deploy

if __name__ == '__main__':
    state = ''
    status, output = deploy.deploy_service("pic_download_v1.2", 17000, "registry.api.weibo.com/weibo_rd_algorithmplatform/mediaservice_download:v1.3")
    if status == 0:
        #查询部署是否完成
        while state != 'Running':
            state = deploy.check_deploy_state(output)
            print(state)
    else:
        #打印部署失败原因
        print(output)
