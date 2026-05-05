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

This module rewrites ``exc.__traceback__`` to drop internal frames. Users
can opt in to the full unfiltered traceback via :func:`set_verbose_errors`
or by setting the ``AUTOQASM_VERBOSE_ERRORS`` environment variable.

How a frame is classified as internal
-------------------------------------

* A module (or subpackage) that should be hidden sets
  ``__autoqasm_internal__ = True`` at its top level. The filter walks a
  frame's dotted module name up the import hierarchy via :data:`sys.modules`
  and hides the frame if any ancestor carries the flag. Setting the flag
  on a subpackage's ``__init__.py`` therefore covers every submodule
  under it.

* Frames from third-party packages we cannot modify are matched by their
  dotted module name against :data:`_THIRD_PARTY_INTERNAL_MODULES` —
  currently ``diastatic-malt``, which AutoQASM uses as its AutoGraph
  implementation.

* AutoGraph compiles transformed user code into a scratch file named
  ``__autograph_generated_file*.py``. Those frames have no importable
  module, so they are matched by filename basename — the one case where
  a path check is genuinely the right tool.
"""

from __future__ import annotations

import os
import sys
from types import FrameType, TracebackType

__autoqasm_internal__ = True

INTERNAL_MARKER: str = "__autoqasm_internal__"

VERBOSE_ERRORS_ENV_VAR: str = "AUTOQASM_VERBOSE_ERRORS"

_THIRD_PARTY_INTERNAL_MODULES: tuple[str, ...] = ("malt",)

_AUTOGRAPH_GENERATED_PREFIX: str = "__autograph_generated_file"

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


def _module_or_ancestor_is_flagged(module_name: str) -> bool:
    """Return True if ``module_name`` or any of its ancestors in
    :data:`sys.modules` sets :data:`INTERNAL_MARKER` to True."""
    name = module_name
    while name:
        module = sys.modules.get(name)
        if module is not None and getattr(module, INTERNAL_MARKER, False):
            return True
        if "." not in name:
            return False
        name = name.rsplit(".", 1)[0]
    return False


def _is_third_party_internal_module(module_name: str) -> bool:
    """Return True if ``module_name`` is, or is nested under, one of the
    third-party modules listed in :data:`_THIRD_PARTY_INTERNAL_MODULES`."""
    return any(
        module_name == ext or module_name.startswith(ext + ".")
        for ext in _THIRD_PARTY_INTERNAL_MODULES
    )


def _is_internal_frame(frame: FrameType) -> bool:
    """Return True if ``frame`` comes from AutoQASM internals."""
    module_name = frame.f_globals.get("__name__", "")
    if _module_or_ancestor_is_flagged(module_name):
        return True
    if _is_third_party_internal_module(module_name):
        return True
    basename = os.path.basename(frame.f_code.co_filename)
    return basename.startswith(_AUTOGRAPH_GENERATED_PREFIX)


def filter_traceback(exc: BaseException) -> BaseException:
    """Rewrite ``exc.__traceback__`` to hide AutoQASM-internal frames.

    No-op when :func:`verbose_errors_enabled` returns ``True``. If every frame
    is internal, the traceback is set to ``None``: Python will then append
    the user's call-site frames as the exception continues propagating.

    Args:
        exc (BaseException): The exception whose ``__traceback__`` should be
            filtered. The exception is returned for convenience.

    Returns:
        BaseException: The same exception with its ``__traceback__`` rewritten.
    """
    if verbose_errors_enabled():
        return exc

    tb = exc.__traceback__
    if tb is None:
        return exc

    kept: list[TracebackType] = []
    cursor: TracebackType | None = tb
    while cursor is not None:
        if not _is_internal_frame(cursor.tb_frame):
            kept.append(cursor)
        cursor = cursor.tb_next

    new_tb: TracebackType | None = None
    for node in reversed(kept):
        new_tb = TracebackType(
            tb_next=new_tb,
            tb_frame=node.tb_frame,
            tb_lasti=node.tb_lasti,
            tb_lineno=node.tb_lineno,
        )
    exc.__traceback__ = new_tb
    return exc


__autoqasm_internal__ = True
