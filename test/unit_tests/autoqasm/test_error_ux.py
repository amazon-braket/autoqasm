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

"""Tests for the traceback filtering and error UX improvements."""

from __future__ import annotations

import sys
import traceback
from types import TracebackType

import pytest

import autoqasm as aq
from autoqasm import _frame_filtering, errors
from autoqasm.instructions import h, measure


def _build_dynamic_program(name: str = "p") -> object:
    """Compile a tiny ``@aq.main`` function from a string and return it.

    The resulting function has no source file on disk, which triggers the
    ``InaccessibleSourceCodeError`` → ``BuildError`` path in the transpiler.
    """
    src = (
        "import autoqasm as aq\n"
        "from autoqasm.instructions import h\n"
        "@aq.main\n"
        f"def {name}():\n"
        "    h(0)\n"
    )
    module_globals: dict = {}
    exec(compile(src, "", "exec"), module_globals)
    return module_globals[name]


def _frame_is_internal(frame) -> bool:
    """Independent reimplementation of ``_frame_filtering._is_internal_frame``.

    Kept separate so that a bug in the production classifier cannot silently
    mask itself in tests.
    """
    f_globals = frame.f_globals
    if f_globals.get(_frame_filtering.INTERNAL_MARKER, False):
        return True
    module_name = f_globals.get("__name__", "")
    return module_name == "malt" or module_name.startswith("malt.")


def _assert_no_internal_frames(tb: TracebackType | None) -> None:
    """Walk ``tb`` and fail if any frame comes from code that should be hidden."""
    cursor: TracebackType | None = tb
    while cursor is not None:
        frame = cursor.tb_frame
        assert not _frame_is_internal(frame), (
            f"internal frame leaked through filter: "
            f"module={frame.f_globals.get('__name__')!r} "
            f"file={frame.f_code.co_filename!r}"
        )
        cursor = cursor.tb_next


def test_outside_program_context_raises_autoqasm_error() -> None:
    """Calling a gate outside an ``@aq.main`` function should raise
    ``OutsideProgramContextError`` with actionable guidance."""
    with pytest.raises(errors.OutsideProgramContextError) as exc_info:
        h(0)
    msg = str(exc_info.value)
    assert "@aq.main" in msg
    assert "@aq.subroutine" in msg


def test_error_classes_are_autoqasm_errors() -> None:
    """New error classes must be catchable as ``AutoQasmError``."""
    assert issubclass(errors.OutsideProgramContextError, errors.AutoQasmError)
    assert issubclass(errors.BuildError, errors.AutoQasmError)


def test_measure_outside_program_context_raises() -> None:
    """``measure()`` called outside ``@aq.main`` produces the clean error."""
    with pytest.raises(errors.OutsideProgramContextError):
        measure(0)


def test_verbose_errors_toggle() -> None:
    """``set_verbose_errors()`` controls whether internal frames are kept."""
    assert aq.verbose_errors_enabled() is False

    aq.set_verbose_errors(True)
    try:
        assert aq.verbose_errors_enabled() is True
    finally:
        aq.set_verbose_errors(False)

    assert aq.verbose_errors_enabled() is False


def test_verbose_errors_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """``AUTOQASM_VERBOSE_ERRORS`` enables verbose mode when no explicit
    override is set."""
    _frame_filtering._verbose_errors_override = None

    for value, expected in [("", False), ("1", True), ("true", True), ("0", False)]:
        monkeypatch.setenv(_frame_filtering.VERBOSE_ERRORS_ENV_VAR, value)
        assert aq.verbose_errors_enabled() is expected, f"for env value {value!r}"


def test_filter_traceback_hides_internal_frames() -> None:
    """Building a dynamically-compiled program should raise ``BuildError``
    and the surfaced traceback should contain no internal frames."""
    program = _build_dynamic_program()
    with pytest.raises(errors.BuildError) as exc_info:
        program.build()
    _assert_no_internal_frames(exc_info.value.__traceback__)


