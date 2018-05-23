namespace cpp ServiceMonitorInterface
namespace java service.monitor.thrift
namespace perl ServiceMonitorInterface
namespace php ServiceMonitorInterface

struct ServiceMonitorParam {
    1: string value         
}
service ServiceMonitorInterface{
	string updateModel(1: ServiceMonitorParam param)
}
