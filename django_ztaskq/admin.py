from django.contrib import admin
from .models import Task

class TaskAdmin(admin.ModelAdmin):
    list_display = ('taskid', 'function_name', 'args', 'kwargs', 'return_value',
                    'error', 'queued', 'started', 'finished', 'status',)
    list_filter = ('function_name', 'return_value', 'status',)
    search_fields = ('taskid', 'function_name','args', 'kwargs', 'return_value',
                    'error', 'queued', 'started', 'finished', 'status',)
    readonly_fields = ('taskid', 'function_name', 'args', 'kwargs',
                       'return_value','error', 'queued', 'started', 'finished',
                       'status',)
    ordering = ('queued',)
    #fields = ('name', 'checksum', 'active', 'description', 'src')


admin.site.register(Task, TaskAdmin)