def test_filter_traceback_verbose_keeps_internal_frames() -> None:
    """With verbose errors on, internal frames are preserved for debugging."""
    program = _build_dynamic_program()
    aq.set_verbose_errors(True)
    try:
        with pytest.raises(errors.BuildError) as exc_info:
            program.build()
        cursor: TracebackType | None = exc_info.value.__traceback__
        saw_internal = any(_frame_is_internal(f) for f, _ in traceback.walk_tb(cursor))
        assert saw_internal, "verbose mode should preserve at least one internal frame"
    finally:
        aq.set_verbose_errors(False)


def test_filter_traceback_preserves_user_call_site() -> None:
    """The user's ``.build()`` call site (this test file) must survive filtering."""
    program = _build_dynamic_program()
    with pytest.raises(errors.BuildError) as exc_info:
        program.build()
    frames = traceback.extract_tb(exc_info.value.__traceback__)
    assert any(f.filename == __file__ for f in frames), (
        f"expected at least one frame from this test file; got {frames}"
    )


def test_inaccessible_source_raises_build_error() -> None:
    """A function whose source can't be read should raise a friendly
    ``BuildError``, not the raw ``InaccessibleSourceCodeError`` from malt."""
    program = _build_dynamic_program(name="dynamic_program")
    with pytest.raises(errors.BuildError) as exc_info:
        program.build()

    msg = str(exc_info.value)
    assert "dynamic_program" in msg
    assert "interactive Python session" in msg
    assert exc_info.value.__cause__ is not None


def test_filter_traceback_with_no_traceback_is_noop() -> None:
    """Filtering an exception that hasn't been raised is a no-op."""
    exc = RuntimeError("no tb here")
    assert exc.__traceback__ is None
    result = _frame_filtering.filter_traceback(exc)
    assert result is exc
    assert exc.__traceback__ is None


def test_module_or_ancestor_is_flagged_empty_name() -> None:
    """A frame whose module has no ``__name__`` must be treated as non-internal."""
    assert _frame_filtering._module_or_ancestor_is_flagged("") is False


@aq.main
def _nameerror_program_for_test():
    """Module-level ``@aq.main`` fixture so AutoGraph can locate its source
    and surface the ``NameError`` via its ``ag_error_metadata`` machinery."""
    this_name_does_not_exist()  # noqa: F821


def test_real_user_nameerror_filter() -> None:
    """A ``NameError`` inside ``@aq.main`` should reach the user with both
    the bad name and the program name mentioned, and no internal frames
    attached."""
    with pytest.raises(NameError) as exc_info:
        _nameerror_program_for_test.build()

    message = str(exc_info.value)
    assert "this_name_does_not_exist" in message
    assert "_nameerror_program_for_test" in message
    _assert_no_internal_frames(exc_info.value.__traceback__)


def test_new_internal_module_is_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """A future AutoQASM module that opts in via ``__autoqasm_internal__``
    has its frames hidden without any change to the filter."""
    import types as _types

    fake = _types.ModuleType("autoqasm._test_fake_internal")
    fake.__dict__[_frame_filtering.INTERNAL_MARKER] = True

    # Compile _raiser in the fake module's namespace so the frame's module is the fake one.
    exec(  # noqa: S102
        compile(
            "def _raiser():\n    raise RuntimeError('boom')\n",
            "<fake-internal>",
            "exec",
        ),
        fake.__dict__,
    )
    monkeypatch.setitem(sys.modules, fake.__name__, fake)

    try:
        fake._raiser()
    except RuntimeError as e:
        raw_frames = list(traceback.walk_tb(e.__traceback__))
        assert any(f.f_globals.get("__name__") == fake.__name__ for f, _ in raw_frames)

        _frame_filtering.filter_traceback(e)
        _assert_no_internal_frames(e.__traceback__)
    else:
        pytest.fail("_raiser did not raise")
