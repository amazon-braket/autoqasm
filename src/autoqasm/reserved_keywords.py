# Permalink: https://github.com/openqasm/openqasm/blob/main/source/grammar/qasm3Lexer.g4
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


def is_reserved_keyword(name: str) -> tuple[bool, str]:
    """
    Method to check whether or not 'name' is a reserved keyword

    Args:
        name (str): Name of the variable to be checked

    Returns:
        tuple[bool, str]: Returns a tuple containing a boolean indicating
        whether the input 'name' is a reserved keyword and the modified name.
        If 'name' is a reserved keyword, the modified name has an underscore
        ('_') appended to it; otherwise, it remains unchanged.
    """
    is_keyword = name in reserved_keywords
    return (is_keyword, f"{name}_" if is_keyword else name)
