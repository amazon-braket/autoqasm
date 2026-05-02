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

"""Tests for the transpiler logging-gate snapshot."""

from autoqasm.transpiler import transpiler


def test_logging_disabled_by_default() -> None:
    """At import time with no ``AUTOGRAPH_VERBOSITY``, the hot-path guards skip
    the log calls."""
    assert transpiler._AG_LOGGING_DISABLED is True


def test_ag_verbosity_recorded() -> None:
    """The captured verbosity should be a non-negative integer."""
    assert isinstance(transpiler._AG_VERBOSITY, int)
    assert transpiler._AG_VERBOSITY >= 0
