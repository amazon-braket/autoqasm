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

import os
import traceback

import pytest

import autoqasm as aq
from autoqasm import _frame_filtering, errors
from autoqasm.instructions import h, measure

# Internal-path markers built with the OS-native separator so these tests pass on
# Windows as well as POSIX.
_MALT_MARKER = os.sep.join(("", "malt", ""))
_TRANSPILER_MARKER = os.sep.join(("autoqasm", "transpiler", ""))
_OPERATORS_MARKER = os.sep.join(("autoqasm", "operators", ""))
_CONVERTERS_MARKER = os.sep.join(("autoqasm", "converters", ""))


def test_outside_program_context_raises_autoqasm_error() -> None:
    """Calling a gate outside an @aq.main function should raise
    OutsideProgramContextError."""
    with pytest.raises(errors.OutsideProgramContextError) as exc_info:
        h(0)
    msg = str(exc_info.value)
    assert "@aq.main" in msg
    assert "@aq.subroutine" in msg


def test_outside_program_context_is_autoqasm_error() -> None:
    """OutsideProgramContextError should be an AutoQasmError so `except
    aq.errors.AutoQasmError` catches it uniformly."""
    assert issubclass(errors.OutsideProgramContextError, errors.AutoQasmError)
    assert issubclass(errors.BuildError, errors.AutoQasmError)


def test_verbose_errors_toggle() -> None:
    """set_verbose_errors() controls whether internal frames are kept."""
    assert aq.verbose_errors_enabled() is False  # default

    aq.set_verbose_errors(True)
    try:
        assert aq.verbose_errors_enabled() is True
    finally:
        aq.set_verbose_errors(False)
    assert aq.verbose_errors_enabled() is False


def test_verbose_errors_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """The AUTOQASM_VERBOSE_ERRORS env var enables verbose mode when the
    module-level override is not set."""
    # Clear the module-level override for this test.
    _frame_filtering._verbose_errors_override = None

    monkeypatch.setenv(_frame_filtering.VERBOSE_ERRORS_ENV_VAR, "")
    assert aq.verbose_errors_enabled() is False

    monkeypatch.setenv(_frame_filtering.VERBOSE_ERRORS_ENV_VAR, "1")
    assert aq.verbose_errors_enabled() is True

    monkeypatch.setenv(_frame_filtering.VERBOSE_ERRORS_ENV_VAR, "true")
    assert aq.verbose_errors_enabled() is True

    monkeypatch.setenv(_frame_filtering.VERBOSE_ERRORS_ENV_VAR, "0")
    assert aq.verbose_errors_enabled() is False


def test_filter_traceback_hides_autoqasm_frames() -> None:
    """Errors raised through AutoQASM's build pipeline should not expose
    AutoQASM / malt internal frames to the user."""

    # A dynamically-compiled @aq.main function triggers the BuildError
    # code path, which flows through the transpiler internals.
    src = (
        "import autoqasm as aq\nfrom autoqasm.instructions import h\n@aq.main\ndef p():\n    h(0)\n"
    )
    module_globals: dict = {}
    exec(compile(src, "<dynamic>", "exec"), module_globals)

    with pytest.raises(errors.BuildError) as exc_info:
        module_globals["p"].build()

    frames = traceback.extract_tb(exc_info.value.__traceback__)
    for frame in frames:
        assert _MALT_MARKER not in frame.filename, (
            f"malt internal frame leaked through filter: {frame.filename}"
        )
        assert _TRANSPILER_MARKER not in frame.filename, (
            f"transpiler internal frame leaked through filter: {frame.filename}"
        )
        assert _OPERATORS_MARKER not in frame.filename, (
            f"operators internal frame leaked through filter: {frame.filename}"
        )


def test_filter_traceback_verbose_keeps_autoqasm_frames() -> None:
    """With verbose errors enabled, internal frames should stay visible for
    debugging AutoQASM itself."""

    src = (
        "import autoqasm as aq\nfrom autoqasm.instructions import h\n@aq.main\ndef p():\n    h(0)\n"
    )
    module_globals: dict = {}
    exec(compile(src, "<dynamic>", "exec"), module_globals)

    aq.set_verbose_errors(True)
    try:
        with pytest.raises(errors.BuildError) as exc_info:
            module_globals["p"].build()
        frames = traceback.extract_tb(exc_info.value.__traceback__)
        # At least one frame should come from autoqasm internals (the
        # transpiler, where BuildError is raised).
        has_internal = any(_TRANSPILER_MARKER in f.filename for f in frames)
        assert has_internal, (
            "Verbose mode should preserve at least one internal frame for debugging"
        )
    finally:
        aq.set_verbose_errors(False)


def test_filter_traceback_preserves_user_bug_frame() -> None:
    """Keep the user's call-site frame for the `.build()` call."""

    src = (
        "import autoqasm as aq\nfrom autoqasm.instructions import h\n@aq.main\ndef p():\n    h(0)\n"
    )
    module_globals: dict = {}
    exec(compile(src, "<dynamic>", "exec"), module_globals)

    with pytest.raises(errors.BuildError) as exc_info:
        module_globals["p"].build()  # <-- this frame should survive filtering

    frames = traceback.extract_tb(exc_info.value.__traceback__)
    # At least one frame should be from this test file.
    assert any(f.filename == __file__ for f in frames), (
        f"Expected at least one frame from this test file; got {frames}"
    )


def test_inaccessible_source_raises_build_error() -> None:
    """Functions defined without accessible source code should raise a
    clean BuildError, not the raw InaccessibleSourceCodeError from malt."""

    src = (
        "import autoqasm as aq\n"
        "from autoqasm.instructions import h\n"
        "@aq.main\n"
        "def dynamic_program():\n"
        "    h(0)\n"
    )
    module_globals: dict = {}
    exec(compile(src, "<dynamic>", "exec"), module_globals)

    with pytest.raises(errors.BuildError) as exc_info:
        module_globals["dynamic_program"].build()

    msg = str(exc_info.value)
    assert "dynamic_program" in msg
    assert "interactive Python session" in msg
    # The original malt exception should still be available as __cause__.
    assert exc_info.value.__cause__ is not None


def test_measure_outside_program_context_raises() -> None:
    """`measure()` called outside @aq.main should produce the clean error."""
    with pytest.raises(errors.OutsideProgramContextError):
        measure(0)


def test_filter_traceback_with_no_traceback_is_noop() -> None:
    """If an exception has no traceback yet (not raised), the filter should
    return it untouched."""
    exc = RuntimeError("no tb here")
    assert exc.__traceback__ is None
    result = _frame_filtering.filter_traceback(exc)
    assert result is exc
    assert exc.__traceback__ is None


# The following "real user bug" test uses a module-level @aq.main function so
# that malt's AutoGraph is able to locate its source code. A typo triggers
# a NameError which AutoGraph wraps via its ``ag_error_metadata`` machinery.


@aq.main
def _nameerror_program_for_test():
    this_name_does_not_exist()  # noqa: F821


def test_real_user_nameerror_filter() -> None:
    with pytest.raises(NameError) as exc_info:
        _nameerror_program_for_test.build()
    message = str(exc_info.value)
    assert "this_name_does_not_exist" in message
    assert "_nameerror_program_for_test" in message

    frames = traceback.extract_tb(exc_info.value.__traceback__)
    for frame in frames:
        assert _MALT_MARKER not in frame.filename
        assert _TRANSPILER_MARKER not in frame.filename
        assert _OPERATORS_MARKER not in frame.filename
        assert _CONVERTERS_MARKER not in frame.filename
        assert "__autograph_generated_file" not in frame.filename
