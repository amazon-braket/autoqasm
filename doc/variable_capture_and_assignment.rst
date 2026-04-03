AutoQASM Variable Capture and Assignment
=========================================

This guide explains how AutoQASM captures Python variable assignments and
transforms them into OpenQASM variable declarations and statements. It is
intended for developers who want to understand the internals of AutoQASM and
may want to contribute to the library.

How AutoQASM Transforms Python Code
------------------------------------

AutoQASM uses a modified version of TensorFlow's AutoGraph library (called
"malt") to transpile Python source code into OpenQASM. When a user decorates a
function with ``@aq.main`` or ``@aq.subroutine``, AutoQASM parses the function's
AST (abstract syntax tree), rewrites certain nodes, and then executes the
rewritten code. During execution, operator functions intercept assignments,
control flow, and other statements to build up an internal representation of the
quantum program using the `oqpy <https://github.com/openqasm/oqpy>`_ library.

The transformation pipeline has three layers:

1. **AST transformation** — rewrites Python assignment nodes to call operator
   functions.
2. **Operator functions** — decide at runtime how to handle each assignment
   based on the value's type and the program's current state.
3. **oqpy program model** — the underlying intermediate representation that
   accumulates variable declarations and statements and ultimately serializes
   to OpenQASM 3.0.


AST Transformation of Assignments
----------------------------------

The ``AssignTransformer`` converter visits assignment nodes in the Python AST
and rewrites them so that every assignment flows through the ``assign_stmt``
operator function.

Regular assignments
^^^^^^^^^^^^^^^^^^^

A statement like ``val = some_expression`` is rewritten to::

    val = ag__.assign_stmt("val", some_expression)

The expression on the right-hand side is evaluated first by Python, producing
whatever value it produces. Then ``assign_stmt`` is called with the target
variable name (as a string) and the evaluated result. This means
``assign_stmt`` sees the *result* of the expression, not the expression AST.

Augmented assignments
^^^^^^^^^^^^^^^^^^^^^

Augmented assignments (``+=``, ``-=``, ``*=``, etc.) are desugared into regular
assignments before transformation. For example::

    val += expr

becomes::

    val = ag__.assign_stmt("val", val + expr)

Without this desugaring, Python would evaluate the augmented assignment natively
using ``__iadd__`` (or similar), completely bypassing ``assign_stmt``. This is
important because ``assign_stmt`` is the only place where certain variable
promotion decisions are made.

Return statements
^^^^^^^^^^^^^^^^^

Return statements in ``@aq.main`` functions are handled by a separate converter
that calls ``assign_for_output`` to register the return value as an output
parameter in the generated OpenQASM. AutoGraph internally transpiles
``return x`` into an assignment to a special ``retval_`` variable::

    retval_ = x
    return retval_

The ``assign_stmt`` function has special handling for the ``retval_`` target
name to avoid creating unnecessary intermediate variables.


The ``assign_stmt`` Operator
-----------------------------

``assign_stmt(target_name, value)`` is the central function that handles all
variable assignments during program transpilation. It receives the target
variable name and the evaluated value, and decides what to do based on the
value's type and the current program state.

The decision logic follows this order:

1. **Already-declared QASM variable**: If the target name already exists in the
   oqpy program and the value is a QASM type (``oqpy.base.Var`` or
   ``oqpy.base.OQPyExpression``), the existing variable is reused and a QASM
   assignment statement is generated.

2. **New QASM variable**: If the value is an ``oqpy.base.Var`` (for example,
   from ``aq.FloatVar(0.5)`` or ``measure(q)``), a new QASM variable is
   declared with the target name.

3. **QASM expression**: If the value is an ``oqpy.base.OQPyExpression`` (but
   not a ``Var``), this may indicate a reassignment where a previously plain
   Python variable is now being combined with a QASM expression. The deferred
   promotion mechanism (described later in this document) handles this case.

4. **Plain Python value**: If the value is a plain Python ``int``, ``float``,
   or ``bool``, it is wrapped in a deferred wrapper and returned. No QASM
   variable is declared at this point. See the section on deferred promotion
   below for details.

After resolving the target variable, ``assign_stmt`` chooses one of three modes
for the actual QASM statement:

- **Direct assignment**: ``a = b;`` — used when the value references an
  already-declared variable.
- **Root-scope declaration**: ``int[32] a = 10;`` — used when the target is new
  and we are at the top level of the function (not inside a loop or
  conditional).
- **Auto-declared assignment**: ``a = 10;`` with an implicit ``int[32] a;`` at
  the top — used when inside a control flow block. oqpy automatically hoists
  the declaration to the root scope.


The Program Conversion Context
-------------------------------

