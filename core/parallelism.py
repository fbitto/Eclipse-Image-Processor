"""One CPU budget per independent filter, inherited by nested helper tasks."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
import os

CPU_CORES = os.cpu_count() or 4
_filter_budget = ContextVar('filter_cpu_budget', default=CPU_CORES)


def filter_cpu_budget():
    return _filter_budget.get()


@contextmanager
def filter_budget(workers):
    token=_filter_budget.set(max(1,int(workers)))
    try:
        yield
    finally:
        _filter_budget.reset(token)


def layer_workers(source, count):
    """Bound scratch memory as well as CPU; conservative unknown-memory fallback.

    128 bytes/pixel/filter estimates scratch space, not measured peak RSS.
    Reserve two thirds of physical RAM for caches, GUI, OS and other applications.
    """
    try:
        memory=os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')//3
    except (AttributeError,ValueError,OSError):
        memory=512*1024**2
    # shortcut: scratch estimates are per pixel; measure per-operator peaks if larger masters exceed the budget.
    memory_limit=max(1,memory//max(1,source.size*128))
    size_limit=2 if source.size>4_000_000 else 4
    return max(1,min(count,CPU_CORES,size_limit,memory_limit))


def map_in_threads(function, items, workers=None):
    """Apply ``function`` to every item on up to ``workers`` threads; results keep input order.

    The default worker count is this filter's CPU budget. Each call runs in its own
    copy of the caller's context, so cancellation and progress scopes reach the
    helper threads. NumPy, SciPy, OpenCV and zlib release the GIL in their numerical
    loops, which is what makes threads pay off here. Split work so that the result
    does not depend on the number of threads (fixed strips, fixed reduction order).
    """
    items=list(items)
    workers=max(1,min(len(items),int(workers or filter_cpu_budget())))
    if workers == 1:
        return [function(item) for item in items]
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='corona-strip') as executor:
        futures=[executor.submit(copy_context().run,function,item) for item in items]
        return [future.result() for future in futures]
