from tastypie import fields
#from tastypie.authentication import BasicAuthentication, ApiKeyAuthentication, MultiAuthentication
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from django_ztaskq.models import Task
from .serializers import PrettyJSONSerializer 


class zTaskResource(ModelResource):
    '''
    API resource definition for the Task model
    '''
    class Meta:
        resource_name = 'task'
        queryset = Task.objects.all()
#       excludes = [ 'user', ]
        detail_allowed_methods = ['get', ]
        list_allowed_methods = [ 'get', ]
        authentication = Authentication() #MultiAuthentication(BasicAuthentication(), ApiKeyAuthentication())
        authorization = Authorization()
        serializer = PrettyJSONSerializer()

