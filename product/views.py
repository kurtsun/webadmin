# Create your views here.
from django.shortcuts import render_to_response,get_object_or_404
from django.forms.models import modelformset_factory
from models import HostForm,DataCenterForm,CabinetForm,HostGroup,AuditLogTest,AuditLog
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.http import HttpResponse,HttpRequest
from django.core.paginator import Paginator,EmptyPage,PageNotAnInteger
from django.contrib import auth
from django.contrib.auth import authenticate,login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import Http404
import models,json,re,Pyro4,datetime,memcache,multiprocessing,time
from gevent.pool import Pool
from pymongo import MongoClient
from django.template import RequestContext

#Pyro4.config.COMMTIMEOUT = 15
mc = memcache.Client(['127.0.0.1:11211'],debug=0)
RPC_PORT=65090
POOL_SIZE=3
#st={}  ## ip status info

@login_required
def index(request):
	if request.user.is_superuser:
		request.session['username'] = request.user
		#return render_to_response("index.html")	
		return main(request)

@login_required
@csrf_exempt
def batch(request):
	bind_groups = request.user.userprofile.bind_groups.select_related
	groups=request.user.userprofile.bind_groups.select_related()
	hosts=[]
	for obj in groups:
		hosts += obj.get_host_ref()		
	
	return render_to_response("batch.html",{'groups': bind_groups,"ips":hosts})

class Task(object):
	def __init__(self,ips,cmd,port):
		self.cmd = cmd
		self.server = ips
		self.port = port
		self.uri = "PYRO:test@%s:%s" % (self.server,self.port)
	
	def get_starttime(self):
		return self.start_time
	def _connect(self,server):
		try:
			daemon = Pyro4.Proxy(self.uri)
			self.start_time = datetime.datetime.now()
		except:
			return None
		return daemon
	def execute(self,wait=False):
		s = self._connect(self.server)
		result = s.echo_command(self.cmd)

def change_node_status(task_id,ip,status):
	al=AuditLogTest.objects.get(task_id=task_id).node_status
	al[ip]=status
	al.save()


class RPCCon(object):
	def __init__(self,ip):
		self.ip=ip
		self.uri="PYRO:test@%s:%s" % (self.ip,RPC_PORT)

	def connect(self):
		try:
			daemon=Pyro4.Proxy(self.uri)
		except:
			return None	
		return daemon

def execute_task(task_id,ip,command,db):
	ret={}
	daemon=RPCCon(ip).connect()
	res=None
	if daemon is not None:
		db.adsame.update({"task_id":task_id,"host":ip},{"$set":{"status":"executing"}})
		res = daemon.echo_command(command)
		if res[2] == 0:
			ret[ip]="success"
		else:
			ret[ip]="failed"
	else:
		ret[ip]="failed"

	db.adsame.update({"task_id":task_id,"host":ip},{"$set":{"status":ret[ip]}})
	return res[0],res[1],res[2],ip
				
def get_mongo_conn():
	try:
		mongo_conn=MongoClient("localhost",27017)
		db=mongo_conn.adsame
	except:
		return None
	return db

class ProcessPool(object):
	def __init__(self,task,*args):
		self.pool = Pool(POOL_SIZE)
		self.task = task
		self.args = args
		self.result = []

	def execute(self):
		p = self.pool.applay_async(self.task,args=args)
		self.result.append(p)
	def get_res(self):
		return self.result
def multi_execute_command(request):
	if request.method == 'GET':
		task_id = time.time().__str__().split(".")[0]
		group_name = request.GET.getlist('group')
		host = request.GET.getlist('host')
		bind_groups = request.user.userprofile.bind_groups.select_related()
		hosts=[]
		for obj in bind_groups:
			for g in group_name:
				if obj.host_group.name == g:
					hosts += obj.get_host_ref()
		command_name = request.GET.get('command')
		
		
		new_hosts=[]
		if hosts:
			for h in hosts:
				new_hosts.append(h.ip_address)

		new_hosts=list(set(new_hosts+host))	
		res_list=[]
		db=get_mongo_conn()
		if db is None:
			return HttpResponse("mongo cannot connect")
		db.adsame.insert({"task_id":task_id});
		audit_log = AuditLogTest.objects.create(user=request.user.username,group=",".join(group_name),
												command_type="cmd",command=command_name,
												execute_time=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),
												task_status="executing")
		audit_log.task_id = task_id
		audit_log.save()
		db=get_mongo_conn()
		if db is None:
			return HttpResponse("mongo cannot connect")
		db.adsame.insert({"task_id":task_id})
		pool = Pool(POOL_SIZE)
		for h in new_hosts:
			db.adsame.insert({"task_id":task_id,"host":h,"status":"padding"})
			p = pool.apply_async(execute_task,args=(task_id,h,command_name,db))
			res_list.append(p)
		
		pool.join()
		result={}
		r=None
		for res in res_list:
			ret={}
			try:
				return_result,error,return_code,ip = res.get()
				if return_code == 0:
					return_code = 'success'
				else:
					return_code = 'failed'
				ret['result'],ret['error'],ret['status'] = return_result,error,return_code
				result[ip]=ret
			except:
				pass
		end_time = datetime.datetime.now()
		audit_log=AuditLogTest.objects.get(task_id=task_id)
		audit_log.task_status="success"
		audit_log.finish_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
		audit_log.result=json.dumps(result)
		audit_log.save()
		result['task_id']=task_id
		return HttpResponse(json.dumps(result),content_type="application/json")
		
		
