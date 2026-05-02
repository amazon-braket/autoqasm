# Copyright Amazon.com Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Traceback filtering for AutoQASM.

AutoQASM rewrites user functions with ``diastatic-malt`` (AutoGraph) before
executing them, producing a transformed Python function whose frames appear
in tracebacks alongside AutoQASM's own internals. When a user's program
has a bug, the traceback can contain more than a dozen frames that obscure
the line in user code that actually raised.

This module rewrites ``exc.__traceback__`` to drop frames whose source
lives inside AutoQASM or malt internals. Users can opt in to the full
unfiltered traceback via :func:`set_verbose_errors` or by setting the
``AUTOQASM_VERBOSE_ERRORS`` environment variable.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from types import TracebackType

VERBOSE_ERRORS_ENV_VAR = "AUTOQASM_VERBOSE_ERRORS"

# Path segments identifying frames that are stripped from filtered
# tracebacks. AutoGraph writes the transformed user function to a
# ``__autograph_generated_file*.py`` scratch module in the OS tmp dir;
# those frames are noise as well. We deliberately keep ``oqpy`` frames
# since they can point at meaningful type errors.
_INTERNAL_PATH_MARKERS: tuple[str, ...] = (
    os.sep.join(("autoqasm", "api.py")),
    os.sep.join(("autoqasm", "transpiler", "")),
    os.sep.join(("autoqasm", "operators", "")),
    os.sep.join(("autoqasm", "converters", "")),
    os.sep.join(("autoqasm", "program", "program.py")),
    os.sep.join(("autoqasm", "_frame_filtering.py")),
    os.sep.join(("", "malt", "")),
    "__autograph_generated_file",
)

# Module-level override. ``None`` defers to the environment variable.
_verbose_errors_override: bool | None = None


def set_verbose_errors(enabled: bool) -> None:
    """Enable or disable verbose tracebacks globally for this process.

    When verbose errors are enabled, AutoQASM will not strip its own
    internal frames from tracebacks raised during program construction.
    This is useful when debugging AutoQASM itself, or when reporting bugs.

    Args:
        enabled (bool): ``True`` to show full (unfiltered) tracebacks;
            ``False`` to suppress AutoQASM / malt internal frames.
    """
    global _verbose_errors_override
    _verbose_errors_override = bool(enabled)


def verbose_errors_enabled() -> bool:
    """Return whether verbose (unfiltered) tracebacks are currently enabled.

    The override set by :func:`set_verbose_errors` takes precedence over the
    ``AUTOQASM_VERBOSE_ERRORS`` environment variable.

    Returns:
        bool: Whether verbose tracebacks are enabled.
    """
    if _verbose_errors_override is not None:
        return _verbose_errors_override
    raw = os.environ.get(VERBOSE_ERRORS_ENV_VAR, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_internal_frame(tb: TracebackType, markers: Iterable[str]) -> bool:
    """Return True if the given traceback frame comes from AutoQASM internals."""
    filename = tb.tb_frame.f_code.co_filename
    return any(marker in filename for marker in markers)


def filter_traceback(
    exc: BaseException,
    extra_markers: Iterable[str] = (),
) -> BaseException:
    """Rewrite ``exc.__traceback__`` to hide AutoQASM and malt internal frames.

    No-op when :func:`verbose_errors_enabled` returns ``True``. If every frame
    is internal, the traceback is set to ``None``: Python will then append
    the user's call-site frames as the exception continues propagating.

    Args:
        exc (BaseException): The exception whose ``__traceback__`` should be
            filtered. The exception is returned for convenience.
        extra_markers (Iterable[str]): Additional path-segment markers to
            treat as internal. Useful for tests.

    Returns:
        BaseException: The same exception with its ``__traceback__`` rewritten.
    """
    if verbose_errors_enabled():
        return exc

    tb = exc.__traceback__
    if tb is None:
        return exc

    markers = (*_INTERNAL_PATH_MARKERS, *extra_markers)
    kept_frames: list[TracebackType] = []
    cursor: TracebackType | None = tb
    while cursor is not None:
        if not _is_internal_frame(cursor, markers):
            kept_frames.append(cursor)
        cursor = cursor.tb_next

    new_tb: TracebackType | None = None
    for frame in reversed(kept_frames):
        new_tb = TracebackType(
            tb_next=new_tb,
            tb_frame=frame.tb_frame,
            tb_lasti=frame.tb_lasti,
            tb_lineno=frame.tb_lineno,
        )
    exc.__traceback__ = new_tb
    return exc
