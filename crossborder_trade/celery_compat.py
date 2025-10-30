"""Utility helpers to allow importing tasks even when Celery isn't installed.

This enables Django management commands (like `check`) to run before Celery
is installed, while still exposing the real Celery decorators when available.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Mapping, Optional

try:  # pragma: no cover - exercised in real environments with Celery installed
    from celery import shared_task  # type: ignore
    from celery.utils.log import get_task_logger  # type: ignore
    CELERY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - executed during lightweight checks
    CELERY_AVAILABLE = False

    class _ImmediateResult:
        def __init__(self, value: Any):
            self._value = value

        def get(self, timeout: Optional[float] = None) -> Any:
            return self._value

        @property
        def result(self) -> Any:
            return self._value

    def _invoke_immediately(func: Callable[..., Any]) -> Callable[..., Any]:
        def delay(*args: Any, **kwargs: Any) -> _ImmediateResult:
            return _ImmediateResult(func(*args, **kwargs))

        def apply_async(
            args: Optional[Iterable[Any]] = None,
            kwargs: Optional[Mapping[str, Any]] = None,
            **options: Any,
        ) -> _ImmediateResult:
            args = tuple(args) if args is not None else ()
            kwargs = dict(kwargs or {})
            return _ImmediateResult(func(*args, **kwargs))

        setattr(func, "delay", delay)
        setattr(func, "apply_async", apply_async)
        return func

    def shared_task(*task_args: Any, **task_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return _invoke_immediately(func)

        return decorator

    def get_task_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

try:  # pragma: no cover
    from celery.schedules import crontab  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    def crontab(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"args": args, "kwargs": kwargs}