The ``ProgramConversionContext`` holds all state for the program currently being
transpiled. Key attributes relevant to variable assignment include:

- **oqpy program stack**: A stack of ``oqpy.Program`` objects, one per scope
  level. The bottom of the stack is the root (main) scope; nested scopes are
  pushed for subroutines and other constructs.

- **Deferred value storage**: A dictionary mapping variable names to their
  deferred wrappers. This is populated when ``assign_stmt`` encounters a plain
  Python value and consumed when the value is later promoted.

- **Variable index counter**: An incrementing counter used to generate unique
  names for auto-created variables (e.g., ``__bit_0__``, ``__int_1__``,
  ``__float_2__``). Deferred wrappers do *not* consume a counter slot when
  created — only explicit ``aq.FloatVar()`` / ``aq.IntVar()`` calls do.

- **Root scope flag**: A boolean indicating whether the transpiler is currently
  at the top level of a function or inside a control flow block (``for``,
  ``while``, ``if``). This affects whether variables are declared inline or
  auto-hoisted.


Type System
-----------

AutoQASM maps Python types to oqpy variable types during transpilation:

.. list-table::
   :header-rows: 1

   * - Python type
     - oqpy type
     - OpenQASM type
   * - ``bool``
     - ``oqpy.BoolVar``
     - ``bool``
   * - ``int``
     - ``oqpy.IntVar``
     - ``int[32]``
   * - ``float``
     - ``oqpy.FloatVar``
     - ``float[64]``

The ``wrap_value`` function converts Python values to their oqpy equivalents.
It is implemented as a ``singledispatch`` function, so it can be extended for
additional types. Values that are already oqpy types (``Var`` or
``OQPyExpression``) are returned unchanged.

The ``map_parameter_type`` function maps Python types to oqpy variable *classes*
(not instances). It is used when determining what type of QASM variable to
create for a given Python value.


Integration with oqpy
----------------------

AutoQASM builds on the `oqpy <https://github.com/openqasm/oqpy>`_ library for
OpenQASM code generation. Understanding a few oqpy concepts is important for
working with the assignment pipeline.

Variable registration
^^^^^^^^^^^^^^^^^^^^^

oqpy tracks variables in two dictionaries on its ``Program`` object:

- ``declared_vars``: Variables that have been explicitly declared (e.g.,
  ``int[32] a = 10;``).
- ``undeclared_vars``: Variables that have been referenced in expressions but
  not yet declared. oqpy auto-declares these at the top of the program when
  serializing to OpenQASM.

The ``_add_var`` method registers a variable. It uses **object identity** to
detect conflicts: if a variable with the same name already exists and is a
*different Python object*, oqpy raises a ``RuntimeError``. This means you must
reuse the same ``Var`` object throughout the program — creating a second
``FloatVar(name="val")`` and using it alongside the first will cause a
conflict.

Expression AST generation
^^^^^^^^^^^^^^^^^^^^^^^^^

When oqpy converts an expression to its AST representation (via ``to_ast``), it
walks the expression tree. Each ``Var`` node calls ``_add_var(self)`` to
register itself with the program. This is why object identity matters — if a
``Var`` in an expression tree is a different object from the one already
registered, oqpy raises a conflict error.

Root-scope declarations
^^^^^^^^^^^^^^^^^^^^^^^

