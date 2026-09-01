import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    transient_exceptions: tuple[type[Exception], ...],
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> T:
    """Retry fn() on transient_exceptions only, with exponential backoff.

    Any exception not in transient_exceptions propagates immediately on the
    first attempt - this is what makes permanent errors "never retried"
    rather than a policy we have to remember to apply everywhere.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except transient_exceptions:
            if attempt == max_attempts:
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))
