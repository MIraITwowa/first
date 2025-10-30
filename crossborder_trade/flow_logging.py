from __future__ import annotations

import logging
from typing import Any

from django.conf import settings


class FlowDebugFilter(logging.Filter):
    """Enable flow logs only when ENABLE_FLOW_DEBUG is set."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - simple boolean gate
        return bool(getattr(settings, "ENABLE_FLOW_DEBUG", False))


def _format_context(context: dict[str, Any]) -> str:
    if not context:
        return ""
    parts = [f"{key}={value}" for key, value in sorted(context.items()) if value is not None]
    return " | ".join(parts)


def log_flow_debug(flow: str, message: str, **context: Any) -> None:
    """Utility for emitting structured flow logs behind the feature flag."""

    if not getattr(settings, "ENABLE_FLOW_DEBUG", False):
        return

    logger = logging.getLogger(f"flow.{flow}")
    context_suffix = _format_context(context)
    if context_suffix:
        logger.info("%s | %s", message, context_suffix)
    else:
        logger.info("%s", message)
