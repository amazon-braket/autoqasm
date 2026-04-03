# AutoQASM Variable Assignment Pipeline

This document describes how variable assignments in Python source code are transformed into OpenQASM variable declarations and assignment statements during AutoQASM program transpilation. It covers the full pipeline from AST transformation through to QASM code generation, including the deferred promotion mechanism for plain Python values.

## Overview

When a user writes an `@aq.main` or `@aq.subroutine` function, AutoQASM uses a modified version of TensorFlow's AutoGraph (called "malt") to transpile the Python source code. Assignment statements are intercepted at the AST level and routed through operator functions that decide whether and how to declare variables in the generated OpenQASM program.

The pipeline has three layers:

1. **AST Transformation** (`src/autoqasm/converters/assignments.py`) — rewrites Python assignment AST nodes to call operator functions
2. **Operator Functions** (`src/autoqasm/operators/assignments.py`) — decide how to handle each assignment at runtime
3. **oqpy Program Model** (`oqpy.Program`) — the underlying IR that accumulates variable declarations and statements

## Layer 1: AST Transformation

### `AssignTransformer` in `src/autoqasm/converters/assignments.py`

The `AssignTransformer` is a converter that visits assignment nodes in the Python AST and rewrites them to call `assign_stmt`.

#### Regular Assignments (`visit_Assign`)

```python
# User writes:
val = some_expression

# AutoGraph transforms to:
val = ag__.assign_stmt("val", some_expression)
```

The key detail: `some_expression` is evaluated first by Python (producing whatever value it produces), and then `assign_stmt` is called with the target variable name as a string and the evaluated value. This means `assign_stmt` sees the *result* of the expression, not the expression itself.

#### Augmented Assignments (`visit_AugAssign`)

```python
# User writes:
val += expr

# AutoGraph transforms to (via desugaring):
val = ag__.assign_stmt("val", val + expr)
```

`visit_AugAssign` desugars `val += expr` into `val = val + expr` (a regular `ast.Assign` with an `ast.BinOp` value), then delegates to `visit_Assign`. This ensures augmented assignments flow through `assign_stmt` just like regular assignments.

Without this desugaring, Python would evaluate `val += expr` natively using `__iadd__`, completely bypassing `assign_stmt`. This is critical for the deferred promotion mechanism (described below) because `assign_stmt` is the only place where deferred variables get promoted to QASM variables.

#### Return Statement Assignments

Return statements are handled separately. AutoGraph transpiles `return value` into:

```python
retval_ = value    # handled by assign_for_output (for @aq.main) or assign_stmt (for retval_)
return retval_
```

The `assign_for_output` function is called for `@aq.main` return values. The `AssignTransformer` detects these (by checking if the value is already a call to `assign_for_output`) and skips them to avoid double-wrapping.

## Layer 2: Operator Functions

### `assign_stmt` — The Main Assignment Operator

`assign_stmt(target_name, value)` is the central function that handles all variable assignments. It receives the target variable name (as a string) and the evaluated value, and decides what to do based on the value's type and whether the variable already exists in the QASM program.

#### Decision Tree

```
assign_stmt(target_name, value)
│
├─ value is UndefinedReturnValue → return as-is
│
├─ target_name is "retval_" → delegate to _resolve_retval()
│   ├─ value is already-used Var in subroutine → return directly (no new variable)
│   ├─ value is list in subroutine → raise error
│   └─ otherwise → wrap_value() and continue
│
├─ target already exists in QASM program AND value is Var/OQPyExpression
│   → reuse existing variable, validate types, assign
│
├─ value is oqpy.base.Var (e.g., aq.FloatVar, measure result)
│   → copy the Var, set target name, declare/assign
│
├─ value is oqpy.base.OQPyExpression (but not Var)
│   → delegate to _promote_deferred_expression()
│   → if promotion returns None, return expression as-is
│
└─ value is anything else (plain Python int, float, bool, etc.)
    → delegate to _defer_python_value()
    → return deferred wrapper (or raw value if not deferrable)
```

#### The Three Assignment Modes (after target resolution)

Once `assign_stmt` has resolved the target variable, it chooses one of three modes for the actual QASM statement generation:

1. **Direct assignment** (`oqpy_program.set(target, value)`) — when the value references an already-declared variable, or has no init expression. Produces `a = b;`.

2. **Root-scope declaration** (`oqpy_program.declare(target)`) — when the target is new and we're at the function root scope. Produces `int[32] a = 10;`.

3. **Auto-declared assignment** (`oqpy_program.set(target, init_expression)`) — when inside a control flow block (if/for/while). The variable is set in the current scope and oqpy auto-declares it at the root scope. Produces `a = 10;` with an implicit `int[32] a;` at the top.

### `assign_for_output` — Return Value Assignments

`assign_for_output(target_name, value)` handles assignments for `@aq.main` return values. It's simpler than `assign_stmt` because return values always need to be QASM types.