@csrf_exempt
def execute_command(request):
	if request.method == 'GET':
		group_name=request.GET.getlist('group')
		bind_groups = request.user.userprofile.bind_groups.select_related()
		hosts=[]
		for obj in bind_groups:
			for g in group_name:
				if obj.host_group.name == g:
					hosts += obj.get_host_ref()	
		command_name = request.GET.get('command')
		
		result={}
		for h in hosts:
			ip=h.ip_address
			result[ip]={}
			uri = "PYRO:test@%s:65090" % ip
			try:
				daemon = Pyro4.Proxy(uri)
				start_time = datetime.datetime.now()
				res = daemon.echo_command(command_name)
				end_time = datetime.datetime.now()
				if res[2] == 0:
					result[ip]['status'] = 'success'
				else:
					result[ip]['status'] = 'failed'
			except:
				result[ip]['status'] = 'failed'
			result[ip]['result'] = res[0]
			result[ip]['error'] = res[1]
		audit_log = AuditLogTest(user=request.user.username,group=",".join(group_name),
									command_type='cmd',command=command_name,
									execute_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
									finish_time =end_time.strftime('%Y-%m-%d %H:%M:%S'),
									result=json.dumps(result),
									task_id=task_id
									)
		audit_log.save()
		result['task_id'] = AuditLog.objects.latest('id').id
		return HttpResponse(json.dumps(result),content_type="application/json")
	

def get_command_result(request):
	if request.method == 'GET':
		task_id = request.GET.get('task_id')
		return 	HttpResponse(models.AuditLogTest.objects.get(task_id=task_id).result)
			

@login_required
def batch_log(request):
	from datetime import datetime
	today=datetime.today()
	audit_log=models.AuditLogTest.objects.filter(execute_time__gte=datetime(today.year,today.month,today.day))
	db=get_mongo_conn()
	if db is None:
		pass
	task_result={}
	task_ids=[]
	for task in audit_log:
		task_ids.append(task.task_id)
		success=0
		failed=0
		executing=0
		padding=0
		result=db.adsame.find({"task_id":task.task_id})	
		#return HttpResponse(result)
		for cur in result:
			res=cur.get("status")
			if res == 'success':
				success += 1
			elif res == 'padding':
				padding += 1
			elif res == 'executing':
				executing += 1
			elif res == 'failed':
				failed += 1
			node_status = "success:%d,executing:%d,failed:%d,padding:%d" % (success,executing,failed,padding)	
			a = AuditLogTest.objects.get(task_id=task.task_id)
			a.node_status=node_status
			a.save()
			
	paginator = Paginator(audit_log,15)
	page = request.GET.get('page')
	try:
		audits = paginator.page(page)
	except PageNotAnInteger:
		audits = paginator.page(1)
	except EmptyPage:
		audits = paginator.page(paginator.num_pages)
	return render_to_response("batch_log.html",{'audit_log':audits,
												'page_current_id': audits.number,
												'max': paginator.page_range,
												})

@login_required
def remote_login(request,ip):
	return render_to_response("remote_login.html",{'ip_address':ip})

@csrf_exempt
def my_login(request):
	if request.method == 'POST':
		email = request.POST.get('email')
		password = request.POST.get('password')
		try:
			user = auth.authenticate(username=email,password=password)
			if user is not None:
				if user.is_active:
					login(request,user)
					login_log = AuditLog(user=email,group="",
											command_type="login",command="",
											execute_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
											finish_time="",result="",error="")
					login_log.save()
					return HttpResponseRedirect("/main")
				else:
					return HttpResponseRedirect("something error")
			else:
				return render_to_response("login.html",{'login_err':"username or password is not correct"})
		except:
			raise Http404
	else:
		return render_to_response("login.html")

		

