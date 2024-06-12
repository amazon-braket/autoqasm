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


def sanitize_parameter_name(name: str) -> str:
    """
    Method to modify the variable name if it is a
    reserved keyword

    Args:
        name (str): Name of the variable to be checked

    Returns:
        str: Returns a modified 'name' that has an underscore ('_') appended to it;
        otherwise, it returns the original 'name' unchanged
    """
    return f"{name}_" if name in reserved_keywords else name
