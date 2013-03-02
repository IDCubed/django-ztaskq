from django.conf import settings

# ZMQ Socket zTaskq master
ZTASKD_URL = getattr(settings, 'ZTASKD_URL', 'tcp://127.0.0.1:5555')

# ZMQ socket for worker 
ZTASK_WORKER_URL = getattr(settings, 'ZTASK_WORKER_URL', 'tcp://127.0.0.1:5556')

# XXX - research to doc
ZTASK_INTERNAL_QUEUE_URL = getattr(settings, 'ZTASK_INTERNAL_QUEUE_URL',
                                   'inproc://django_ztask_internal_queue')
# XXX - research to doc
ZTASKD_ON_LOAD = getattr(settings, 'ZTASKD_ON_LOAD', ())

# default log verbosity
ZTASKD_LOG_LEVEL = getattr(settings, 'ZTASKD_LOG_LEVEL', 'info')

# XXX - research to doc
ZTASKD_LOG_PATH = getattr(settings, 'ZTASKD_LOG_PATH', None)

# max filesize per log file (before rollover?)
ZTASKD_LOG_MAXBYTES = getattr(settings, 'ZTASKD_LOG_MAXBYTES', 36864)

# how many log files to let rollover
ZTASKD_LOG_BACKUP = getattr(settings, 'ZTASKD_LOG_BACKUP', 4)
