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

"""Errors raised in the AutoQASM build process."""

from __future__ import annotations

from typing import Any


class AutoQasmError(Exception):
    """Base class for all AutoQASM exceptions."""


class AutoQasmTypeError(AutoQasmError):
    """Generic type error."""


class UnsupportedFeatureError(AutoQasmError):
    """AutoQASM unsupported feature."""


class ParameterTypeError(AutoQasmError):
    """AutoQASM parameter type error."""


class MissingParameterTypeError(AutoQasmError):
    """AutoQASM requires type hints for subroutine parameters."""


class ParameterNotFoundError(AutoQasmError):
    """A FreeParameter could not be found in the program."""


class InvalidGateDefinition(AutoQasmError):
    """Gate definition does not meet the necessary requirements."""


class InvalidCalibrationDefinition(AutoQasmError):
    """Calibration definition does not meet the necessary requirements."""


class InvalidTargetQubit(AutoQasmError):
    """Target qubit is invalid in the current context."""


class InvalidQubitIdentifier(AutoQasmError):
    """An object cannot be used as a qubit identifier."""

    def __init__(self, qid: Any):
        """
        Args:
            qid (Any): The object that was supplied where a single qubit was expected.
        """
        super().__init__(
            f'Invalid qubit identifier: "{qid}". Must be a single qubit, '
            f"not an object of type '{type(qid).__name__}'."
        )


class UnsupportedGate(AutoQasmError):
    """Gate is not supported by the target device."""


class UnsupportedNativeGate(AutoQasmError):
    """Native gate is not supported by the target device."""


class VerbatimBlockNotAllowed(AutoQasmError):
    """Verbatim block is not supported by the target device."""


class UnknownQubitCountError(AutoQasmError):
    """Missing declaration for the number of qubits."""

    def __init__(self):
        super().__init__("""Unspecified number of qubits.

Specify the number of qubits used by your program by supplying the \
`num_qubits` argument to `aq.main`. For example:

    @aq.main(num_qubits=5)
    def my_autoqasm_program():
        ...
""")


class OutsideProgramContextError(AutoQasmError):
    """Raised when an AutoQASM feature is used outside of an active program
    context (i.e. outside a function decorated with ``@aq.main`` /
    ``@aq.subroutine`` / ``@aq.gate``).
    """

    def __init__(self, feature: str | None = None):
        """
        Args:
            feature (str | None): The name of the AutoQASM feature being invoked
                outside of an active program context, if known. Used to produce a
                slightly more pointed error message.
        """
        feature_description = f"`{feature}`" if feature else "This AutoQASM feature"
        super().__init__(f"""{feature_description} can only be used inside a function decorated \
with `@aq.main`, `@aq.subroutine`, `@aq.gate`, or `@aq.gate_calibration`.

For example:

    import autoqasm as aq
    from autoqasm.instructions import h, cnot, measure

    @aq.main
    def my_program():
        h(0)
        cnot(0, 1)
        return measure([0, 1])

If you want to build a program programmatically, use the `aq.build_program()` \
context manager directly.
""")


class BuildError(AutoQasmError):
    """Non-AutoQasmError raised during program construction, wrapped with
    actionable guidance pointing back to the user's code.

    The original exception is preserved via ``__cause__``.
    """


class InsufficientQubitCountError(AutoQasmError):
    """Target device does not have enough qubits for the program."""


class UnsupportedConditionalExpressionError(AutoQasmError):
    """Conditional expressions which return values are not supported."""

    def __init__(self, true_type: type | None, false_type: type | None):
        if_type = true_type.__name__ if true_type else "None"
        else_type = false_type.__name__ if false_type else "None"
        super().__init__(f"""\
`if` clause resolves to {if_type}, but `else` clause resolves to {else_type}. \
Both the `if` and `else` clauses of an inline conditional expression \
must resolve to the same type.""")


class InvalidAssignmentStatement(AutoQasmError):
    """Invalid assignment statement for an AutoQASM variable."""


class InvalidArrayDeclaration(AutoQasmError):
    """Invalid declaration of an AutoQASM array variable."""


class UnsupportedSubroutineReturnType(AutoQasmError):
    """Unsupported return type for an AutoQASM subroutine."""


class NameConflict(AutoQasmError):
    """Name conflict between user-named variables."""


class NestedMainProgramError(AutoQasmError):
    """Main program nested inside another main program."""
