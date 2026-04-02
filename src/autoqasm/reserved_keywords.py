# Copied from:
# https://github.com/openqasm/openqasm/blob/main/source/grammar/qasm3Lexer.g4
# https://github.com/openqasm/openpulse-python/blob/main/source/grammar/openpulseLexer.g4

reserved_keywords = {
    # openQASM keywords
    "angle",
    "array",
    "barrier",
    "bit",
    "bool",
    "box",
    "cal",
    "case",
    "complex",
    "const",
    "creg",
    "ctrl",
    "default",
    "defcal",
    "defcalgrammar",
    "delay",
    "duration",
    "durationof",
    "end",
    "euler",
    "extern",
    "false",
    "float",
    "gate",
    "gphase",
    "im",
    "include",
    "input",
    "int",
    "inv",
    "let",
    "OPENQASM",
    "measure",
    "mutable",
    "negctrl",
    "output",
    "pi",
    "pragma",
    "qreg",
    "qubit",
    "readonly",
    "reset",
    "return",
    "sizeof",
    "stretch",
    "switch",
    "tau",
    "true",
    "U",
    "uint",
    "void",
    # openpulse keywords
    "frame",
    "port",
    "waveform",
}


def sanitize_parameter_name(name: str, existing_names: set[str] | None = None) -> str:
    """
    Method to modify the variable name if it is a
    reserved keyword

    Args:
        name (str): Name of the variable to be checked
        existing_names (set[str] | None): Optional set of existing parameter names
            in the same subroutine signature. When provided, the function will keep
            appending underscores until the result is unique among existing_names
            and not a reserved keyword. When None, preserves the original
            single-underscore behavior for backward compatibility.

    Returns:
        str: Returns a modified 'name' that has underscores appended to avoid
        collisions with reserved keywords and existing names; otherwise,
        it returns the original 'name' unchanged
    """
    if name not in reserved_keywords:
        return name
    new_name = f"{name}_"
    if existing_names is not None:
        while new_name in existing_names or new_name in reserved_keywords:
            new_name = f"{new_name}_"
    return new_name
