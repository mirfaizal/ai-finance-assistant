"""
LangSmith Tracing Helper

Provides the ``@traceable`` decorator and a ``get_langsmith_client`` factory
so any agent or orchestrator function can log traces to LangSmith with a
single import line.

Set these variables in .env to enable tracing:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=ls__...
    LANGCHAIN_PROJECT=ai-finance-assistant   (optional, default project name)

Graceful degradation: if the environment variables are missing or
langsmith is not installed, ``traceable`` becomes a no-op pass-through
decorator so all code continues to work without any changes.
"""

from __future__ import annotations

import os
import functools
from typing import Any, Callable, TypeVar

from src.utils.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ── Detect whether tracing is enabled ───────────────────────────────────────────

def _tracing_enabled() -> bool:
    return (
        os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")
        and bool(os.getenv("LANGCHAIN_API_KEY", "").strip())
    )


# ── Lazy client factory ─────────────────────────────────────────────────────────

_client = None

def get_langsmith_client():
    """
    Return a cached LangSmith Client, or None if tracing is not configured.
    """
    global _client
    if _client is not None:
        return _client
    if not _tracing_enabled():
        return None
    try:
        from langsmith import Client  # noqa: PLC0415
        _client = Client(
            api_key=os.getenv("LANGCHAIN_API_KEY"),
        )
        logger.info(
            "LangSmith tracing enabled. Project: %s",
            os.getenv("LANGCHAIN_PROJECT", "default"),
        )
        return _client
    except ImportError:
        logger.warning(
            "langsmith package not installed; tracing disabled. "
            "Run: pip install langsmith"
        )
        return None
    except Exception as exc:
        logger.warning("LangSmith client init failed: %s", exc)
        return None


# ── @traceable decorator ─────────────────────────────────────────────────────────

def traceable(
    name: str | None = None,
    run_type: str = "chain",
    tags: list[str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator that wraps a function with LangSmith tracing.

    If LangSmith is not configured (no API key / package), this decorator
    is a transparent no-op — the original function runs unchanged.

    Parameters
    ----------
    name : str | None
        Display name in the LangSmith UI (defaults to the function name).
    run_type : str
        One of "chain", "llm", "tool", "retriever" (default "chain").
    tags : list[str] | None
        Optional list of tags visible in the LangSmith UI.

    Usage
    -----
    from src.utils.tracing import traceable

    @traceable(name="finance_qa_agent", run_type="chain", tags=["finance"])
    def ask_finance_agent(question: str) -> str:
        ...
    """
    def decorator(func: F) -> F:
        if not _tracing_enabled():
            return func   # no-op when tracing is off

        try:
            from langsmith.run_helpers import traceable as ls_traceable  # noqa: PLC0415
            wrapped = ls_traceable(
                run_type=run_type,
                name=name or func.__name__,
                tags=tags or [],
            )(func)
            return wrapped  # type: ignore[return-value]
        except ImportError:
            logger.warning(
                "langsmith not installed; @traceable on '%s' is a no-op.",
                func.__name__,
            )
            return func
        except Exception as exc:
            logger.warning(
                "Failed to apply @traceable to '%s': %s", func.__name__, exc
            )
            return func

    return decorator


# ── Manual span logging ──────────────────────────────────────────────────────────

def log_run(
    name: str,
    inputs: dict,
    outputs: dict,
    run_type: str = "chain",
    tags: list[str] | None = None,
    error: str | None = None,
) -> None:
    """
    Manually log a single run to LangSmith without using the decorator.

    Useful for logging runs inside conditional branches or loops.

    Parameters
    ----------
    name : str
        Name of the run.
    inputs : dict
        Input values for the run.
    outputs : dict
        Output values for the run.
    run_type : str
        One of "chain", "llm", "tool", "retriever".
    tags : list[str] | None
        Optional tags.
    error : str | None
        Error message if the run failed.
    """
    client = get_langsmith_client()
    if client is None:
        return
    try:
        import uuid
        from datetime import datetime, timezone
        run_id = uuid.uuid4()
        project = os.getenv("LANGCHAIN_PROJECT", "ai-finance-assistant")
        client.create_run(
            id=run_id,
            name=name,
            run_type=run_type,
            inputs=inputs,
            start_time=datetime.now(timezone.utc),
            project_name=project,
            tags=tags or [],
        )
        client.update_run(
            run_id=run_id,
            outputs=outputs,
            end_time=datetime.now(timezone.utc),
            error=error,
        )
        logger.debug("LangSmith: logged run '%s'", name)
    except Exception as exc:
        logger.debug("LangSmith log_run failed silently: %s", exc)
