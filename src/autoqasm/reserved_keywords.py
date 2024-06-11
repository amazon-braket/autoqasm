# Copied from: https://github.com/openqasm/openqasm/blob/main/source/grammar/qasm3Lexer.g4
reserved_keywords = {
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
    "frame",
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
    "port",
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
    is_keyword = name in reserved_keywords
    return f"{name}_" if is_keyword else name
