import functools
from django.core.cache import cache


def single_instance_task(timeout):
    def task_exc(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ret_value = None
            lock_id = "celery-single-instance-" + func.__name__
            lock = cache.lock(lock_id, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = func(*args, **kwargs)
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        return wrapper

    return task_exc
