from views import RPCCon
from django.http import HttpResponse,HttpRequest
from gevent.pool import Pool
import json


#config={"avg":load_avg}

class MultiProcess(object):
	def __init__(self,task_func,func_name,*args):
		self.task_func=task_func
		self.func_name=func_name
		self.hosts = args
		self.pool = Pool(3)
		self.result = []
	
	def execute(self):
		for h in self.hosts[0]:
			p = self.pool.apply_async(self.task_func,args=(h,self.func_name))
			self.result.append(p)	
		
		#self.pool.join()
		return self.get_result()
	
	def get_result(self):
		return self.result
	
	def addcallback(self,func):
		return func(self.execute())

def handle_result(result_list):
	ret={}
	for r in result_list:
		tmp={}
		try:
			result,ip,host_name = r.get()
			tmp["load1min"],tmp['host_name']=result[0],host_name.split(".")[0]
			ret[ip]=tmp
		except:
			pass
	
	return 	HttpResponse(json.dumps(ret),content_type="application/json")

def handle_disk_result(result_list):
	ret={}
	for r in result_list:
		tmp={}
		try:
			result,ip,host_name = r.get()
			tmp['disk'],tmp['host_name']=result,host_name.split(".")[0]
			ret[ip]=tmp
		except:
			pass
	return HttpResponse(json.dumps(ret),content_type="application/json")

def get_bind_hosts(request):
	bind_groups=request.user.userprofile.bind_groups.select_related()
	hosts=[]
	for obj in bind_groups:
		hosts+=obj.get_host_ref()

	return hosts

def get_loadavg(request):
	return MultiProcess(get_rpc_func,"load_avg",get_bind_hosts(request)).addcallback(handle_result)

def get_disk(request):
	return MultiProcess(get_rpc_func,"get_disk_volumn",get_bind_hosts(request)).addcallback(handle_disk_result)

def get_rpc_func(host,func_name):
	daemon=RPCCon(host.ip_address).connect()
	res=None
	if daemon is not None:
		func=getattr(daemon,func_name)
		res=func()
	else:
		res = None
	return res,host.ip_address,host.host_name

