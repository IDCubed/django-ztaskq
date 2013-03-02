from django.contrib.auth.models import User

from tastypie import fields
#from tastypie.authentication import BasicAuthentication, ApiKeyAuthentication, MultiAuthentication
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.resources import ModelResource

from django_ztaskq.conf import settings
from django_ztaskq.models import Task
#from modules.api.serializers import PrettyJSONSerializer 


class UserResource():
    '''
    aim to be noop UserResource
    '''
    class Meta:
        resource_name = 'user'
        queryset = User.objects.all()
        excludes = [ 'username', 'email', 'first_name', 'last_name', ]
        list_allowed_methods = []
        detail_allowed_methods = []
        authentication = Authentication() #MultiAuthentication(BasicAuthentication(), ApiKeyAuthentication())
        authorization = Authorization()
#       serializer = PrettyJSONSerializer()


class zTaskResource(ModelResource):
    '''
    API resource definition for the Task model
    '''
    user = fields.ForeignKey(settings.ZTASKD_API_USER_RESOURCE, 'user')

    class Meta:
        resource_name = 'task'
        queryset = Task.objects.all()
#       excludes = [ 'user', ]
        list_allowed_methods = [ 'get', ]
        detail_allowed_methods = [ 'get', ]
        authentication = Authentication() #MultiAuthentication(BasicAuthentication(), ApiKeyAuthentication())
        authorization = Authorization()
#       serializer = PrettyJSONSerializer()

