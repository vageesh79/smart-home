"""Define common decorators."""

from typing import Callable


def callback(func: Callable[..., None]) -> Callable[..., None]:
    """Annotation to mark a method as a callback."""
    # pylint: disable=protected-access
    func._appdaemon_callback = True  # type: ignore
    return func


def endpoint(func: Callable[..., None]) -> Callable[..., None]:
    """Annotation to mark a method as an API endpoint."""
    # pylint: disable=protected-access
    func._appdaemon_endpoint = True  # type: ignore
    return func
