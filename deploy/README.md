注意：
在root权限下使用本包，使用示例请参考test.py
deploy_service接受3个参数:
1). 服务名称，字符串类型
2). 服务端口，整型
3). 服务所用docker镜像的地址和tag组成的字符串
部署服务需要一定时间去拉镜像，启动docker等缓慢动作
所以deploy_service会返回（status, output)
status 如果是0，则用output做参数去调check_deploy_state检查服务是否部署完成
status 如果非0，说明部署失败，失败原因保存在output
