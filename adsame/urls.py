from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from product import views
from product import backend
admin.autodiscover()

urlpatterns = patterns('product.views',
		(r'^$','my_login'),
		(r'^login','my_login'),
		(r'^remote_login/(?P<ip>.*)','remote_login'),
		(r'^main$','main'),
		(r'^batch$','batch'),
		(r'^batch_log$','batch_log'),
		(r'^add_host$','manager_host'),
		#(r'^command$','execute_command'),
		url(r'^api',views.multi_execute_command,name="command"),
		url(r'^result',views.get_command_result,name="result"),
		url(r'^load',backend.get_loadavg,name="loadavg"),
		url(r'^disk',backend.get_disk,name="disk"),
		url(r'^memory',backend.get_mem,name="memory"),
		(r'^add_data_center$','add_data_center'),
		(r'^add_cabinet$','add_cabinet'),
		(r'delhost/(?P<host_id>\d+)/','del_host'),
		(r'query/(?P<key>\w+)/(?P<value>\w+)','get_key_value'),
		(r'^batch_add_hosts$','batch_add_hosts'),
		(r'^admin/', include(admin.site.urls)),
)
