from product.models import Host,BindHosts,UserProfile,Department,HostGroup,HostUsers,BindGroup,UserBindGroup,AuditLog
from django.contrib import admin
from django.conf.urls import patterns,url
#_*_coding:utf-8_*_

class HostAdmin(admin.ModelAdmin):
	search_fields=("host_name","ip_address")
	list_display=("ip_address","host_name","group")

class DepartmentAdmin(admin.ModelAdmin):
	list_display=("name",)

class HostUserAdmin(admin.ModelAdmin):
	list_display=("username","password")

#class BindHostInline(admin.TabularInline):
#	model = BindHosts.host_group.through
#
#	readonly_fields = ['hostname']
#	def hostname(self, instance):
#		print dir(instance)
#		return '%s(%s)' % (instance.bindhosts.host.hostname,instance.bindhosts.host.ip_addr)	
#
#	hostname.short_description = 'row name'

class HostGroupAdmin(admin.ModelAdmin):
	list_display=("name",)
	#inlines = [ BindHostInline,]

class AuditLogAdmin(admin.ModelAdmin):
	list_display=("user","group","command_type","command","execute_time")
	list_filter=("user",)

class UserProfileAdmin(admin.ModelAdmin):
	list_display=('user','name','department')
	filter_horizontal=('user_bind_groups','bind_groups')

class UserBindGroupAdmin(admin.ModelAdmin):
	list_display = ('host_user','get_groups')
	list_filter = ('host_user','host_group')
	filter_horizontal = ('host_group',)

class BindGroupAdmin(admin.ModelAdmin):
	list_display = ('host_group','get_hosts')
	list_filter = ('host_group','host')
	filter_horizontal = ('host',)
	#raw_id_fields = (host_group",'host')

class BindHostAdmin(admin.ModelAdmin):
    list_display = ('host','host_user','get_groups')
    list_filter = ('host','host_user','host_group')
    filter_horizontal = ('host_group',)
    raw_id_fields = ("host",'host_user')

    def get_urls(self):

        urls = super(BindHostAdmin, self).get_urls()
        my_urls = patterns("",
            url(r"^multi_add/$", self.multi_add)
        )
        return my_urls + urls


    #@staff_member_required
    def multi_add(self, request):
        if request.user.is_superuser:
            import admin_custom_view
            err = {}
            result = None
            chosen_data = {}
            if request.method == 'POST':
                print request.POST
                form_obj = admin_custom_view.BindHostsMultiHandle(request)
                if form_obj.is_valid():
                    form_obj.save()
                    result = form_obj.result
                else:
                    err = form_obj.err_dic
                chosen_data = form_obj.clean_data

            #else:
            host_users = models.HostUsers.objects.all()
            hosts = models.Host.objects.all()
            host_groups = models.HostGroup.objects.all()
            return render(request,'admin/product/BindHosts/multi_add.html',{
                'user':request.user,
                'host_users':host_users,
                'host_groups':host_groups,
                'hosts':hosts,
                'err':err,
                'chosen_data': chosen_data,
                'result': result
            })
        else:
            return HttpResponse("Only superuser can access this page!")

admin.site.register(Host,HostAdmin) 
#admin.site.register(BindHosts,BindHostAdmin)
admin.site.register(UserProfile,UserProfileAdmin)
admin.site.register(Department,DepartmentAdmin)
admin.site.register(HostGroup,HostGroupAdmin)
admin.site.register(HostUsers,HostUserAdmin)
admin.site.register(BindGroup,BindGroupAdmin)
admin.site.register(UserBindGroup,UserBindGroupAdmin)
admin.site.register(AuditLog,AuditLogAdmin)