Key behaviors:
- Unwraps deferred values back to raw Python values before calling `wrap_value`
- For `OQPyExpression` values (not `Var`), reuses an already-declared variable if one exists for the target name, otherwise creates a `FloatVar`
- For `Var` values, delegates to `_add_assignment`

### `_resolve_retval` — Return Statement Special Handling

AutoGraph transpiles `return x` into `retval_ = x; return retval_`. The `_resolve_retval` function handles the `retval_` assignment:

- If the value is an already-used `Var` in a subroutine, returns it directly (avoids creating an unnecessary `retval_` variable)
- Unwraps deferred values before wrapping
- Otherwise wraps the value via `types.wrap_value`

## Deferred Promotion Mechanism

### The Problem

When a user writes:

```python
val = 0.5
for q in aq.range(3):
    val = val + measure(q)
```

At the time of `val = 0.5`, we don't know whether `val` will later be used as a QASM variable (reassigned with a QASM expression in a loop) or as a plain literal (passed to a gate like `rx(0, val)`). Eagerly promoting `0.5` to a `FloatVar` would cause `rx(0, val)` to generate `float[64] val = 0.5; rx(val)` instead of the correct `rx(0.5)`.

### The Solution: Deferred Wrappers

The deferred promotion mechanism uses wrapper classes (`DeferredFloat`, `DeferredInt`) defined in `src/autoqasm/types/deferred.py` that subclass Python's `float` and `int`. These wrappers:

- **Behave as plain numeric values** when used in pure Python contexts (gate parameters, Python arithmetic, etc.)
- **Lazily promote to oqpy variables** when combined with QASM expressions via arithmetic operators

#### `DeferredVarMixin`

The shared mixin (in `src/autoqasm/types/deferred.py`) provides:

- `_deferred_init(value, name)` — stores the Python value and target variable name
- `get_or_create_var()` — lazily creates an oqpy `Var` (e.g., `FloatVar`) with the stored value and name. The `Var` is cached in `promoted_var` so subsequent calls return the same object.
- `_dispatch(op, other)` — if `other` is an `OQPyExpression`, delegates the arithmetic to the promoted oqpy `Var`. Otherwise returns `NotImplemented`, causing Python to fall back to the base type's arithmetic.
- Arithmetic operator overrides (`__add__`, `__radd__`, `__mul__`, etc.) — each calls `_dispatch` and falls back to `super()` if not dispatched.

#### `DeferredFloat` and `DeferredInt`

Thin subclasses that set `_oqpy_var_type` to `oqpy.FloatVar` or `oqpy.IntVar` respectively.

### Deferred Promotion Flow

#### Case 1: Variable used as a literal (no promotion needed)

```python
val = 0.5       # assign_stmt returns DeferredFloat(0.5, "val")
rx(0, val)      # val is a float subclass, rx sees 0.5 as a literal
```

Generated QASM: `rx(0.5) __qubits__[0];` — no variable declaration.

#### Case 2: Variable updated in a loop (promotion needed)

```python
val = 0.5                           # assign_stmt returns DeferredFloat(0.5, "val")
for q in aq.range(3):
    val = val + measure(q)          # val + measure(q) triggers _dispatch
                                    # get_or_create_var creates FloatVar(name="val", init=0.5)
                                    # assign_stmt sees OQPyExpression, calls _promote_deferred_expression
                                    # ctx.promote_deferred_value declares float[64] val = 0.5;
```

Generated QASM:
```
float[64] val = 0.5;
for int q in [0:3 - 1] {
    bit __bit_0__;
    __bit_0__ = measure __qubits__[q];
    val = val + __bit_0__;
}
```

#### Case 3: Temporary expression variable (no promotion needed)

```python
expr = 2 * theta    # 2 is a plain Python int (NOT a deferred wrapper, since it's a literal)
                     # 2 * theta: Python tries int.__mul__(2, FloatVar) → NotImplemented
                     # then FloatVar.__rmul__(theta, 2) → OQPyExpression with literal 2
                     # assign_stmt sees OQPyExpression, no deferred value for "expr"
                     # _promote_deferred_expression returns None → expression returned as-is
gpi(0, expr)        # expr is the OQPyExpression, inlined in the gate call
```

Generated QASM: `gpi(2 * theta) __qubits__[0];` — no variable declaration.

### `_defer_python_value`

Called from `assign_stmt`'s `else` branch when the value is not a QASM type. Wraps `int`, `float`, and `bool` values in deferred wrappers (via `make_deferred` from `types.deferred`) and stores them via `ctx.defer_python_value()` for later retrieval by `ctx.promote_deferred_value()`.

### `_promote_deferred_expression`

Called from `assign_stmt` when the value is an `OQPyExpression` and the target name is not yet a QASM variable. Delegates to `ctx.promote_deferred_value()` for the actual promotion and declaration.

Decision logic:
1. If `ctx.promote_deferred_value(target_name)` returns a `Var`, the deferred value was found and promoted — use it.
2. If it returns `None` but the value is an `oqpy.base.Var`, copy it with the target name.
3. If no deferred value exists and the value is a bare `OQPyExpression`, return `None` — the expression should be used as-is without creating a variable.

