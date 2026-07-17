from __future__ import annotations

import time
from functools import wraps


def timed(logger):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            start = time.perf_counter()

            result = func(*args, **kwargs)

            elapsed = time.perf_counter() - start

            logger.debug(
                "%s completed in %.3f sec",
                func.__name__,
                elapsed,
            )

            return result

        return wrapper

    return decorator