When a deferred variable is promoted inside a loop body, the declaration must
appear at the root scope of the program (before the loop), not inside the loop
body. AutoQASM achieves this by appending the declaration statement directly to
``oqpy_program.stack[0].body`` (the root scope's statement list) and marking
the variable as declared via ``_mark_var_declared``.


Return Value Handling
---------------------

Return values from ``@aq.main`` functions are handled by a dedicated code path:

1. The return converter rewrites ``return x`` to call ``return_output_from_main``
   (which registers the output parameter) followed by ``assign_for_output``
   (which generates the QASM assignment).

2. ``assign_for_output`` unwraps any deferred wrappers back to their raw Python
   values before processing, so the return path behaves identically regardless
   of whether the value was deferred.

3. For subroutine returns, ``assign_stmt`` handles the special ``retval_``
   variable. If the return value is an already-declared variable, it is returned
   directly without creating an intermediate ``retval_`` variable.


Deferred Promotion of Plain Python Values
-------------------------------------------

When a variable is initialized with a plain Python value (e.g., ``val = 0.5``)
and later updated with a QASM expression inside a loop (e.g.,
``val = val + measure(q)``), AutoQASM needs to promote the Python value to a
declared QASM variable. However, not all plain Python values need promotion —
a value used only as a gate parameter (e.g., ``rx(0, val)``) should remain a
literal in the generated QASM.

AutoQASM handles this with **deferred wrapper classes** that subclass Python's
built-in numeric types. These wrappers behave identically to plain numeric
values in most contexts but can lazily promote themselves to oqpy variables when
they participate in arithmetic with QASM expressions.

Deferred wrapper classes
^^^^^^^^^^^^^^^^^^^^^^^^

- ``DeferredFloat`` — subclasses ``float``, promotes to ``oqpy.FloatVar``
- ``DeferredInt`` — subclasses ``int``, promotes to ``oqpy.IntVar``

Both inherit from a shared ``DeferredVarMixin`` that provides the lazy
promotion logic. The wrappers override arithmetic operators (``__add__``,
``__mul__``, etc.) to detect when the other operand is a QASM expression. When
this happens, the wrapper creates an oqpy variable and delegates the arithmetic
to it. When the other operand is a plain Python value, the wrapper falls back to
normal numeric arithmetic.

How deferred promotion works
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``assign_stmt`` encounters a plain Python value, it wraps it in a deferred
wrapper and stores it in the program conversion context. The wrapper is returned
as the new value of the Python variable.

Because the wrapper subclasses the original numeric type, it behaves as a
literal in most contexts:

- Passed to a gate: ``rx(0, val)`` sees ``val`` as a plain ``float`` and
  inlines the literal ``0.5`` in the generated QASM.
- Used in pure Python arithmetic: ``val * 2`` returns a plain Python ``float``
  result.

When the wrapper participates in arithmetic with a QASM expression (e.g.,
``val + measure(q)``), it lazily creates an oqpy variable and delegates the
operation. The resulting ``OQPyExpression`` references the named variable.

When ``assign_stmt`` is later called for the reassignment (e.g.,
``val = val + measure(q)``), it detects the stored deferred value and promotes
it to a declared QASM variable at the root program scope.

If the deferred value is never used in a QASM expression (e.g., it is only
passed to a gate as a literal), no QASM variable is ever declared.

Example
^^^^^^^

::

    @aq.main(num_qubits=3)
    def main():
        val = 0.5
        for q in aq.range(3):
            val = val + measure(q)
        rx(0, val)

Generated QASM:

.. code-block:: text

    OPENQASM 3.0;
    qubit[3] __qubits__;
    float[64] val = 0.5;
    for int q in [0:3 - 1] {
        bit __bit_0__;
        __bit_0__ = measure __qubits__[q];
        val = val + __bit_0__;
    }
    rx(val) __qubits__[0];

Compared with a variable that remains a literal::

    @aq.main(num_qubits=1)
    def main():
        val = 0.5
        rx(0, val)

Generated QASM:

.. code-block:: text

    OPENQASM 3.0;
    qubit[1] __qubits__;
    rx(0.5) __qubits__[0];

In the second case, ``val`` is never promoted — it remains a plain ``float``
and is inlined as the literal ``0.5``.


Common Pitfalls for Contributors
---------------------------------

Object identity in oqpy
^^^^^^^^^^^^^^^^^^^^^^^^

oqpy uses ``is`` (not ``==``) to check if two variables are the same. Creating
two ``FloatVar(name="val")`` objects and using both in the same program will
raise a ``RuntimeError``. Always reuse the same ``Var`` object when referring to
the same QASM variable.

Deferred wrappers and ``isinstance``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``DeferredFloat`` is a subclass of ``float``, and ``DeferredInt`` is a subclass
of ``int``. This means ``isinstance(val, float)`` returns ``True`` for deferred
wrappers. If you need to distinguish deferred wrappers from plain values, check
for ``DeferredVarMixin``.

Augmented assignments bypass normal dispatch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Without the ``visit_AugAssign`` desugaring in the AST transformer, ``val += x``
would be evaluated natively by Python using ``__iadd__``, completely bypassing
``assign_stmt``. Any new assignment-like syntax that Python adds in the future
would need similar treatment in the AST transformer.

Variable counter and naming
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The variable index counter on ``ProgramConversionContext`` is incremented each
time a new auto-named variable is created. Deferred wrappers intentionally do
*not* increment this counter when created. If they did, every plain Python value
assignment would shift all subsequent auto-generated variable names. The counter
is only incremented when an explicit ``aq.FloatVar()``, ``aq.IntVar()``, or
similar is created.

Root scope vs. control flow scope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The root scope flag is ``True`` at the top level of a function and ``False``
inside ``for``/``while``/``if`` blocks. This affects how variables are declared:

- At root scope: variables are declared inline (e.g., ``int[32] a = 10;``).
- Inside control flow: variables are assigned in the current scope and oqpy
  auto-hoists the declaration (``int[32] a;``) to the root scope.

When a deferred variable is promoted inside a loop, the declaration is manually
appended to the root scope to ensure correct ordering in the generated QASM.