## The `ProgramConversionContext`

The `ProgramConversionContext` (in `src/autoqasm/program/program.py`) holds the state for the current program being transpiled:

- `_oqpy_program_stack` — stack of oqpy `Program` objects (one per scope level)
- `_deferred_python_values: dict` — maps variable names to their deferred wrappers, managed via `defer_python_value()` and `promote_deferred_value()` methods
- `_var_idx` — counter for auto-generated variable names (e.g., `__bit_0__`, `__int_1__`)
- `at_function_root_scope` — `True` at the top level of a function, `False` inside control flow blocks
- `is_var_name_used(name)` — checks if a variable name exists in the oqpy program's declared or undeclared vars

### Variable Naming

Auto-generated variable names use templates like `__bit_N__`, `__int_N__`, `__float_N__` where `N` is the value of `_var_idx` at creation time. The counter is incremented by `next_var_name()`.

Deferred wrappers do NOT increment the counter when created. This is intentional — if the deferred value is never promoted, no counter slot should be consumed. The counter is only incremented when an explicit `aq.FloatVar()`, `aq.IntVar()`, etc. is created by the user.

## oqpy Integration

### Variable Registration

oqpy tracks variables in two dictionaries on the `Program` object:
- `declared_vars` — variables that have been explicitly declared (e.g., `int[32] a = 10;`)
- `undeclared_vars` — variables that have been referenced but not yet declared (oqpy auto-declares them at the top of the program)

The `_add_var(var)` method registers a variable. It raises `RuntimeError` if a variable with the same name already exists and is a different object (identity check via `var is not existing_var`). This means you must reuse the same `Var` object throughout the program — creating a new `Var` with the same name will conflict.

### `_mark_var_declared(var)`

Moves a variable from `undeclared_vars` to `declared_vars`. Used by `ProgramConversionContext.promote_deferred_value()` to explicitly declare deferred variables at the root scope.

### Expression AST Generation

When oqpy converts an expression to AST (via `to_ast`), it walks the expression tree. Each `Var` node calls `_add_var(self)` to register itself with the program. This is why object identity matters — if a `Var` in an expression tree is a different object from the one in `declared_vars`, oqpy raises a conflict error.

## Type System

### Python to oqpy Type Mapping

`map_parameter_type` in `src/autoqasm/types/conversions.py` maps Python types to oqpy variable types:

| Python Type | oqpy Type |
|---|---|
| `bool` | `oqpy.BoolVar` |
| `int` | `oqpy.IntVar` |
| `float` | `oqpy.FloatVar` |

### `wrap_value` in `src/autoqasm/types/conversions.py`

A `singledispatch` function that converts Python values to oqpy types:
- `float` → `FloatVar`
- `int` → `IntVar`
- `bool` → `BoolVar`
- `tuple` → tuple of wrapped values
- `None` → `None`
- `oqpy.base.Var` → returned as-is
- `oqpy.base.OQPyExpression` → returned as-is

## Common Pitfalls

### Object Identity in oqpy

oqpy uses `var is existing_var` to check if a variable is the same object. Creating two `FloatVar(name="val")` objects and using both in the same program will raise `RuntimeError("Program has conflicting variables with name val")`. Always reuse the same `Var` object.

### Deferred Wrappers and `isinstance`

`DeferredFloat` is a subclass of `float`, and `DeferredInt` is a subclass of `int`. This means `isinstance(deferred_val, float)` returns `True`. Code that checks `isinstance(value, float)` will match deferred wrappers. If you need to distinguish deferred wrappers from plain values, check `isinstance(value, DeferredVarMixin)`.

### Augmented Assignments

`val += expr` is desugared to `val = val + expr` by `visit_AugAssign` before flowing through `assign_stmt`. Without this desugaring, Python evaluates the augmented assignment natively, bypassing `assign_stmt` entirely. This means the deferred promotion mechanism would never trigger for augmented assignments.

### The `retval_` Variable

AutoGraph transpiles `return x` into `retval_ = x; return retval_`. The `assign_stmt` function has special handling for `target_name == "retval_"` to avoid creating unnecessary intermediate variables. The `_resolve_retval` helper unwraps deferred values and handles subroutine-specific logic.

### Root Scope vs. Control Flow Scope

`ctx.at_function_root_scope` is `True` at the top level of a function and `False` inside `for`/`while`/`if` blocks. This affects how variables are declared:
- At root scope: `oqpy_program.declare(target)` produces `int[32] a = 10;`
- Inside control flow: `oqpy_program.set(target, value)` produces `a = 10;` with an auto-declared `int[32] a;` at the top

### `_promote_deferred_expression` and Root Scope Declaration

When a deferred variable is promoted inside a loop body (not at root scope), `ctx.promote_deferred_value()` appends the declaration to `oqpy_program.stack[0].body` — the root scope — rather than the current scope. This ensures the declaration appears at the correct position in the generated QASM (after qubit register declarations, before the loop).
