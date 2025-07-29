import os

# from pyqir import Context, Module
from llvmlite import binding
from llvmlite.binding.module import ModuleRef

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()


def load(filename: str) -> ModuleRef:
    """Load a QIR program from the file ``filename``.

    Args:
        filename: the filename to load the program from.

    Returns:
        Module: --

    Raises:
        --
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".bc":
        with open(filename, "rb") as f:
            bitcode = f.read()
        module_ref = loads_bc(bitcode)
    elif ext == ".ll":
        with open(filename, "r") as f:
            ir_text = f.read()
        module_ref = loads_ll(ir_text)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    module_ref.verify()

    return module_ref


def loads_bc(bitcode: bytes) -> ModuleRef:
    """Load a QIR program from the given string.

    Args:
        program: the QIR program.

    Returns:
        Module: --

    Raises:
        --
    """
    context = binding.create_context()
    module = binding.parse_bitcode(bitcode, context)
    return module


def loads_ll(ir_text: str) -> ModuleRef:
    """Load a QIR program from the given string.

    Args:
        program: the QIR program.

    Returns:
        Module: --

    Raises:
        --
    """
    context = binding.create_context()
    module = binding.parse_assembly(ir_text, context)
    return module
