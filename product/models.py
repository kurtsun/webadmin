from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User

# Create your models here.

class Host(models.Model):
	host_name = models.CharField(max_length=50)
	ip_address = models.CharField(max_length=15)
	suffix_host_name =models.CharField(max_length=20)
	operation_system = models.CharField(max_length=20)
	group = models.CharField(max_length=10)
	data_center= models.CharField(max_length=20)
	cabinet = models.CharField(max_length=20)
	hardware = models.TextField()

	def __unicode__(self):
		return "%s(%s)" % (self.host_name,self.ip_address)
	

class DataCenter(models.Model):
	name = models.CharField(max_length=20)
	contact = models.CharField(max_length=50)

class Cabinet(models.Model):
	name = models.CharField(max_length=20)

class HostForm(ModelForm):
	class Meta:
		model = Host

class DataCenterForm(ModelForm):
	class Meta:
		model = DataCenter

class CabinetForm(ModelForm):
	class Meta:
		model = Cabinet

class Terminal(models.Model):
	time = models.DateField()
	user = models.CharField(max_length=20)
	command = models.TextField()


class HostUsers(models.Model):
	username = models.CharField(max_length=20)
	password = models.CharField(max_length=20)

	
	def __unicode__(self):
		return self.username

class UserBindGroup(models.Model):
	host_user = models.ForeignKey('HostUsers')
	host_group = models.ManyToManyField('HostGroup')

	def __str__(self):
		return self.host_user.username

	def get_groups(self):
		return ",\n".join([g.name for g in self.host_group.all()])

class BindGroup(models.Model):
	#host_user = models.ForeignKey('HostUsers')
	host_group = models.ForeignKey('HostGroup')
	host = models.ManyToManyField('Host')

	def __str__(self):
		return self.host_group.name
	def get_hosts(self):
		return ",\n".join([g.host_name for g in self.host.all()])
	def get_hosts_ip(self):
		return ",\n".join([g.ip_address for g in self.host.all()])

	def get_host_ref(self):
		return self.host.all()



class HostGroup(models.Model):
	name = models.CharField(max_length=20)
	def __unicode__(self):
		return self.name
	
class Department(models.Model):
	name = models.CharField(max_length=20)
	def __unicode__(self):
		return self.name

#class BindHosts(models.Model):
#    host = models.ForeignKey('Host')
#    host_user = models.ForeignKey('HostUsers')
#    host_group = models.ManyToManyField('HostGroup')
#    enabled = models.BooleanField(default=True)
#    def __str__(self):
#        return '%s:%s' % (self.host.ip_address,self.host_user.username)
#    def get_groups(self):
#        return ",\n".join([g.name for g in self.host_group.all()])

class BindHosts(models.Model):
    host = models.ForeignKey('Host')
    host_user = models.ForeignKey('HostUsers')
    host_group = models.ManyToManyField('HostGroup')
    enabled = models.BooleanField(default=True)
    def __str__(self):
        return '%s:%s' % (self.host.ip_address,self.host_user.username)
    def get_groups(self):
        return ",\n".join([g.name for g in self.host_group.all()])



class UserProfile(models.Model):
	user = models.OneToOneField(User)
	name = models.CharField(unique=True,max_length=32)
	department = models.ForeignKey('Department',verbose_name=u'department')
    #user_groups = models.ManyToManyField('PUserGroups') #might use it in the future version
	#host_groups = models.ManyToManyField('HostGroup',verbose_name=u'accept groups')
	#bind_hosts = models.ManyToManyField('BindHosts',verbose_name=u'accept host')
	user_bind_groups = models.ManyToManyField('UserBindGroup',verbose_name=u'user_bind groups')
	bind_groups  =  models.ManyToManyField('BindGroup',verbose_name=u'bind_groups')
	#valid_begin_time = models.DateTimeField()
	#valid_end_time = models.DateTimeField()


class HostDetail(models.Model):
	architecture = models.CharField(max_length=50)
	bios_release_date = models.CharField(max_length=50)
	fqdn = models.CharField(max_length=50)
	ipaddress = models.CharField(max_length=50)
	memorysize = models.CharField(max_length=50)
	operatingsystemmajrelease = models.CharField(max_length=50)
	processorcount = models.CharField(max_length=50)
	productname = models.CharField(max_length=50)
	puppetversion = models.CharField(max_length=50)
	rubyversion = models.CharField(max_length=50)
	serialnumber  = models.CharField(max_length=50)
	selinux  = models.CharField(max_length=50)
	swapsize = models.CharField(max_length=50)
	virtual = models.CharField(max_length=50)
	processor0  = models.CharField(max_length=50)
	uptime = models.CharField(max_length=50)
	host = models.ForeignKey("Host")



class AuditLog(models.Model):
	user = models.CharField(max_length=50)
	group = models.CharField(max_length=200)
	command_type = models.CharField(max_length=20)
	command = models.TextField()
	execute_time = models.DateTimeField()
	finish_time = models.CharField(max_length=20)
	result=models.TextField()
	error = models.TextField()

class AuditLogTest(models.Model):
	user = models.CharField(max_length=50)
	group = models.CharField(max_length=20)
	command_type = models.CharField(max_length=20)
	command = models.TextField()
	execute_time = models.DateTimeField()
	finish_time = models.CharField(max_length=20)
	result=models.TextField()
	error = models.TextField()
	task_id = models.CharField(max_length=20)
	task_status = models.CharField(max_length=20)
	node_status = models.TextField()