@login_required
def main(request):
	bind_groups = request.user.userprofile.bind_groups.select_related()
	user_bind_groups = request.user.userprofile.user_bind_groups.select_related()
	host_list=[]
	for obj in bind_groups:
			host_list += obj.get_host_ref()
	data_center = models.DataCenter.objects.all()
	cabinet = models.Cabinet.objects.all()
	
	search=False
	search_value=''
	search_key=''
	get_list=[]
	if request.method == 'GET':
		if request.GET.get('data_center'):
			search_value = request.GET.get('data_center')
			get_list = models.Host.objects.filter(data_center=search_value)
			search_key='data_center'
		elif request.GET.get('cabinet'):
			search_value = request.GET.get('cabinet')
			get_list = models.Host.objects.filter(cabinet=search_value)
			search_key='cabinet'
		elif request.GET.get('search'):
			search_value = request.GET.get('search')
			get_list = [ ip for ip in host_list if re.search(search_value,ip.ip_address) 
													or re.search(search_value,ip.group)]
			search_key='search'

		if len(search_key)>0:
			host_list = get_list
			search=True
		
		hosts=list(set(host_list))
		host_length=len(hosts)
		paginator = Paginator(hosts,15)
		page = request.GET.get('page')
		try:
			hosts = paginator.page(page)
		except PageNotAnInteger:
			hosts = paginator.page(1)
		except EmptyPage:
			hosts = paginator.page(paginator.num_pages)
			
	return render_to_response('index.html',{'host_list':hosts,
						'host_user': user_bind_groups[0].host_user.username,
						'host_length':host_length,
						'groups':len(bind_groups),
						'search': search,
						'search_key': search_key,
						'search_value' : search_value,
						'page_current_id': hosts.number,
						"max": paginator.page_range,
						"data_center": data_center,
						"cabinet": cabinet},
						context_instance=RequestContext(request))

@csrf_exempt
def manager_host(request):
	data_center = models.DataCenter.objects.all()
	cabinet = models.Cabinet.objects.all()
	if request.method == 'POST':
		data=request.POST.copy()
		data['hardware'] = json.JSONEncoder().encode({"cpu":data['cpu'],
													"disk":data['disk_capcity']})
		form = HostForm(data)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect("/main")
	else:
		form = HostForm()

	return render_to_response("add_host.html",{"form": form,
												"data_center": data_center,
												"cabinet": cabinet})

@csrf_exempt
def add_data_center(request):
	if request.method == 'POST':
		form = DataCenterForm(request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect("/main")
	else:
		form = DataCenterForm()
	return render_to_response("add_data_center.html",{"form":form})

@csrf_exempt
def add_cabinet(request):
	if request.method == 'POST':
		form = CabinetForm(request.POST)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect("/main")
	else:
		form = CabinetForm()
	return render_to_response("add_cabinet.html",{"form":form})


def del_host(request,host_id):
	entity = get_object_or_404(models.Host,pk=host_id)
	entity.delete()
	return HttpResponse("success delete")

def get_distinct_column(column):
	return models.Host.objects.values(column).distinct()

def get_column(request,column):
	entity = get_distinct_column(column)
	groupid = request.GET.get('group_select')
	result=models.Host.objects.filter(group=groupid)
	return render_to_response('query.html',{"entity":entity,"result":result})

def get_key_value(request,key,value):
	#return HttpResponse(key + value)
	if key == 'data_center':
		entity = models.Host.objects.filter(data_center=value)
		#return HttpResponse(entity)
	elif key == 'cabinet':
		entity = models.Host.objects.filter(cabinet=value)
	else:
		return HttpResponse("<h2>something error</h2>")
		
	return render_to_response('query.html',{"entity": entity})

@csrf_exempt
def batch_add_hosts(request):
	if request.method == 'POST':
		line=request.POST['comment'].split("\n")
		for element in line:
			host=element.strip().split(",")
			ins=models.Host(
				ip_address=host[0],
				host_name=host[1],
				operation_system=host[2],
				group=host[3])
			ins.save()
		return HttpResponseRedirect("/main")
	else:
		return render_to_response("batch_add_hosts.html")
