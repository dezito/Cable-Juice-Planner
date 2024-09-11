__version__ = "1.0.0"
from time import perf_counter

from logging import getLogger
BASENAME = f"pyscript.{__name__}"
_LOGGER = getLogger(BASENAME)

# Dictionary to store start times
start_times = {}

def start_benchmark(section):
    _LOGGER = globals()['_LOGGER'].getChild(f"start_benchmark")
    _LOGGER.warn(f"Benchmarking for section '{section}' has started.")
    start_times[section] = perf_counter()

def end_benchmark(section):
    _LOGGER = globals()['_LOGGER'].getChild(f"end_benchmark")
    end_time = perf_counter()
    if section in start_times:
        elapsed_time = end_time - start_times[section]
        _LOGGER.warn(f"{section}: took {elapsed_time:.6f} seconds")
        return elapsed_time
    else:
        _LOGGER.warn(f"Benchmarking for section '{section}' was not started.")

def benchmark_decorator(repeats=None):
    if repeats is None:
        repeats = 1
        
    def decorator(func):
        def wrapper(*args, **kwargs):
            _LOGGER = globals()['_LOGGER'].getChild(f"benchmark_decorator_average => {func.get_name()}")
            times = []
            result = None
            for i in range(repeats):
                start_time = perf_counter()
                result = func(*args, **kwargs)
                end_time = perf_counter()
                time = end_time - start_time
                times.append(time)
                
            if repeats > 1:
                for i, time in enumerate(times):
                    _LOGGER.warn(f"Run {i+1}: took {time} seconds")
            
            avg_time = sum(times) / repeats
            _LOGGER.warn(f"Took {avg_time:.6f} seconds{' on average' if repeats > 1 else ''}.")
            return result
        return wrapper
    return decorator