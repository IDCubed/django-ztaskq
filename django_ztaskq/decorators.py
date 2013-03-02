import uuid
import logging
from functools import wraps


def ztask(memoize=False):
    """Decorator to augment function (task) with async computation ability.

    :param memoize: should function calls with the same args be memoized?
    :type memoize: bool

    The memoize flag allows functions to be marked

    """
    from .conf import settings
    try:
        from zmq import PUSH
    except ImportError:
        from zmq import DOWNSTREAM as PUSH

    def wrapper(func):
        function_name = '%s.%s' % (func.__module__, func.__name__)

        logger = logging.getLogger('ztaskd')
        logger.info('Registered task: %s' % function_name)

        from .context import shared_context as context
        socket = context.socket(PUSH)
        socket.connect(settings.ZTASKD_URL)

        @wraps(func)
        def _async(*args, **kwargs):
            """Call the function asynchronously by placing it in a task queue.
            """
            ztaskq_delay = kwargs.pop('ztaskq_delay', 0)
            if memoize: # same func and args will have same taskid
                taskid = str(uuid.uuid5(uuid.NAMESPACE_URL,
                    '%r-%r-%r' % (function_name, args, kwargs)))
            else:
                # give a random unique id regardless of input
                # (almost certainly unique)
                taskid = str(uuid.uuid4())
            try:
                socket.send_pyobj(
                    (taskid, function_name, args, kwargs, ztaskq_delay, user)
                )
            except Exception: # pylint: disable=W0703
                logger.error('Failed to submit task to ztaskd: '
                    '%s(args=%r, kwargs=%r)' % (function_name, args, kwargs))
            return taskid

        setattr(func, 'async', _async)
        return func

    return wrapper
