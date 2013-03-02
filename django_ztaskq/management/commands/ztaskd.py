import sys
import traceback
import atexit
from datetime import datetime, timedelta
from threading import Thread, Lock, Timer
from pytz import utc
from zmq import STREAMER, PUSH, PULL, device, ZMQError
from django.core.management.base import BaseCommand
from ...models import Task, Status
from ...conf import settings, get_logger
from ...context import shared_context as context


logger = get_logger('ztaskd')


def queue(task_pk):
    queue_socket = context.socket(PUSH)
    queue_socket.connect(settings.ZTASK_INTERNAL_QUEUE_URL)
    queue_socket.send_pyobj((str(task_pk),))
    logger.info('Passed task to worker queue (%r)' % task_pk)


class ThreadPool(object):

    def __init__(self):
        self.threads = {}
        self.lock = Lock()

    def spawn(self, task_pk, delay=0):
        with self.lock:
            self._shutdown()
            kwargs = {
                'task_pk': task_pk
            }
            if delay > 0:
                thread = Timer(float(delay), queue, kwargs=kwargs)
            else:
                thread = Thread(target=queue, kwargs=kwargs)
            self.threads[thread.name] = thread
            logger.debug('Added thread %s' % thread.name)
            self.threads[thread.name].start()
            logger.debug('Started thread %s' % thread.name)

    def _shutdown(self, all=False):
        keys = self.threads.keys()
        logger.debug('Current active threads: %s' % ', '.join(keys))
        for thread_name in keys:
            if all:
                if hasattr(self.threads[thread_name], 'cancel'):
                    self.threads[thread_name].cancel()
                if self.threads[thread_name].is_alive():
                    self.threads[thread_name].join()
            if not self.threads[thread_name].is_alive():
                del self.threads[thread_name]
                logger.debug('Removed spent thread %s' % thread_name)

    def shutdown(self):
        with self.lock:
            self._shutdown(all=True)


class BouncerThread(Thread):
    """A simple thread that bounces data to the worker.
    """

    def __init__(self, group=None, name=None):
        super(BouncerThread, self).__init__(group=group, name=name)
        self.queue_socket = context.socket(PULL)
        self.worker_socket = context.socket(PUSH)
        self.device = None
        self.daemon = True

    def run(self):
        self.queue_socket.bind(settings.ZTASK_INTERNAL_QUEUE_URL)
        self.worker_socket.bind(settings.ZTASK_WORKER_URL)
        try:
            self.device = device(STREAMER,
                                 self.queue_socket,
                                 self.worker_socket)
        except ZMQError, e:
            if e.errno == 156384765:
                self.queue_socket.close()
                self.worker_socket.close()
            else:
                raise e


class Command(BaseCommand):

    args = ''
    help = 'Start the ztaskd server'

    def __init__(self):
        super(Command, self).__init__()
        self.server_socket = context.socket(PULL)
        self.threads = ThreadPool()
        self.bouncer_thread = BouncerThread()

    def shutdown(self):
        logger.info('Shutting down nicely')
        logger.debug('Closing connections')
        self.server_socket.close()
        logger.debug('Terminating threads')
        self.threads.shutdown()
        context.term()

    def bind_sockets(self):
        self.server_socket.bind(settings.ZTASKD_URL)

    def enqueue_leftover(self):
        logger.info('Enqueuing left-over tasks...')
        queued_tasks = Task.objects.filter(status=Status.QUEUED)
        now = utc.localize(datetime.utcnow())
        for task in queued_tasks:
            delta = task.queued - now
            delay = int(delta.total_seconds())
            if delay < 0:
                delay = 0
            self.enqueue_task(task, delay)
        logger.info('Left-over tasks enqueued')

    def enqueue_task(self, task, delay):
        self.threads.spawn(task_pk=task.pk, delay=delay)
        logger.info('Enqueued task (%r)' % task.pk)

    def recv_and_enqueue(self):
        try:
            id, func, args, kwargs, delay, user = self.server_socket.recv_pyobj()
            queued = utc.localize(datetime.utcnow() + timedelta(seconds=delay))
            task, was_created = Task.objects.get_or_create(
                taskid=id,
                function_name=func,
                args=args,
                kwargs=kwargs,
                queued=queued,
                user=user
            )
            logger.info('Listed task in django database (%r)' % task.pk)
            if was_created:
                self.enqueue_task(task, delay)
            else:
                logger.warning(
                    'Ignoring task (%r) because it is already present.' % (
                        task.pk,
                    )
                )
        except Exception, e: # pylint: disable=W0703
            logger.error('Error setting up function. Details:\n%s' % e)
            traceback.print_exc(e)

    def _on_load(self):
        """Execute any startup function callbacks associated with ztaskd.
        """
        self.bind_sockets()
        self.bouncer_thread.start()
        self.enqueue_leftover()
        for callable_name in settings.ZTASKD_ON_LOAD:
            logger.info("ON_LOAD calling %s" % callable_name)

            parts = callable_name.split('.')
            module_name = '.'.join(parts[:-1])
            member_name = parts[-1]

            if not module_name in sys.modules:
                __import__(module_name)

            callable_fn = getattr(sys.modules[module_name], member_name)
            callable_fn()

    def handle(self, *args, **options): # pylint: disable=W0613
        try:
            logger.info(
                'Server starting on %s.' % settings.ZTASKD_URL
            )
            atexit.register(self.shutdown)
            self._on_load()
            while True:
                self.recv_and_enqueue()
        except KeyboardInterrupt:
            raise SystemExit()
