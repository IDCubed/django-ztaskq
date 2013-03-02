import datetime
import sys
import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from pytz import utc
from picklefield import PickledObjectField

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.loading import get_model
from django.db.models import ( Model, CharField, TextField, DateTimeField,
                               ForeignKey )

from .conf import settings


class Status(object):
    """Enum-style class of possible task statuses."""
    QUEUED = u'Q'
    RUNNING = u'R'
    COMPLETED = u'C'
    FAILED = u'F'


# pretty forms for the admin interface
STATUS_CHOICES = (
    (Status.QUEUED, u'Queued'),
    (Status.RUNNING, u'Running'),
    (Status.COMPLETED, u'Completed'),
    (Status.FAILED, u'Failed'),
)


_func_cache = {} # could be a classwide "static" member
                 # (may have to override __new__)


cls_path = settings.ZTASKD_USER_MODEL
module, user_cls = cls_path.rsplit('.', 1)
user_model = get_model(module, user_cls)


class Task(Model):
    """The queued task, persisted in the database
    (so it can be polled for status)
    """

    taskid = CharField(max_length=36, primary_key=True)
    function_name = CharField(max_length=255)
    args = PickledObjectField()
    kwargs = PickledObjectField()
    return_value = PickledObjectField(null=True)

    error = TextField(blank=True, null=True)

    queued = DateTimeField(blank=True, null=True)
    started = DateTimeField(blank=True, null=True)
    finished = DateTimeField(blank=True, null=True)

    status = CharField(max_length=1, choices=STATUS_CHOICES,
        default=Status.QUEUED)

    user = ForeignKey(user_model, blank=True, null=True,
        help_text='link this task to a User, totally optional')

    class Meta:
        db_table = 'django_ztaskq_task'

    @classmethod
    def run_task(cls, task_id, logger):
        try:
            task = cls.objects.get(pk=task_id)
        except ObjectDoesNotExist, e:
            logger.info('Could not get task with id %s:\n%s' % (task_id, e))
            return
        task.run(logger)

    def mark_running(self):
        self.status = Status.RUNNING
        self.started = utc.localize(datetime.datetime.utcnow())

        self.save()

    def mark_complete(self, success=True, delete=False, error_msg=''):
        """Mark the task as finished (success/failure)

        The error message is only used if success is False.

        """
        if delete:
            self.delete()
            return

        self.status = Status.COMPLETED if success else Status.FAILED
        if not success:
            self.error = error_msg
        self.finished = utc.localize(datetime.datetime.utcnow())

        self.save()

    def run(self, logger):

        function_name = self.function_name
        args = self.args
        kwargs = self.kwargs

        self.mark_running()
        logger.info('Executing task function (%s)' % function_name)

        try:
            function = _func_cache[function_name]
        except KeyError:
            parts = function_name.split('.')
            module_name = '.'.join(parts[:-1])
            member_name = parts[-1]
            if not module_name in sys.modules:
                __import__(module_name)
            function = getattr(sys.modules[module_name], member_name)
            _func_cache[function_name] = function

        try:
            logger.info('Task.run is calling %r(%r, %r)' % (
                    function, args, kwargs))
            return_value = function(*args, **kwargs)
            logger.info('Successfully finished the function call.')
        except Exception: # pylint: disable=W0703
            stream = StringIO()
            traceback.print_exc(None, stream)
            self.mark_complete(success=False, error_msg=stream.getvalue())
            logger.error('Error calling %s. Details:\n%s' % (
                    function_name, stream.getvalue()))
            sys.exc_clear()
        else:
            self.return_value = return_value
            self.save()
            self.mark_complete(success=True)
            logger.info('Called %s successfully' % function_name)
