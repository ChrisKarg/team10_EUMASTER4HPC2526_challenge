# helpers.py
import time

def time_function(func, *args, **kwargs):
    """Time a function call and return the result + elapsed time"""
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    return result, end - start
